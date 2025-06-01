# 🎉 Arrowport v0.2.0 Release Notes

We're thrilled to announce **Arrowport v0.2.0**, featuring **Delta Lake support** as an alternative storage backend!

## 🌟 Highlights

### Delta Lake Integration

Arrowport now supports Delta Lake alongside DuckDB, giving you the flexibility to choose the best storage backend for your use case:

- **ACID Transactions**: Full transactional guarantees with multi-writer support
- **Time Travel**: Query your data as it existed at any point in time
- **Schema Evolution**: Safely evolve schemas without breaking existing queries
- **Data Organization**: Partition and Z-order your data for optimal query performance

## 🚀 Quick Example

```python
# Ingest to Delta Lake with partitioning
response = requests.post(
    "http://localhost:8888/stream/events",
    json={
        "config": {
            "target_table": "events",
            "storage_backend": "delta",
            "delta_options": {
                "partition_by": ["date", "event_type"],
                "schema_mode": "merge"
            }
        },
        "batch": {
            "arrow_schema": base64.b64encode(table.schema.serialize()).decode(),
            "data": base64.b64encode(sink.getvalue().to_pybytes()).decode()
        }
    }
)
```

## 📚 New Features

### API Endpoints

- `POST /delta/{table_name}` - Direct Delta Lake ingestion
- `GET /delta/{table_name}/info` - Table metadata and statistics
- `GET /delta/{table_name}/history` - Version history
- `POST /delta/{table_name}/vacuum` - Clean up old files

### CLI Commands

```bash
# List Delta tables
arrowport delta list

# View table history
arrowport delta history events

# Time travel restore
arrowport delta restore events 10

# Clean up old files
arrowport delta vacuum events --retention-hours 168 --no-dry-run
```

### Configuration

```yaml
streams:
  events:
    storage_backend: delta
    delta_options:
      partition_by: ["date", "event_type"]
      z_order_by: ["user_id"]
      compression: snappy
      schema_mode: merge
```

## 🔄 Migration

Existing Arrowport installations will continue to work with DuckDB as the default backend. To use Delta Lake:

1. Update to v0.2.0: `pip install --upgrade arrowport`
2. Set `storage_backend: delta` in your configuration
3. Or use `--backend delta` with CLI commands

## 🏗️ Technical Details

- Built on the high-performance Rust Delta Lake engine
- Zero-copy Arrow integration maintained
- Consistent API across storage backends
- Full test coverage for Delta operations

## 🙏 Thank You

Thanks to all our users and contributors! Special thanks to the Delta Lake and Arrow communities for making this integration possible.

## 📖 Documentation

Full documentation available at:

- Design document: `art/design.md`
- README: Updated with Delta Lake examples
- Example scripts: `examples/delta_demo.py`

---

**Happy data landing with Arrowport! 🛬**
