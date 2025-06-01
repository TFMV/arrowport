# 🏹 Arrowport

[![PyPI version](https://badge.fury.io/py/arrowport.svg)](https://badge.fury.io/py/arrowport)
[![Python Versions](https://img.shields.io/pypi/pyversions/arrowport.svg)](https://pypi.org/project/arrowport/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Development Status](https://img.shields.io/pypi/status/arrowport.svg)](https://pypi.org/project/arrowport/)

*Where Arrow streams land gracefully in DuckDB ponds* 🦆

## What is Arrowport? 🤔

Arrowport is a high-performance bridge that helps Arrow data streams find their way into DuckDB's cozy data ponds. Think of it as a friendly air traffic controller for your data - it ensures your Arrow packets land safely, efficiently, and in the right spot!

## 🎉 New in v0.2.0: Delta Lake Support

Arrowport now supports **Delta Lake** as an alternative storage backend to DuckDB! This gives you:

- 🔄 **ACID Transactions** with multi-writer support
- ⏰ **Time Travel** - query data as of any version
- 📊 **Schema Evolution** - safely evolve table schemas
- 🗂️ **Partitioning** - efficient data organization
- 🔍 **Z-Ordering** - optimize for query patterns
- 🌐 **Ecosystem Integration** - works with Spark, Databricks, and more!

## Features 🌟

- **Dual Storage Backends**:
  - DuckDB for OLAP workloads
  - Delta Lake for data lake scenarios (NEW!)
- **Dual Protocol Support**:
  - REST API with ZSTD compression
  - Native Arrow Flight server
- **Zero-Copy Data Transfer**: Direct Arrow-to-DuckDB/Delta integration without intermediate conversions
- **Automatic Schema Handling**: Automatic table creation and schema mapping
- **Transaction Support**: ACID-compliant transactions for data safety
- **Configurable Streams**: Dynamic stream configuration with sensible defaults
- **Time Travel Queries**: Query historical data with Delta Lake
- **Data Organization**: Partitioning and Z-ordering support

## Installation

### Prerequisites

- Python 3.9 or higher
- DuckDB 1.3.0 or higher
- PyArrow 20.0.0 or higher
- Delta Lake 0.15.0 or higher (for Delta backend)

### Using pip

```bash
pip install arrowport
```

### From Source

```bash
git clone https://github.com/TFMV/arrowport.git
cd arrowport

# Using uv (recommended for faster installs)
uv pip install -e .

# Or using traditional pip
pip install -e .
```

## Quick Start 🚀

1. **Start the Arrowport server:**

```bash
arrowport serve
```

2. **Send data using Python:**

### DuckDB Backend (Default)

```python
import pyarrow as pa
import requests
import base64

# Create sample data
data = pa.table({'a': [1, 2, 3], 'b': ['foo', 'bar', 'baz']})

# Convert to IPC format
sink = pa.BufferOutputStream()
writer = pa.ipc.new_stream(sink, data.schema)
writer.write_table(data)
writer.close()

# Send to Arrowport
response = requests.post(
    "http://localhost:8000/stream/my_stream",
    json={
        "config": {
            "target_table": "my_table",
            "compression": {"algorithm": "zstd", "level": 3}
        },
        "batch": {
            "arrow_schema": base64.b64encode(data.schema.serialize()).decode(),
            "data": base64.b64encode(sink.getvalue().to_pybytes()).decode()
        }
    }
)
```

### Delta Lake Backend (NEW!)

```python
# Send to Delta Lake with partitioning
response = requests.post(
    "http://localhost:8888/stream/events",
    json={
        "config": {
            "target_table": "events",
            "storage_backend": "delta",
            "delta_options": {
                "partition_by": ["date", "event_type"],
                "z_order_by": ["user_id"],
                "schema_mode": "merge"  # Allow schema evolution
            }
        },
        "batch": {
            "arrow_schema": base64.b64encode(data.schema.serialize()).decode(),
            "data": base64.b64encode(sink.getvalue().to_pybytes()).decode()
        }
    }
)
```

## CLI Usage

### DuckDB Operations

```bash
# List configured streams
arrowport streams

# Ingest Arrow file to DuckDB
arrowport ingest my_stream data.arrow

# Ingest with specific backend
arrowport ingest my_stream data.arrow --backend duckdb
```

### Delta Lake Operations (NEW!)

```bash
# List Delta tables
arrowport delta list

# Show table history
arrowport delta history events --limit 10

# Vacuum old files (dry run)
arrowport delta vacuum events --retention-hours 168

# Actually vacuum
arrowport delta vacuum events --retention-hours 168 --no-dry-run

# Restore to previous version
arrowport delta restore events 5

# Ingest to Delta with partitioning
arrowport ingest events data.arrow --backend delta --partition-by date --partition-by event_type
```

## Configuration 🛠️

Configuration is handled through environment variables or a YAML file:

```yaml
# config.yaml
api:
  host: "127.0.0.1"
  port: 8000
  enable_metrics: true
  metrics_port: 9090

# Storage backend configuration
storage_backend: duckdb  # or 'delta'

duckdb:
  path: "data/db.duckdb"

# Delta Lake configuration (NEW!)
delta_config:
  table_path: "./delta_tables"
  version_retention_hours: 168  # 7 days
  checkpoint_interval: 10
  enable_cdc: false
  
compression:
  algorithm: "zstd"
  level: 3

defaults:
  chunk_size: 10000

# Stream-specific configuration
streams:
  # DuckDB example
  sensor_data:
    target_table: sensors
    storage_backend: duckdb
    chunk_size: 122880
    compression:
      algorithm: zstd
      level: 3

  # Delta Lake example
  events:
    target_table: event_log
    storage_backend: delta
    delta_options:
      partition_by: ["date", "event_type"]
      z_order_by: ["user_id"]
      target_file_size: 134217728  # 128MB
      compression: snappy
      schema_mode: merge
```

Environment variables take precedence over the config file:

```bash
export ARROWPORT_API_HOST="0.0.0.0"
export ARROWPORT_API_PORT=8888
export ARROWPORT_ENABLE_METRICS=true
export ARROWPORT_STORAGE_BACKEND=delta
```

## API Reference

### Stream Endpoints

#### POST /stream/{stream_name}

Process an Arrow IPC stream and load it into DuckDB or Delta Lake.

**Parameters**:

- `stream_name`: Identifier for the stream (string)

**Request Body**:

```json
{
  "config": {
    "target_table": "string",
    "storage_backend": "duckdb",  // or "delta"
    "chunk_size": 10000,
    "compression": {
      "algorithm": "zstd",
      "level": 3
    },
    "delta_options": {  // Delta Lake specific
      "partition_by": ["date"],
      "z_order_by": ["user_id"],
      "schema_mode": "merge"
    }
  },
  "batch": {
    "arrow_schema": "base64-encoded Arrow schema",
    "data": "base64-encoded Arrow IPC stream"
  }
}
```

**Response**:

```json
{
  "status": "success",
  "stream": "stream_name",
  "rows_processed": 1000,
  "storage_backend": "duckdb",
  "message": "Data processed successfully"
}
```

### Delta Lake Endpoints (NEW!)

#### POST /delta/{table_name}

Direct Delta Lake ingestion endpoint.

#### GET /delta/{table_name}/info

Get Delta Lake table information including version, file count, and size.

#### GET /delta/{table_name}/history

View table history with version information.

#### POST /delta/{table_name}/vacuum

Clean up old files with configurable retention period.

### GET /metrics

Prometheus metrics endpoint (if enabled).

Example metrics:

```
# Total rows processed by stream
arrowport_rows_processed_total{stream="example"} 1000

# Ingest latency histogram
arrowport_ingest_latency_seconds_bucket{le="0.1",stream="example"} 42
arrowport_ingest_latency_seconds_bucket{le="0.5",stream="example"} 197
arrowport_ingest_latency_seconds_bucket{le="1.0",stream="example"} 365

# Active connections
arrowport_active_connections{protocol="flight"} 5
arrowport_active_connections{protocol="rest"} 3
```

## Architecture

Arrowport is built on modern Python technologies:

- **FastAPI**: High-performance web framework
- **DuckDB**: Embedded analytical database
- **Delta Lake**: Open-source storage layer for data lakes
- **PyArrow**: Apache Arrow implementation for Python
- **Pydantic**: Data validation using Python type annotations
- **Structlog**: Structured logging
- **Prometheus Client**: Metrics collection and exposure

The system follows a modular architecture:

```
arrowport/
├── api/          # FastAPI application and endpoints
├── core/         # Core functionality (Arrow, DuckDB, Storage)
├── config/       # Configuration management
├── models/       # Pydantic models
└── utils/        # Utility functions
```

### Updated Architecture Diagram

```text
                                   ┌──────────────────┐
        Arrow IPC                  │ Arrowport Server │
┌───────────────┐  HTTP/Flight    │                  │
│  Producers    │────────────────▶│  FastAPI +       │
│ (Polars etc.) │                 │  Flight Server   │
└───────────────┘                 └────────┬─────────┘
                                          │
                           DuckDB SQL     ▼          Delta Lake API
                                   ┌────────────┐    ┌──────────────┐
                                   │  DuckDB    │    │  Delta Lake  │
                                   │ .duckdb    │ OR │  (Parquet +  │
                                   │            │    │   _delta_log)│
                                   └────────────┘    └──────────────┘
```

### Data Flow

1. **Client Sends Data**: Two protocols are supported:

   a) **REST API**:

   ```python
   # Client serializes Arrow table and sends as base64-encoded IPC stream
   sink = pa.BufferOutputStream()
   writer = pa.ipc.new_stream(sink, table.schema)
   writer.write_table(table)
   
   response = requests.post(
       "http://localhost:8000/stream/my_stream",
       json={
           "config": {
               "target_table": "my_table",
               "compression": {"algorithm": "zstd", "level": 3}
           },
           "batch": {
               "arrow_schema": base64.b64encode(table.schema.serialize()).decode(),
               "data": base64.b64encode(sink.getvalue().to_pybytes()).decode()
           }
       }
   )
   ```

   b) **Arrow Flight**:

   ```python
   # Client connects directly using Arrow Flight protocol
   client = flight.FlightClient("grpc://localhost:8889")
   descriptor = flight.FlightDescriptor.for_command(
       json.dumps({"stream_name": "my_stream"}).encode()
   )
   writer, _ = client.do_put(descriptor, table.schema)
   writer.write_table(table)
   writer.close()
   ```

2. **Server Processing**:

   a) **REST API Path**:
   - Decodes base64 Arrow schema and data
   - Converts to Arrow Table using `ArrowBatch.to_arrow_table()`
   - Determines storage backend (DuckDB or Delta Lake)
   - For DuckDB: Uses transaction for atomic operations
   - For Delta Lake: Uses write_deltalake with specified options
   - Creates target table if needed using Arrow schema
   - Executes data transfer with zero-copy optimization

   b) **Flight Path**:
   - Receives Arrow data directly via gRPC
   - Reads complete table using `reader.read_all()`
   - Gets stream configuration for target table
   - Routes to appropriate storage backend
   - Executes INSERT/append in a single operation

