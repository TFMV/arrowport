"""Tests for Delta Lake storage backend."""

import tempfile
from pathlib import Path

import pyarrow as pa
import pytest

from arrowport.core.storage import DeltaLakeBackend, get_storage_backend


@pytest.fixture
def delta_backend():
    """Create a Delta Lake backend with temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield DeltaLakeBackend(base_path=tmpdir)


@pytest.fixture
def sample_table():
    """Create a sample Arrow table."""
    return pa.table(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
            "value": [10.5, 20.3, 15.7, 30.2, 25.8],
            "category": ["A", "B", "A", "C", "B"],
        }
    )


def test_delta_write_read(delta_backend, sample_table):
    """Test basic write and read operations."""
    # Write data
    rows_written = delta_backend.write(sample_table, "test_table")
    assert rows_written == 5

    # Check table exists
    assert delta_backend.table_exists("test_table")

    # Read data back
    read_table = delta_backend.read("test_table")
    assert read_table.num_rows == 5
    assert read_table.column_names == sample_table.column_names


def test_delta_append_mode(delta_backend, sample_table):
    """Test appending data to Delta table."""
    # Initial write
    delta_backend.write(sample_table, "append_test")

    # Append more data
    delta_backend.write(sample_table, "append_test", mode="append")

    # Read and verify
    read_table = delta_backend.read("append_test")
    assert read_table.num_rows == 10  # 5 + 5


def test_delta_overwrite_mode(delta_backend, sample_table):
    """Test overwriting data in Delta table."""
    # Initial write
    delta_backend.write(sample_table, "overwrite_test")

    # Overwrite with new data
    new_table = pa.table(
        {
            "id": [10, 11],
            "name": ["Frank", "Grace"],
            "value": [40.1, 35.6],
            "category": ["D", "E"],
        }
    )
    delta_backend.write(new_table, "overwrite_test", mode="overwrite")

    # Read and verify
    read_table = delta_backend.read("overwrite_test")
    assert read_table.num_rows == 2


def test_delta_partitioning(delta_backend, sample_table):
    """Test partitioned Delta table."""
    # Write with partitioning
    delta_backend.write(sample_table, "partitioned_table", partition_by=["category"])

    # Get info and verify partitions
    info = delta_backend.get_table_info("partitioned_table")
    assert info["partitions"] == ["category"]
    assert info["row_count"] == 5


def test_delta_table_info(delta_backend, sample_table):
    """Test getting table information."""
    delta_backend.write(sample_table, "info_test")

    info = delta_backend.get_table_info("info_test")
    assert info["backend"] == "delta"
    assert info["table"] == "info_test"
    assert info["version"] == 0
    assert info["row_count"] == 5
    assert info["file_count"] > 0


def test_delta_time_travel(delta_backend, sample_table):
    """Test time travel functionality."""
    # Write initial data
    delta_backend.write(sample_table, "time_travel_test")

    # Write update
    update_table = pa.table(
        {
            "id": [6, 7],
            "name": ["Helen", "Ivan"],
            "value": [45.2, 50.1],
            "category": ["A", "B"],
        }
    )
    delta_backend.write(update_table, "time_travel_test", mode="append")

    # Read current version
    current_table = delta_backend.read("time_travel_test")
    assert current_table.num_rows == 7

    # Read version 0
    version_0_table = delta_backend.read("time_travel_test", version=0)
    assert version_0_table.num_rows == 5


def test_storage_factory():
    """Test storage backend factory."""
    # Test DuckDB backend
    duckdb_backend = get_storage_backend("duckdb")
    assert duckdb_backend.__class__.__name__ == "DuckDBBackend"

    # Test Delta backend with custom path
    with tempfile.TemporaryDirectory() as tmpdir:
        delta_backend = get_storage_backend("delta", base_path=tmpdir)
        assert delta_backend.__class__.__name__ == "DeltaLakeBackend"
        assert delta_backend.base_path == Path(tmpdir)
