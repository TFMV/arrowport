# 🏹 Arrowport

*Where Arrow streams land gracefully in DuckDB ponds* 🦆

> Status: Early Development.

## What is Arrowport? 🤔

Arrowport is a high-performance bridge that helps Arrow data streams find their way into DuckDB's cozy data ponds. Think of it as a friendly air traffic controller for your data - it ensures your Arrow packets land safely, efficiently, and in the right spot!

```python
🏹 Arrow Stream → 🎯 Arrowport → 🦆 DuckDB
```

## Features 🌟

- **Zero-Copy Landing** 🛬
  - Your data touches down without unnecessary copies
  - Native Arrow → DuckDB pathways
  - As smooth as a duck gliding on water

- **Compression Options** 🗜️
  - ZSTD for the storage-conscious
  - LZ4 for the speed demons
  - Configure per stream, because one size doesn't fit all!

- **Hot-Reloadable Config** 🔥
  - Change routes mid-flight
  - No restart required
  - YAML-based for human happiness

- **Prometheus Metrics** 📊
  - Watch your data flow
  - Track your landings
  - Monitor your pond health

## Quick Start 🚀

1. **Install Arrowport:**

```bash
pip install arrowport  # Coming soon to PyPI!
# For now:
git clone https://github.com/yourusername/arrowport.git
cd arrowport
poetry install
```

2. **Create a stream config:**

```yaml
streams:
  sensor_readings:
    target_table: sensor_data
    compression:
      algorithm: zstd
      level: 3  # Balanced, like a duck on one leg
```

3. **Launch the server:**

```bash
python -m arrowport
```

4. **Send some data:**

```python
import pyarrow as pa
import requests

# Prepare your Arrow data
table = pa.table(...)

# Send it to Arrowport
sink = pa.BufferOutputStream()
writer = pa.ipc.new_stream(sink, table.schema)
writer.write_table(table)
writer.close()

requests.post(
    "http://localhost:8888/stream/sensor_readings",
    data=sink.getvalue().to_pybytes()
)
```

## Why Arrowport? 🎯

Because getting data from A(rrow) to D(uckDB) shouldn't require a PhD in data engineering! We handle the complexities of:

- Schema inference
- Transaction management
- Batch processing
- Error recovery
- Performance monitoring

All while keeping it as simple as feeding bread to ducks! 🦆🍞

## Configuration 🛠️

Arrowport is as configurable as a Swiss Army knife, but with sensible defaults that work out of the box. Here's a taste:

```yaml
# config/streams.yaml
streams:
  metrics:
    target_table: metrics
    chunk_size: 61440  # Smaller chunks for real-time data
    compression:
      algorithm: zstd
      level: 1  # Speed over size for metrics

  logs:
    target_table: system_logs
    chunk_size: 245760  # Larger chunks for logs
    compression:
      algorithm: lz4
      level: 6  # Balance is key
```

## Performance 🏃‍♂️

Arrowport is built for speed:

- Zero-copy data transfer where possible
- Efficient compression options
- Background processing with retries
- Transaction-based writes

Think of it as a duck: calm and graceful on the surface, but paddling efficiently underneath! 🦆💨

## Monitoring 📊

Keep an eye on your data flow with built-in Prometheus metrics:

- Request rates
- Processing times
- Error counts
- Resource usage

All accessible via `/metrics` - because observability shouldn't be an afterthought!

## Contributing 🤝

We welcome contributions! Whether you're fixing bugs, adding features, or improving documentation, we'd love to have you aboard.

Check out our [Contributing Guide](CONTRIBUTING.md) to get started.

## License 📜

Arrowport is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

Special thanks to:

- The DuckDB team for their amazing database
- The Apache Arrow project for their fantastic format
- All the open source projects that make this possible

---
