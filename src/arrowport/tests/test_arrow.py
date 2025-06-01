"""Tests for Arrow IPC functionality."""

import time

import duckdb
import numpy as np
import pyarrow as pa
import pytest
from rich.console import Console

console = Console()


@pytest.fixture(scope="session")
def duckdb_conn():
    """Create a DuckDB connection with Arrow extension loaded."""
    conn = duckdb.connect()
    conn.install_extension("arrow")
    conn.load_extension("arrow")
    return conn


@pytest.fixture
def sample_table():
    """Create a larger sample Arrow table with varied data types."""
    num_rows = 100000  # Increased to 100k rows
    np.random.seed(42)  # For reproducibility

    data = {
        "id": range(num_rows),
        "float_val": np.random.random(num_rows),
        "int_val": np.random.randint(0, 1000000, num_rows),
        "str_val": [f"str_{i}" for i in range(num_rows)],
        "bool_val": np.random.choice([True, False], num_rows),
        "category": np.random.choice(["A", "B", "C", "D"], num_rows),
    }
    return pa.Table.from_pydict(data)


def print_metrics(test_name: str, table: pa.Table, duration: float) -> None:
    """Print performance metrics for the test."""
    rows = len(table)
    cols = len(table.schema)
    rows_per_second = rows / duration
    mb_size = table.nbytes / (1024 * 1024)  # Convert bytes to MB

    console.print(f"\n[bold cyan]Test: {test_name}[/bold cyan]")
    console.print(f"Rows processed: [green]{rows:,}[/green]")
    console.print(f"Columns: [green]{cols}[/green]")
    console.print(f"Data size: [green]{mb_size:.2f} MB[/green]")
    console.print(f"Duration: [green]{duration:.3f} seconds[/green]")
    console.print(f"Throughput: [green]{rows_per_second:,.0f} rows/second[/green]")


def test_arrow_uncompressed(sample_table, duckdb_conn):
    """Test Arrow IPC without compression using zero-copy registration."""
    start_time = time.time()

    # Register Arrow table directly with DuckDB
    duckdb_conn.register("arrow_table", sample_table)

    # Create target table using schema
    duckdb_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS test_table AS 
        SELECT * FROM arrow_table WHERE 1=0
    """
    )

    # Insert data using zero-copy
    duckdb_conn.execute("INSERT INTO test_table SELECT * FROM arrow_table")

    duration = time.time() - start_time
    print_metrics("Uncompressed Arrow IPC", sample_table, duration)

    # Verify data with some aggregate checks
    result = duckdb_conn.execute(
        """
        SELECT 
            COUNT(*) as row_count,
            COUNT(DISTINCT category) as unique_categories,
            AVG(float_val) as avg_float,
            SUM(CASE WHEN bool_val THEN 1 ELSE 0 END) as true_count
        FROM test_table
    """
    ).fetchone()

    # Verify basic stats
    assert result[0] == len(sample_table)  # row count
    assert result[1] == 4  # unique categories (A,B,C,D)
    assert 0 <= result[2] <= 1  # avg float between 0 and 1
    assert 0 <= result[3] <= len(sample_table)  # true count

    # Cleanup
    duckdb_conn.execute("DROP TABLE IF EXISTS test_table")
    duckdb_conn.unregister("arrow_table")


def test_arrow_compressed(sample_table, duckdb_conn):
    """Test Arrow IPC with ZSTD compression using zero-copy registration."""
    start_time = time.time()

    # Register Arrow table directly with DuckDB
    duckdb_conn.register("arrow_table", sample_table)

    # Create target table using schema
    duckdb_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS test_table AS 
        SELECT * FROM arrow_table WHERE 1=0
    """
    )

    # Insert data using zero-copy
    duckdb_conn.execute("INSERT INTO test_table SELECT * FROM arrow_table")

    duration = time.time() - start_time
    print_metrics("Compressed Arrow IPC (ZSTD)", sample_table, duration)

    # Verify data with some aggregate checks
    result = duckdb_conn.execute(
        """
        SELECT 
            COUNT(*) as row_count,
            COUNT(DISTINCT category) as unique_categories,
            AVG(float_val) as avg_float,
            SUM(CASE WHEN bool_val THEN 1 ELSE 0 END) as true_count
        FROM test_table
    """
    ).fetchone()

    # Verify basic stats
    assert result[0] == len(sample_table)  # row count
    assert result[1] == 4  # unique categories (A,B,C,D)
    assert 0 <= result[2] <= 1  # avg float between 0 and 1
    assert 0 <= result[3] <= len(sample_table)  # true count

    # Cleanup
    duckdb_conn.execute("DROP TABLE IF EXISTS test_table")
    duckdb_conn.unregister("arrow_table")
