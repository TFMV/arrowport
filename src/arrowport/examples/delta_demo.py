"""Demo script for Delta Lake functionality in Arrowport."""

import base64
import json
from datetime import datetime, timedelta

import pyarrow as pa
import requests
from rich.console import Console
from rich.table import Table

console = Console()

# Configuration
ARROWPORT_URL = "http://localhost:8888"


def create_sample_data(num_rows=1000, date_offset=0):
    """Create sample event data."""
    import random

    base_date = datetime.now() - timedelta(days=date_offset)

    data = {
        "event_id": list(range(num_rows)),
        "event_date": [base_date.strftime("%Y-%m-%d")] * num_rows,
        "event_type": [
            random.choice(["click", "view", "purchase", "signup"])
            for _ in range(num_rows)
        ],
        "user_id": [f"user_{random.randint(1, 100)}" for _ in range(num_rows)],
        "value": [random.uniform(0, 100) for _ in range(num_rows)],
        "timestamp": [
            (base_date + timedelta(seconds=i)).isoformat() for i in range(num_rows)
        ],
    }

    return pa.table(data)


def send_to_delta(table: pa.Table, table_name: str, partition_by=None):
    """Send Arrow table to Arrowport Delta Lake endpoint."""
    # Serialize Arrow table
    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_stream(sink, table.schema)
    writer.write_table(table)
    writer.close()

    # Prepare request
    url = f"{ARROWPORT_URL}/delta/{table_name}"
    params = {}
    if partition_by:
        params["partition_by"] = partition_by

    payload = {
        "batch": {
            "arrow_schema": base64.b64encode(table.schema.serialize()).decode(),
            "data": base64.b64encode(sink.getvalue().to_pybytes()).decode(),
        }
    }

    # Send request
    response = requests.post(url, json=payload, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to send data: {response.text}")


def get_table_info(table_name: str):
    """Get Delta Lake table information."""
    response = requests.get(f"{ARROWPORT_URL}/delta/{table_name}/info")
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get table info: {response.text}")


def get_table_history(table_name: str, limit=5):
    """Get Delta Lake table history."""
    response = requests.get(
        f"{ARROWPORT_URL}/delta/{table_name}/history", params={"limit": limit}
    )
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get table history: {response.text}")


def main():
    """Run the Delta Lake demo."""
    console.print("[bold blue]Arrowport Delta Lake Demo[/bold blue]")
    console.print()

    table_name = "demo_events"

    # Step 1: Create initial data
    console.print("[yellow]Step 1:[/yellow] Creating initial event data (Day 1)...")
    day1_data = create_sample_data(num_rows=1000, date_offset=1)
    result = send_to_delta(
        day1_data, table_name, partition_by=["event_date", "event_type"]
    )
    console.print(f"✅ Inserted {result['rows_processed']} rows")
    console.print()

    # Step 2: Add more data
    console.print("[yellow]Step 2:[/yellow] Adding more event data (Day 2)...")
    day2_data = create_sample_data(num_rows=1500, date_offset=0)
    result = send_to_delta(
        day2_data, table_name, partition_by=["event_date", "event_type"]
    )
    console.print(f"✅ Inserted {result['rows_processed']} rows")
    console.print()

    # Step 3: Show table info
    console.print("[yellow]Step 3:[/yellow] Table Information")
    info = get_table_info(table_name)

    info_table = Table(title=f"Delta Table: {table_name}")
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="green")

    info_table.add_row("Version", str(info["version"]))
    info_table.add_row("Total Rows", f"{info['row_count']:,}")
    info_table.add_row("File Count", str(info["file_count"]))
    info_table.add_row("Total Size", f"{info['total_size_bytes'] / (1024*1024):.2f} MB")
    info_table.add_row("Partitions", ", ".join(info["partitions"]))

    console.print(info_table)
    console.print()

    # Step 4: Show history
    console.print("[yellow]Step 4:[/yellow] Table History")
    history = get_table_history(table_name)

    history_table = Table(title="Recent Operations")
    history_table.add_column("Version", style="cyan")
    history_table.add_column("Timestamp", style="green")
    history_table.add_column("Operation", style="blue")

    for entry in history["history"][:5]:
        history_table.add_row(
            str(entry["version"]),
            entry["timestamp"][:19],  # Truncate microseconds
            entry["operation"],
        )

    console.print(history_table)
    console.print()

    # Step 5: Demo complete
    console.print("[bold green]✨ Demo Complete![/bold green]")
    console.print()
    console.print("You can now:")
    console.print("• Query the Delta table with DuckDB or Spark")
    console.print("• Use time travel to query previous versions")
    console.print("• Run VACUUM to clean up old files")
    console.print("• Continue appending more data")


if __name__ == "__main__":
    main()
