# 🏹 Arrowport

*Where Arrow streams land gracefully in DuckDB ponds* 🦆

## What is Arrowport? 🤔

Arrowport is a high-performance bridge that helps Arrow data streams find their way into DuckDB's cozy data ponds. Think of it as a friendly air traffic controller for your data - it ensures your Arrow packets land safely, efficiently, and in the right spot!

```python
🏹 Arrow Stream → 🎯 Arrowport → 🦆 DuckDB
```

## Features 🌟

- **High-Performance Data Transfer**: Direct Arrow IPC stream ingestion into DuckDB
- **Native Compression Support**: ZSTD compression for Arrow IPC streams
- **RESTful API**: FastAPI-based endpoints for data ingestion
- **Prometheus Metrics**: Optional metrics endpoint for monitoring
- **Transaction Support**: Atomic operations for data consistency
- **Configurable**: Flexible configuration for compression, chunk sizes, and more

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
uv pip install -e .
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

## Contributing

We welcome contributions! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting:

   ```bash
   # Run all checks
   python -m pytest
   black .
   isort .
   ruff check .
   mypy .
   ```

5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Submit a pull request

## License

MIT License

## Acknowledgments

- [DuckDB team](https://duckdb.org/) for their excellent Arrow integration and support
- [FastAPI team](https://fastapi.tiangolo.com/) for the high-performance framework
- [Apache Arrow team](https://arrow.apache.org/) for the columnar format
- All our contributors and users who make this project better every day

---
