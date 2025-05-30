"""Prometheus metrics for Arrowport."""

from prometheus_client import Counter, Gauge, Histogram

# Stream processing metrics
STREAM_ROWS_TOTAL = Counter(
    "arrowport_stream_rows_total",
    "Total number of rows processed",
    ["stream_name", "target_table"],
)

STREAM_BYTES_TOTAL = Counter(
    "arrowport_stream_bytes_total",
    "Total bytes processed",
    ["stream_name", "compression_algorithm"],
)

STREAM_PROCESSING_TIME = Histogram(
    "arrowport_stream_processing_seconds",
    "Time spent processing streams",
    ["stream_name"],
    buckets=[
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ],
)

# DuckDB metrics
DUCKDB_TRANSACTION_TIME = Histogram(
    "arrowport_duckdb_transaction_seconds",
    "Time spent in DuckDB transactions",
    ["operation"],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0],
)

DUCKDB_ERRORS = Counter(
    "arrowport_duckdb_errors_total", "Total number of DuckDB errors", ["error_type"]
)

# Memory metrics
MEMORY_USAGE = Gauge(
    "arrowport_memory_bytes",
    "Current memory usage",
    ["type"],  # e.g., "arrow_buffer", "duckdb_buffer"
)

# Compression metrics
COMPRESSION_RATIO = Histogram(
    "arrowport_compression_ratio",
    "Compression ratio achieved",
    ["algorithm", "stream_name"],
    buckets=[1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0],
)

# API metrics
HTTP_REQUESTS_TOTAL = Counter(
    "arrowport_http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "arrowport_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0],
)

# Background task metrics
TASK_QUEUE_SIZE = Gauge(
    "arrowport_task_queue_size", "Current size of the background task queue"
)

TASK_PROCESSING_TIME = Histogram(
    "arrowport_task_processing_seconds",
    "Time spent processing background tasks",
    ["task_type"],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0],
)
