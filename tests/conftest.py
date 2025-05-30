import os
import pytest
import tempfile
from pathlib import Path
import duckdb
import pyarrow as pa
from fastapi.testclient import TestClient

from ..api.app import app
from ..core.db import DuckDBManager
from ..config.settings import Settings
from ..config.streams import StreamConfigManager


@pytest.fixture
def test_settings():
    """Test settings with temporary paths."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.duckdb")
        config_path = os.path.join(temp_dir, "streams.yaml")

        settings = Settings(
            db_path=db_path,
            api_host="127.0.0.1",
            api_port=8889,
            enable_metrics=False,
        )
        return settings


@pytest.fixture
def test_db(test_settings):
    """Test DuckDB instance."""
    db = DuckDBManager(db_path=test_settings.db_path)
    yield db
    db.close()
    if os.path.exists(test_settings.db_path):
        os.remove(test_settings.db_path)


@pytest.fixture
def test_client(test_settings):
    """Test FastAPI client."""
    with TestClient(app) as client:
        yield client


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
