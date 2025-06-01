"""Arrow data models."""

import base64
from typing import Any, List, Optional

import pyarrow as pa
from pydantic import BaseModel, Field, field_validator

from ..constants import LZ4_MAX_LEVEL, ZSTD_MAX_LEVEL


class DeltaOptions(BaseModel):
    """Delta Lake specific options."""

    partition_by: List[str] = Field(
        default_factory=list, description="Columns to partition by"
    )
    z_order_by: List[str] = Field(
        default_factory=list, description="Columns for Z-ordering"
    )
    target_file_size: int = Field(
        default=134217728, description="Target file size in bytes (default: 128MB)"
    )
    compression: str = Field(
        default="snappy", description="Compression codec for Parquet files"
    )
    schema_mode: str = Field(
        default="merge", description="Schema evolution mode (merge, overwrite, strict)"
    )


class ArrowStreamConfig(BaseModel):
    """Configuration for an Arrow stream."""

    target_table: str = Field(..., description="Target table")
    storage_backend: Optional[str] = Field(
        default=None, description="Storage backend override (duckdb or delta)"
    )
    chunk_size: int = Field(default=10000, description="Chunk size for processing")
    compression: Optional[dict[str, Any]] = Field(
        default=None, description="Compression settings"
    )
    delta_options: Optional[DeltaOptions] = Field(
        default=None, description="Delta Lake specific options"
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
    storage_backend: str = Field(..., description="Storage backend used")
    message: Optional[str] = Field(default=None, description="Optional message")


class DeltaTableInfo(BaseModel):
    """Delta Lake table information."""

    table: str = Field(..., description="Table name")
    version: int = Field(..., description="Current version")
    file_count: int = Field(..., description="Number of data files")
    total_size_bytes: int = Field(..., description="Total size in bytes")
    row_count: int = Field(..., description="Number of rows")
    partitions: List[str] = Field(default_factory=list, description="Partition columns")
