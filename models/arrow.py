from typing import Optional, List
from pydantic import BaseModel, Field, validator
import pyarrow as pa

from ..config.settings import settings


class ArrowStreamConfig(BaseModel):
    """Configuration for Arrow IPC stream processing."""

    target_table: str = Field(..., description="Target table name in DuckDB")
    chunk_size: Optional[int] = Field(
        default=settings.default_chunk_size,
        description="Chunk size for processing Arrow IPC stream",
    )
    compression: Optional[dict] = Field(
        default_factory=lambda: {
            "algorithm": settings.compression_algorithm,
            "level": settings.compression_level,
        },
        description="Compression settings for Arrow IPC stream",
    )

    @validator("compression")
    def validate_compression(cls, v):
        """Validate compression settings."""
        if v is None:
            return v

        algorithm = v.get("algorithm", "").lower()
        level = v.get("level", 0)

        if algorithm not in ["zstd", "lz4"]:
            raise ValueError("Compression algorithm must be either 'zstd' or 'lz4'")

        if algorithm == "zstd" and not 1 <= level <= 9:
            raise ValueError("ZSTD compression level must be between 1 and 9")
        elif algorithm == "lz4" and not 1 <= level <= 12:
            raise ValueError("LZ4 compression level must be between 1 and 12")

        return v


class ArrowBatch(BaseModel):
    """Represents a batch of data in Arrow IPC format."""

    schema: dict = Field(..., description="Arrow schema as JSON")
    data: bytes = Field(..., description="Arrow IPC format data")

    def to_arrow_table(self) -> pa.Table:
        """Convert the batch to an Arrow Table."""
        try:
            # Reconstruct the schema
            schema = pa.Schema.from_dict(self.schema)
            # Read the IPC stream
            reader = pa.ipc.open_stream(pa.py_buffer(self.data))
            table = reader.read_all()
            return table
        except Exception as e:
            raise ValueError(f"Failed to convert to Arrow Table: {str(e)}")


class StreamResponse(BaseModel):
    """Response model for stream processing operations."""

    status: str = Field(..., description="Status of the operation")
    rows_processed: int = Field(..., description="Number of rows processed")
    message: Optional[str] = Field(None, description="Additional information")
