# 🏹 Arrowport

*Where Arrow streams land gracefully in DuckDB ponds* 🦆

## What is Arrowport? 🤔

Arrowport is a high-performance bridge that helps Arrow data streams find their way into DuckDB's cozy data ponds. Think of it as a friendly air traffic controller for your data - it ensures your Arrow packets land safely, efficiently, and in the right spot!

## Features 🌟

- **Dual Protocol Support**:
  - REST API with ZSTD compression
  - Native Arrow Flight server
- **Zero-Copy Data Transfer**: Direct Arrow-to-DuckDB integration without intermediate conversions
- **Automatic Schema Handling**: Automatic table creation and schema mapping
- **Transaction Support**: ACID-compliant transactions for data safety
- **Configurable Streams**: Dynamic stream configuration with sensible defaults

## Installation

### Prerequisites

- Python 3.9 or higher
- DuckDB 1.3.0 or higher
- PyArrow 20.0.0 or higher

### Using pip

```bash
pip install arrowport
```

### From Source

```bash
git clone https://github.com/yourusername/arrowport.git
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

## Configuration ��️

Configuration is handled through environment variables or a YAML file:

```yaml
# config.yaml
api:
  host: "127.0.0.1"
  port: 8000
  enable_metrics: true
  metrics_port: 9090

duckdb:
  path: "data/db.duckdb"
  
compression:
  algorithm: "zstd"
  level: 3

defaults:
  chunk_size: 10000
```

Environment variables take precedence over the config file:

```bash
export ARROWPORT_API_HOST="0.0.0.0"
export ARROWPORT_API_PORT=8888
export ARROWPORT_ENABLE_METRICS=true
```

## API Reference

### POST /stream/{stream_name}

Process an Arrow IPC stream and load it into DuckDB.

**Parameters**:

- `stream_name`: Identifier for the stream (string)

**Request Body**:

```json
{
  "config": {
    "target_table": "string",
    "chunk_size": 10000,
    "compression": {
      "algorithm": "zstd",
      "level": 3
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
  "message": "Data processed successfully"
}
```

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
- **PyArrow**: Apache Arrow implementation for Python
- **Pydantic**: Data validation using Python type annotations
- **Structlog**: Structured logging
- **Prometheus Client**: Metrics collection and exposure

The system follows a modular architecture:

```
arrowport/
├── api/          # FastAPI application and endpoints
├── core/         # Core functionality (Arrow, DuckDB)
├── config/       # Configuration management
├── models/       # Pydantic models
└── utils/        # Utility functions
```

### Data Flow

1. Client sends Arrow IPC stream with schema
2. API endpoint validates request and configuration
3. Arrow stream is written to temporary file
4. DuckDB reads the Arrow stream directly using `read_arrow`
5. Data is inserted into target table in a transaction
6. Response is sent with processing status

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
