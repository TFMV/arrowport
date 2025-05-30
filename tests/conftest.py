"""Test configuration and fixtures."""

import os
import tempfile

import pyarrow as pa
import pytest
from arrowport.api.app import app
from arrowport.config.settings import Settings
from arrowport.core.db import DuckDBManager
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_settings():
    """Create test settings with temporary paths."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.duckdb")
        settings = Settings(
            db_path=db_path,
            api_host="127.0.0.1",
            api_port=8889,
            enable_metrics=False,
        )
        yield settings


@pytest.fixture
def test_db(test_settings):
    """Test DuckDB instance."""
    db = DuckDBManager(db_path=test_settings.db_path)
    yield db
    db.close()
    if os.path.exists(test_settings.db_path):
        os.remove(test_settings.db_path)


@pytest.fixture
def sample_arrow_table():
    """Create a sample Arrow table for testing."""
    data = {
        "id": pa.array([1, 2, 3, 4, 5]),
        "name": pa.array(["a", "b", "c", "d", "e"]),
        "value": pa.array([1.0, 2.0, 3.0, 4.0, 5.0]),
    }
    return pa.Table.from_pydict(data)


@pytest.fixture
def stream_config():
    """Sample stream configuration."""
    return {
        "streams": {
            "test_stream": {
                "target_table": "test_table",
                "chunk_size": 1000,
                "compression": {"algorithm": "zstd", "level": 3},
            }
        }
    }


@pytest.fixture
def sample_table():
    """Create a sample Arrow table for testing."""
    data = {"a": [1, 2, 3], "b": ["foo", "bar", "baz"]}
    return pa.Table.from_pydict(data)
