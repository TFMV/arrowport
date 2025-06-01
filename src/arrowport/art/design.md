# Arrowport (Python) — Design v1.0

---

## 1. Project Goals & Enhanced Scope

| Goal | Why | Implementation |
|------|-----|----------------|
| **Zero-copy ingest** of Arrow data into DuckDB | Maximize performance for Polars/PyArrow users | Using DuckDB's new Arrow community extension |
| **Compression support** | Optimize network and storage usage | ZSTD and LZ4 compression via Arrow IPC |
| **Single‑binary UX** (`pipx install arrowport`) | Easy local trials & CI pipelines | PyOxidizer packaging |
| **No heavy services** — pure user‑space process | Keeps deployment and security simple | Lightweight FastAPI + Arrow Flight |
| **Config‑driven routing** (YAML or env) | Avoids baking table names in code | Hot-reloadable configuration |

*Non‑Goals (MVP)*: Full schema registry, multi‑node sharding, authN/authZ, UI dashboards.

---

## 2. High‑Level Architecture

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
                                   │ .duckdb or │ OR │  (Parquet +  │
                                   │ DuckLake   │    │   _delta_log)│
                                   └────────────┘    └──────────────┘
```

Key Enhancements:

- Zero-copy data transfer using Arrow IPC format
- Support for both ZSTD and LZ4 compression
- DuckDB Arrow community extension integration
- Memory-mapped file support for large datasets
- **NEW: Delta Lake support as alternative storage backend**

---

## 3. Core Runtime Components

| Component | Key Points | Defaults |
|-----------|------------|----------|
| **Ingest API** | *Dual‑stack*: FastAPI `POST /ingest/{stream}` (body = Arrow stream) **and** `pyarrow.flight` endpoint | Both enabled on `0.0.0.0:8888` |
| **Router** | Stream path → table lookup in YAML with hot reload | If no match, table = stream name |
| **Loader** | Zero-copy Arrow → DuckDB via community extension | Transaction per batch |
| **Storage** | DuckDB file or DuckLake directory | Local file `arrowport.duckdb` |
| **Compression** | ZSTD and LZ4 support via Arrow IPC | ZSTD level 3 |
| **CLI** | `arrowport serve`, `arrowport ingest`, `arrowport streams` | Rich CLI output |

---

## 4. Configuration (YAML or ENV)

```yaml
db_path: ./warehouse.duckdb
storage_backend: duckdb  # NEW: or 'delta'
delta_config:  # NEW: Delta Lake configuration
  table_path: ./delta_tables
  version_retention_hours: 168  # 7 days
  checkpoint_interval: 10
  enable_cdc: false
compression:
  algorithm: zstd  # or lz4
  level: 3
streams:
  lineitem:
    target_table: lineitem
    storage_backend: delta  # NEW: Override per stream
    chunk_size: 122880  # Aligned with DuckDB row group size
  sensors:
    target_table: sensor_readings
    compression:
      algorithm: lz4  # Override per stream
