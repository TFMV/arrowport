from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog

from ..config.settings import settings
from ..core.db import db_manager
from ..models.arrow import ArrowBatch, ArrowStreamConfig, StreamResponse

# Configure structured logging
logger = structlog.get_logger()

# Create FastAPI application
app = FastAPI(
    title="Arrowport",
    description="A high-performance bridge from Arrow IPC streams to DuckDB",
    version="0.1.0",
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


@app.post("/stream/{stream_name}", response_model=StreamResponse)
async def process_stream(
    stream_name: str,
    config: ArrowStreamConfig,
    batch: ArrowBatch,
    background_tasks: BackgroundTasks,
) -> StreamResponse:
    """
    Process an Arrow IPC stream and load it into DuckDB.

    Args:
        stream_name: Name of the stream (used for logging and metrics)
        config: Stream configuration including target table and processing options
        batch: Arrow IPC batch data
        background_tasks: FastAPI background tasks for async processing

    Returns:
        StreamResponse with processing status and statistics
    """
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
            # Create table if it doesn't exist (schema inference)
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {config.target_table} AS 
            SELECT * FROM arrow_table LIMIT 0
            """
            conn.execute(create_table_sql)

            # Insert data
            insert_sql = f"INSERT INTO {config.target_table} SELECT * FROM arrow_table"
            conn.execute(insert_sql)

        logger.info(
            "Successfully processed Arrow IPC stream",
            stream_name=stream_name,
            rows_processed=rows_count,
        )

        return StreamResponse(
            status="success",
            rows_processed=rows_count,
            message="Data processed successfully",
        )

    except Exception as e:
        logger.error(
            "Failed to process Arrow IPC stream",
            stream_name=stream_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process stream: {str(e)}",
        )


@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup."""
    logger.info(
        "Starting Arrowport",
        host=settings.api_host,
        port=settings.api_port,
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown."""
    db_manager.close()
    logger.info("Arrowport shutdown complete")
