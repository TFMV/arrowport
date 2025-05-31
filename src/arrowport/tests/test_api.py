"""Tests for API endpoints."""

import base64

import pyarrow as pa
import pytest
from arrowport.api.app import app
from arrowport.constants import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from arrowport.models.arrow import ArrowStreamConfig
from fastapi.testclient import TestClient

# Test constants
TEST_ROW_COUNT = 3


@pytest.fixture
def test_client():
    """Create a test client."""
    return TestClient(app)


def test_process_stream(test_client, sample_table):
    """Test stream processing endpoint."""
    # Convert table to IPC format
    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_stream(sink, sample_table.schema)
    writer.write_table(sample_table)
    writer.close()

    # Create request data
    config = ArrowStreamConfig(
        target_table="test_table",
        chunk_size=1000,
        compression={"algorithm": "zstd", "level": 3},
    )

    # Send request
    response = test_client.post(
        "/stream/test_stream",
        json={
            "config": config.model_dump(),
            "batch": {
                "arrow_schema": base64.b64encode(
                    sample_table.schema.serialize()
                ).decode("utf-8"),
                "data": base64.b64encode(sink.getvalue().to_pybytes()).decode("utf-8"),
            },
        },
    )

    # Verify response
    assert response.status_code == HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["stream"] == "test_stream"
    assert data["rows_processed"] == TEST_ROW_COUNT


def test_process_stream_invalid_data(test_client):
    """Test stream processing with invalid data."""
    response = test_client.post(
        "/stream/test_stream",
        json={
            "config": {
                "target_table": "test_table",
                "chunk_size": 1000,
            },
            "batch": {
                "arrow_schema": "invalid",
                "data": "invalid",
            },
        },
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR


def test_metrics_endpoint(test_client, test_settings):
    """Test metrics endpoint if enabled."""
    if test_settings.enable_metrics:
        response = test_client.get("/metrics")
        assert response.status_code == HTTP_200_OK
        assert "arrowport_" in response.text
    else:
        response = test_client.get("/metrics")
        assert response.status_code == HTTP_404_NOT_FOUND