3. **Storage Integration**:

   **DuckDB**:
   - Zero-copy data transfer using `register_arrow()`
   - Automatic schema mapping from Arrow to DuckDB types
   - Transaction-safe data loading
   - Proper cleanup and unregistration of temporary tables

   **Delta Lake**:
   - Direct Arrow Table write using Rust engine
   - Automatic partitioning and file organization
   - Schema evolution with merge mode
   - ACID transactions with optimistic concurrency

4. **Response Handling**:
   - REST API returns JSON with rows processed and status
   - Flight protocol completes the put operation
   - Both methods include proper error handling and logging
   - Metrics are collected for monitoring (if enabled)
   - Storage backend information included in response

## Example: Time Travel with Delta Lake

```python
# Query current version
current_data = requests.get(
    "http://localhost:8888/delta/events/info"
).json()
print(f"Current version: {current_data['version']}")

# View history
history = requests.get(
    "http://localhost:8888/delta/events/history?limit=5"
).json()

# Restore to previous version (via CLI)
# arrowport delta restore events 10
```

## Performance Tips

### DuckDB

- Align chunk sizes with row groups (122,880 rows)
- Use ZSTD compression for better ratios
- Single-writer for maximum performance

### Delta Lake

- Use partitioning for large datasets
- Z-order by common query columns
- Run periodic vacuum operations
- Use merge schema mode for flexibility

