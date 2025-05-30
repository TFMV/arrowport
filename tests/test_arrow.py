"""Tests for Arrow IPC functionality."""

import tempfile

import duckdb
import pyarrow as pa
import pytest
from arrowport.core.arrow import ArrowStream


@pytest.fixture(scope="session")
def duckdb_conn():
    """Create a DuckDB connection with Arrow extension loaded."""
    conn = duckdb.connect()
    conn.install_extension("arrow")
    conn.load_extension("arrow")
    return conn


@pytest.fixture
def sample_table():
    """Create a sample Arrow table."""
    data = {"a": [1, 2, 3], "b": ["foo", "bar", "baz"]}
    return pa.Table.from_pydict(data)


def test_arrow_uncompressed(sample_table, duckdb_conn):
    """Test Arrow IPC without compression."""
    stream = ArrowStream()

    with tempfile.NamedTemporaryFile(suffix=".arrows") as f:
        # Write table
        stream.write_table(sample_table, f.name)

        # Read with DuckDB
        result = duckdb_conn.execute(f"SELECT * FROM read_arrow('{f.name}')").fetchall()

        # Verify data
        assert len(result) == len(sample_table)
        assert result[0][0] == 1  # First row, first column
        assert result[0][1] == "foo"  # First row, second column


def test_arrow_compressed(sample_table, duckdb_conn):
    """Test Arrow IPC with ZSTD compression."""
    stream = ArrowStream(compression="zstd")

    with tempfile.NamedTemporaryFile(suffix=".arrows") as f:
        # Write table
        stream.write_table(sample_table, f.name)

        # Read with DuckDB
        result = duckdb_conn.execute(f"SELECT * FROM read_arrow('{f.name}')").fetchall()

        # Verify data
        assert len(result) == len(sample_table)
        assert result[0][0] == 1  # First row, first column
        assert result[0][1] == "foo"  # First row, second column