duckdb_extensions: [httpfs, parquet, arrow]
```

Environment overrides:
`ARROWPORT_DB`, `ARROWPORT_PORT`, `ARROWPORT_STREAMS_PATH`, `ARROWPORT_COMPRESSION`, `ARROWPORT_STORAGE_BACKEND`

---

## 5. Performance Optimizations

1. **Zero-copy ingestion**:
   - Direct Arrow IPC → DuckDB using community extension
   - Memory-mapped files for large datasets
   - Aligned chunk sizes with DuckDB row groups (122880 rows)

2. **Compression strategies**:
   - ZSTD: Better compression ratio, slower
   - LZ4: Faster compression/decompression
   - Per-stream configuration

3. **Memory management**:
   - Streaming ingestion to avoid OOM
   - Buffer pool management
   - Automatic cleanup of temporary buffers

4. **Monitoring**:
   - Prometheus metrics for throughput
   - Memory usage tracking
   - Compression ratio monitoring

---

## 6. MVP Roadmap

| Week | Deliverable |
|------|-------------|
| **1** | Project scaffold, Arrow community extension integration |
| **2** | Zero-copy loader implementation, compression support |
| **3** | Flight server + HTTP endpoints, E2E tests |
| **4** | CLI implementation, monitoring setup |
| **5** | Performance tuning, documentation |
| **6** | Binary packaging, example notebooks |

---

## 7. Tech Stack

| Concern | Library | Notes |
|---------|----------|--------|
| IPC/Flight | **pyarrow** ≥ 16.0 | Zero-copy support |
| Web API | **FastAPI** + **uvicorn** | Async support |
| DB Layer | **duckdb** + arrow extension | Community extension |
| **Delta Lake** | **deltalake** ≥ 0.15.0 | **NEW: Alternative storage** |
| CLI | **Typer** + **rich** | Modern CLI UX |
| Tests | **pytest**, **pytest-asyncio** | Async testing |
| Packaging | **pyoxidizer** | Single binary |
| Storage | Local FS, S3 via DuckDB | Native integration |

---

## 8. Operational Considerations

- **Schema evolution**: Log warning & skip if incoming batch schema ⊄ table schema
  - **NEW: Delta Lake** - Supports schema evolution with merge schema option
- **Metrics**: Prometheus format exposing:
  - Rows/second throughput
  - Compression ratios
  - Memory usage
  - Schema mismatches
  - **NEW: Delta Lake metrics** - Version count, file count, table size
- **Concurrency**: Single process, async I/O
  - **NEW: Delta Lake** - Multi-writer support with optimistic concurrency
- **Durability**: DuckDB WAL + configurable checkpointing
  - **NEW: Delta Lake** - ACID transactions with time travel

---

## 9. Future Enhancements

1. **Streaming aggregations** using DuckDB's window functions
2. **Arrow Flight SQL** endpoint for downstream consumers
3. **Schema registry** integration
4. **Multi-node** support via DuckDB remote
5. **Cloud-native** deployment patterns

---

## 10. Delta Lake Integration (NEW)

### Overview

Delta Lake support provides an alternative storage backend to DuckDB, enabling:

- ACID transactions with optimistic concurrency control
- Time travel queries (query data as of a specific version)
- Schema evolution and enforcement
- Unified batch and streaming data processing
- Better integration with Spark, Databricks, and other big data tools

### Implementation Details

1. **Storage Backend Selection**:
   - Global default via `storage_backend` config
   - Per-stream override in stream configuration
   - Runtime selection based on API endpoint

2. **Zero-copy Ingestion**:

   ```python
   # Direct Arrow Table to Delta Lake write
   from deltalake import write_deltalake
   
   write_deltalake(
       table_path,
       arrow_table,
       mode="append",
       engine="rust",  # High-performance Rust engine
       schema_mode="merge"  # Allow schema evolution
   )
   ```

3. **API Endpoints**:
   - `/stream/{stream_name}` - Auto-selects backend based on config
   - `/delta/{table_name}` - Explicit Delta Lake ingestion
   - `/delta/{table_name}/history` - Query table history
   - `/delta/{table_name}/version/{version}` - Time travel queries

4. **CLI Commands**:
   - `arrowport delta list` - List Delta tables
   - `arrowport delta vacuum <table>` - Run vacuum operation
   - `arrowport delta history <table>` - Show table history
   - `arrowport delta restore <table> <version>` - Restore to version

5. **Performance Optimizations**:
   - Batch writes aligned with file size targets
   - Automatic file compaction
   - Z-order optimization for common query patterns
   - Partition pruning support

6. **Monitoring**:
   - Delta Lake specific metrics
   - Version growth rate
   - File count and sizes
   - Transaction success/failure rates

### Configuration Example

```yaml
streams:
  events:
    storage_backend: delta
    target_table: events
    delta_options:
      partition_by: ["date"]
      z_order_by: ["user_id"]
      target_file_size: 134217728  # 128MB
      compression: snappy
```

### Migration Path

- Existing DuckDB tables can be migrated to Delta Lake
- Delta Lake tables can be queried from DuckDB via external tables
- Bi-directional data movement supported