## Development

### Setting Up Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=arrowport

# Run specific test file
python -m pytest tests/test_api.py
```

### Code Style

The project uses:

- Black for code formatting
- isort for import sorting
- Ruff for linting
- MyPy for type checking

Run formatters:

```bash
black .
isort .
```

## Performance Considerations

- Uses DuckDB's native Arrow support for zero-copy data transfer
- ZSTD compression for efficient network transfer
- Configurable chunk sizes for memory management
- Transaction support for data consistency

## Performance Benchmarks

> 📊 **Note**: For detailed benchmarks including system specifications, raw data, and
> reproducibility instructions, see [docs/benchmarks.md](docs/benchmarks.md)

Recent benchmarks show impressive performance characteristics across different data sizes:

### Small Dataset (1,000 rows)

| Method | Compression | Rows/Second |
|--------|------------|-------------|
| REST API | None | 3,578 |
| REST API | ZSTD | 252,122 |
| Flight | N/A | 3,817 |

### Medium Dataset (100,000 rows)

| Method | Compression | Rows/Second |
|--------|------------|-------------|
| REST API | None | 1,864,806 |
| REST API | ZSTD | 1,909,340 |
| Flight | N/A | 5,527,039 |

### Large Dataset (1,000,000 rows)

| Method | Compression | Rows/Second |
|--------|------------|-------------|
| REST API | None | 2,399,843 |
| REST API | ZSTD | 2,640,097 |
| Flight | N/A | 19,588,201 |

### Key Findings

1. **Arrow Flight Performance**: The Flight server shows exceptional performance for larger datasets, reaching nearly 20M rows/second for 1M rows. This is achieved because Arrow Flight:
   - Avoids HTTP parsing and JSON serialization overhead
   - Streams binary Arrow data directly over gRPC
   - Uses pre-negotiated schemas for efficient data transfer
   - Leverages zero-copy optimizations where possible
2. **ZSTD Compression Benefits**: ZSTD compression significantly improves REST API performance, especially for smaller datasets.
3. **Scalability**: Both implementations scale well, but Flight's zero-copy approach provides substantial advantages at scale.
4. **Use Case Recommendations**:
   - Use Flight for high-throughput, large dataset operations
   - Use REST API with ZSTD for smaller datasets or when Flight setup isn't feasible

## Implementation Details

### DuckDB Integration

- Zero-copy Arrow data registration
- Automatic schema mapping from Arrow to DuckDB types
- Transaction-safe data loading
- Connection pooling and management

### Arrow Flight Server

- Native gRPC-based implementation
- Streaming data transfer
- Automatic server health checking
- Configurable host/port binding

### REST API

- FastAPI-based implementation
- ZSTD compression support
- Base64-encoded Arrow IPC stream transfer
- Configurable compression levels

## Usage

### REST API

```python
import requests
import pyarrow as pa
import base64

