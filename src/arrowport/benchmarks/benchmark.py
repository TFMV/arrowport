"""Benchmark script for Arrowport performance testing."""

import base64
import json
import subprocess
import sys
import time
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.flight as flight
import requests
import structlog
from rich.console import Console
from rich.table import Table

logger = structlog.get_logger()
console = Console()


def generate_test_data(num_rows: int) -> pa.Table:
    """Generate test data with specified number of rows."""
    np.random.seed(42)  # For reproducibility

    # Generate timestamps
    base_timestamps = pd.date_range(
        "2020-01-01", freq="1s", periods=min(num_rows, 100000)
    )
    if num_rows > 100000:
        repeats = num_rows // 100000 + 1
        timestamps = np.tile(base_timestamps.values, repeats)[:num_rows]
    else:
        timestamps = base_timestamps.values

    # Generate varied data types
    data = {
        "id": range(num_rows),
        "float_col": np.random.random(num_rows),
        "int_col": np.random.randint(0, 1000000, num_rows),
        "str_col": [f"str_{i}" for i in range(num_rows)],
        "bool_col": np.random.choice([True, False], num_rows),
        "timestamp_col": timestamps,
    }

    return pa.Table.from_pydict(data)


def start_servers():
    """Start Arrowport servers."""
    console.print("Starting Arrowport servers...")

    # Start the FastAPI server
    api_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "arrowport.api.app:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8888",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Start the Flight server
    flight_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "arrowport.core.flight",
            "--host",
            "0.0.0.0",
            "--port",
            "8889",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for servers to start
    time.sleep(5)  # Give more time for startup

    # Check if servers are running
    try:
        # Check REST API
        requests.get("http://localhost:8888/metrics")

        # Check Flight server
        client = flight.FlightClient("grpc://localhost:8889")
        client.list_flights()

        console.print("Servers started successfully")
    except Exception as e:
        console.print(f"[red]Failed to start servers: {e}[/red]")
        api_process.terminate()
        flight_process.terminate()
        api_process.wait()
        flight_process.wait()
        raise

    return api_process, flight_process


def stop_servers(processes):
    """Stop Arrowport servers."""
    console.print("Stopping Arrowport servers...")
    api_process, flight_process = processes
    api_process.terminate()
    flight_process.terminate()


def benchmark_rest_api(table: pa.Table, compression: Dict) -> Tuple[float, float]:
    """Benchmark REST API performance."""
    # Prepare data
    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_stream(sink, table.schema)
    writer.write_table(table)
    writer.close()

    data = {
        "config": {"target_table": "benchmark_table", "compression": compression},
        "batch": {
            "arrow_schema": base64.b64encode(table.schema.serialize()).decode(),
            "data": base64.b64encode(sink.getvalue().to_pybytes()).decode(),
        },
    }

    # Measure time
    start_time = time.time()
    response = requests.post("http://localhost:8888/stream/benchmark", json=data)
    end_time = time.time()

    if response.status_code != 200:
        raise Exception(f"API request failed: {response.text}")

    return end_time - start_time, len(table)


def benchmark_flight(table: pa.Table) -> Tuple[float, float]:
    """Benchmark Arrow Flight performance."""
    client = flight.FlightClient("grpc://localhost:8889")

    # Prepare descriptor
    descriptor = flight.FlightDescriptor.for_command(
        json.dumps({"stream_name": "benchmark"}).encode()
    )

    # Measure time
    start_time = time.time()

    # Write table
    writer, _ = client.do_put(descriptor, table.schema)
    writer.write_table(table)
    writer.close()

    end_time = time.time()

    return end_time - start_time, len(table)


def run_benchmarks() -> None:
    """Run all benchmarks and display results."""
    sizes = [1000, 100000, 1000000]  # Different data sizes
    compressions = [
        None,
        {"algorithm": "zstd", "level": 3},
    ]

    results: List[Dict] = []

    # Start servers
    processes = start_servers()

    try:
        for size in sizes:
            table = generate_test_data(size)

            # Test REST API with different compression settings
            for compression in compressions:
                try:
                    duration, rows = benchmark_rest_api(table, compression)
                    results.append(
                        {
                            "method": "REST API",
                            "rows": rows,
                            "compression": str(compression),
                            "duration": duration,
                            "rows_per_second": rows / duration,
                        }
                    )
                except Exception as e:
                    logger.error("REST API benchmark failed", error=str(e))

            # Test Flight server
            try:
                duration, rows = benchmark_flight(table)
                results.append(
                    {
                        "method": "Flight",
                        "rows": rows,
                        "compression": "N/A",
                        "duration": duration,
                        "rows_per_second": rows / duration,
                    }
                )
            except Exception as e:
                logger.error("Flight benchmark failed", error=str(e))
    finally:
        # Stop servers
        stop_servers(processes)

    # Display results
    table = Table(title="Arrowport Benchmark Results")
    table.add_column("Method", style="cyan")
    table.add_column("Rows", style="magenta")
    table.add_column("Compression", style="yellow")
    table.add_column("Duration (s)", style="green")
    table.add_column("Rows/Second", style="red")

    for result in results:
        table.add_row(
            result["method"],
            f"{result['rows']:,}",
            result["compression"],
            f"{result['duration']:.3f}",
            f"{result['rows_per_second']:,.0f}",
        )

    console.print(table)


if __name__ == "__main__":
    run_benchmarks()
