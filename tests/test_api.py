import pytest
import pyarrow as pa
from ..models.arrow import ArrowBatch, ArrowStreamConfig


def test_process_stream_success(test_client, sample_arrow_table):
    """Test successful stream processing."""
    # Prepare the request data
    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_stream(sink, sample_arrow_table.schema)
    writer.write_table(sample_arrow_table)
    writer.close()

    config = ArrowStreamConfig(
        target_table="test_table",
        chunk_size=1000,
        compression={"algorithm": "zstd", "level": 3},
    )

    response = test_client.post(
        "/stream/test_stream",
        json={
            "config": config.model_dump(),
            "batch": {
                "schema": sample_arrow_table.schema.to_dict(),
                "data": sink.getvalue().to_pybytes(),
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["rows_processed"] == 5


def test_process_stream_invalid_data(test_client):
    """Test stream processing with invalid data."""
    response = test_client.post(
        "/stream/test_stream",
        json={
            "config": {"target_table": "test_table"},
            "batch": {"schema": {}, "data": b"invalid data"},
        },
    )

    assert response.status_code == 422


def test_metrics_endpoint(test_client, test_settings):
    """Test metrics endpoint if enabled."""
    if test_settings.enable_metrics:
        response = test_client.get("/metrics")
        assert response.status_code == 200
        assert "arrowport_" in response.text
    else:
        response = test_client.get("/metrics")
        assert response.status_code == 404
