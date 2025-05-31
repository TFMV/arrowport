
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings."""

    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API host to bind to")
    api_port: int = Field(default=8888, description="API port to bind to")

    # Flight Settings
    flight_port: int = Field(default=8889, description="Arrow Flight port to bind to")
    enable_flight: bool = Field(default=True, description="Enable Arrow Flight server")

    # DuckDB Settings
    db_path: str = Field(
        default="arrowport.duckdb", description="Path to DuckDB database file"
    )

    # Compression Settings
    compression_algorithm: str = Field(
        default="zstd", description="Default compression algorithm (zstd or lz4)"
    )
    compression_level: int = Field(
        default=3, description="Compression level (1-9 for zstd, 1-12 for lz4)"
    )

    # Chunk Size Settings
    default_chunk_size: int = Field(
        default=122880, description="Default chunk size for Arrow IPC streams"
    )

    # Monitoring Settings
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Port for Prometheus metrics")

    # Logging Settings
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = SettingsConfigDict(
        env_prefix="ARROWPORT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Create global settings instance
settings = Settings()
