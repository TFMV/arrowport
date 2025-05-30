# Arrowport (Python) — Design v1.0

*A high-performance bridge from Arrow IPC streams to DuckDB, leveraging the new Arrow community extension.*

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
                           DuckDB SQL     ▼
                                   ┌────────────┐
                                   │  DuckDB    │
                                   │ .duckdb or │
                                   │ DuckLake   │
                                   └────────────┘
```

Key Enhancements:

- Zero-copy data transfer using Arrow IPC format
- Support for both ZSTD and LZ4 compression
- DuckDB Arrow community extension integration
- Memory-mapped file support for large datasets

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
compression:
  algorithm: zstd  # or lz4
  level: 3
streams:
  lineitem:
    target_table: lineitem
    chunk_size: 122880  # Aligned with DuckDB row group size
  sensors:
    target_table: sensor_readings
    compression:
      algorithm: lz4  # Override per stream
duckdb_extensions: [httpfs, parquet, arrow]
```

Environment overrides:
`ARROWPORT_DB`, `ARROWPORT_PORT`, `ARROWPORT_STREAMS_PATH`, `ARROWPORT_COMPRESSION`

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
| CLI | **Typer** + **rich** | Modern CLI UX |
| Tests | **pytest**, **pytest-asyncio** | Async testing |
| Packaging | **pyoxidizer** | Single binary |
| Storage | Local FS, S3 via DuckDB | Native integration |

---

## 8. Operational Considerations

- **Schema evolution**: Log warning & skip if incoming batch schema ⊄ table schema
- **Metrics**: Prometheus format exposing:
  - Rows/second throughput
  - Compression ratios
  - Memory usage
  - Schema mismatches
- **Concurrency**: Single process, async I/O
- **Durability**: DuckDB WAL + configurable checkpointing

---

## 9. Future Enhancements

1. **Streaming aggregations** using DuckDB's window functions
2. **Arrow Flight SQL** endpoint for downstream consumers
3. **Schema registry** integration
4. **Multi-node** support via DuckDB remote
5. **Cloud-native** deployment patterns

---

### Summary

Arrowport leverages DuckDB's new Arrow community extension to provide:

- **Zero-copy data transfer** with compression support
- **Simple deployment** - one process, one config file
- **Production-ready** monitoring and operational features
- **Future-proof** architecture supporting cloud-native patterns

Let us know which section needs more detail - implementation specifics, performance tuning, or deployment patterns.
