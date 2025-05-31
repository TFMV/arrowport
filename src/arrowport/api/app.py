"""FastAPI application for Arrowport."""

import tempfile
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import make_asgi_app

from ..config.settings import settings
from ..constants import HTTP_500_INTERNAL_SERVER_ERROR
from ..core.arrow import ArrowStream
from ..core.db import db_manager
from ..models.arrow import ArrowBatch, ArrowStreamConfig, StreamResponse

# Configure structured logging
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup
    logger.info(
        "Starting Arrowport",
        host=settings.api_host,
        port=settings.api_port,
    )
    yield
    # Shutdown
    db_manager.close()
    logger.info("Arrowport shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Arrowport",
    description="High-performance bridge from Arrow IPC streams to DuckDB",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics endpoint if enabled
if settings.enable_metrics:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


# Add catch-all route for metrics when disabled
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.enable_metrics:
        return Response(status_code=404)
    return Response(
        status_code=404
    )  # Should never reach here as mount takes precedence


@app.post("/stream/{stream_name}", response_model=StreamResponse)
async def process_stream(
    stream_name: str,
    config: ArrowStreamConfig,
    batch: ArrowBatch,
) -> StreamResponse:
    """Process an Arrow IPC stream."""
    try:
        # Convert batch to Arrow Table
        table = batch.to_arrow_table()
        rows_count = len(table)

        logger.info(
            "Processing Arrow IPC stream",
            stream_name=stream_name,
            target_table=config.target_table,
            rows=rows_count,
        )

        # Process the batch in a transaction
        with db_manager.transaction() as conn:
            # Create table if it doesn't exist using the Arrow table schema
            conn.register(
                "arrow_schema_table", table.slice(0, 0)
            )  # Empty table for schema
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {config.target_table} AS 
            SELECT * FROM arrow_schema_table LIMIT 0
            """
            conn.execute(create_table_sql)

            # Register the full table and insert data
            conn.register("arrow_table", table)
            insert_sql = f"""
            INSERT INTO {config.target_table} 
            SELECT * FROM arrow_table
            """
            conn.execute(insert_sql)

        logger.info(
            "Successfully processed Arrow IPC stream",
            stream_name=stream_name,
            rows_processed=rows_count,
        )

        return StreamResponse(
            status="success",
            stream=stream_name,
            rows_processed=rows_count,
            message="Data processed successfully",
        )

    except Exception as e:
        logger.error(
            "Failed to process stream",
            stream=stream_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process stream: {e!s}",
        ) from e
