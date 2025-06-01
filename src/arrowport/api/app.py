"""FastAPI application for Arrowport."""

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import make_asgi_app

from ..config.settings import settings
from ..constants import HTTP_500_INTERNAL_SERVER_ERROR
from ..core.db import db_manager
from ..core.storage import get_storage_backend
from ..models.arrow import ArrowBatch, ArrowStreamConfig, DeltaTableInfo, StreamResponse

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

        # Determine storage backend
        backend_type = config.storage_backend or settings.storage_backend

        logger.info(
            "Processing Arrow IPC stream",
            stream_name=stream_name,
            target_table=config.target_table,
            rows=rows_count,
            backend=backend_type,
        )

        # Get storage backend
        storage = get_storage_backend(backend_type)

        # Prepare kwargs for backend-specific options
        write_kwargs = {}
        if backend_type == "delta" and config.delta_options:
            write_kwargs.update(config.delta_options.model_dump())

        # Write data
        rows_processed = storage.write(
            table,
            config.target_table,
            mode="append",
            **write_kwargs,
        )

        logger.info(
            "Successfully processed Arrow IPC stream",
            stream_name=stream_name,
            rows_processed=rows_processed,
            backend=backend_type,
        )

        return StreamResponse(
            status="success",
            stream=stream_name,
            rows_processed=rows_processed,
            message="Data processed successfully",
            storage_backend=backend_type,
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


# Delta Lake specific endpoints
@app.post("/delta/{table_name}", response_model=StreamResponse)
async def ingest_to_delta(
    table_name: str,
    batch: ArrowBatch,
    partition_by: Optional[List[str]] = Query(default=None),
    mode: str = Query(default="append", regex="^(append|overwrite)$"),
) -> StreamResponse:
    """Ingest data directly to Delta Lake."""
    try:
        table = batch.to_arrow_table()
        storage = get_storage_backend("delta")

        write_kwargs = {"mode": mode}
        if partition_by:
            write_kwargs["partition_by"] = partition_by

        rows_processed = storage.write(
            table,
            table_name,
            **write_kwargs,
        )

        return StreamResponse(
            status="success",
            stream=table_name,
            rows_processed=rows_processed,
            storage_backend="delta",
        )
    except Exception as e:
        logger.error(
            "Failed to ingest to Delta Lake",
            table=table_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest to Delta Lake: {e!s}",
        ) from e


@app.get("/delta/{table_name}/info", response_model=DeltaTableInfo)
async def get_delta_table_info(table_name: str) -> DeltaTableInfo:
    """Get Delta Lake table information."""
    try:
        storage = get_storage_backend("delta")

        if not storage.table_exists(table_name):
            raise HTTPException(
                status_code=404,
                detail=f"Delta table '{table_name}' not found",
            )

        info = storage.get_table_info(table_name)
        return DeltaTableInfo(**info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get Delta table info",
            table=table_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get table info: {e!s}",
        ) from e


@app.get("/delta/{table_name}/history")
async def get_delta_table_history(
    table_name: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> Dict[str, Any]:
    """Get Delta Lake table history."""
    try:
        storage = get_storage_backend("delta")

        if not storage.table_exists(table_name):
            raise HTTPException(
                status_code=404,
                detail=f"Delta table '{table_name}' not found",
            )

        table_path = storage._get_table_path(table_name)
        from deltalake import DeltaTable

        dt = DeltaTable(table_path)
        history = dt.history(limit=limit)

        return {
            "table": table_name,
            "history": history,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get Delta table history",
            table=table_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get table history: {e!s}",
        ) from e


@app.post("/delta/{table_name}/vacuum")
async def vacuum_delta_table(
    table_name: str,
    retention_hours: int = Query(default=168, ge=0),
) -> Dict[str, Any]:
    """Run vacuum on Delta Lake table."""
    try:
        storage = get_storage_backend("delta")

        if not storage.table_exists(table_name):
            raise HTTPException(
                status_code=404,
                detail=f"Delta table '{table_name}' not found",
            )

        result = storage.vacuum(table_name, retention_hours)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to vacuum Delta table",
            table=table_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to vacuum table: {e!s}",
        ) from e