# Prepare Arrow data
table = pa.Table.from_pydict({
    "id": range(1000),
    "value": [1.0] * 1000
})

# Serialize to Arrow IPC format
sink = pa.BufferOutputStream()
writer = pa.ipc.new_stream(sink, table.schema)
writer.write_table(table)
writer.close()

# Send to server
response = requests.post(
    "http://localhost:8888/stream/example",
    json={
        "config": {
            "target_table": "example",
            "compression": {"algorithm": "zstd", "level": 3}
        },
        "batch": {
            "arrow_schema": base64.b64encode(table.schema.serialize()).decode(),
            "data": base64.b64encode(sink.getvalue().to_pybytes()).decode()
        }
    }
)
```

### Arrow Flight

```python
import pyarrow as pa
import pyarrow.flight as flight

# Prepare data
table = pa.Table.from_pydict({
    "id": range(1000),
    "value": [1.0] * 1000
})

# Connect to Flight server
client = flight.FlightClient("grpc://localhost:8889")

# Send data
descriptor = flight.FlightDescriptor.for_command(
    json.dumps({"stream_name": "example"}).encode()
)
writer, _ = client.do_put(descriptor, table.schema)
writer.write_table(table)
writer.close()
```

## Running Benchmarks

```bash
python -m arrowport.benchmarks.benchmark
```

## License

MIT
