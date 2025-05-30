"""Arrow data models."""

import base64
from typing import Any, Optional

import pyarrow as pa
from pydantic import BaseModel, Field, field_validator

from ..constants import LZ4_MAX_LEVEL, ZSTD_MAX_LEVEL


class ArrowStreamConfig(BaseModel):
    """Configuration for an Arrow stream."""

    target_table: str = Field(..., description="Target table in DuckDB")
    chunk_size: int = Field(default=10000, description="Chunk size for processing")
    compression: Optional[dict[str, Any]] = Field(
        default=None, description="Compression settings"
    )

    @field_validator("compression")
    @classmethod
    def validate_compression(
        cls, v: Optional[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """Validate compression settings."""
        if v is None:
            return None

        algorithm = v.get("algorithm")
        level = v.get("level", 1)

        if algorithm not in ["zstd", "lz4"]:
            raise ValueError("Compression algorithm must be either 'zstd' or 'lz4'")

        if algorithm == "zstd" and not 1 <= level <= ZSTD_MAX_LEVEL:
            raise ValueError(
                f"ZSTD compression level must be between 1 and {ZSTD_MAX_LEVEL}"
            )
        elif algorithm == "lz4" and not 1 <= level <= LZ4_MAX_LEVEL:
            raise ValueError(
                f"LZ4 compression level must be between 1 and {LZ4_MAX_LEVEL}"
            )

        return v


class ArrowBatch(BaseModel):
    """Arrow IPC batch data."""

    arrow_schema: str = Field(..., description="Base64-encoded Arrow schema")
    data: str = Field(..., description="Base64-encoded Arrow IPC stream")

    def to_arrow_table(self) -> pa.Table:
        """Convert the batch data to an Arrow table."""
        try:
            data_bytes = base64.b64decode(self.data)
            reader = pa.ipc.open_stream(pa.py_buffer(data_bytes))
            table = reader.read_all()
            return table
        except Exception as e:
            raise ValueError(f"Failed to convert to Arrow Table: {e!s}") from e


class StreamResponse(BaseModel):
    """Response for stream processing."""

    status: str = Field(..., description="Processing status")
    stream: str = Field(..., description="Stream name")
    rows_processed: int = Field(..., description="Number of rows processed")
