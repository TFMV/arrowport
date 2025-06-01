# Changelog

All notable changes to Arrowport will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-01-XX

### Added

- 🎉 **Delta Lake Support** - Alternative storage backend to DuckDB
  - ACID transactions with multi-writer support
  - Time travel queries to access historical data
  - Schema evolution with merge mode
  - Partitioned tables for efficient data organization
  - Z-ordering optimization for query patterns
  - Vacuum operation to clean up old files
  - Restore capability to rollback to previous versions

- **New API Endpoints**
  - `POST /delta/{table_name}` - Direct Delta Lake ingestion
  - `GET /delta/{table_name}/info` - Get table information
  - `GET /delta/{table_name}/history` - View table history
  - `POST /delta/{table_name}/vacuum` - Clean up old files
  
- **New CLI Commands**
  - `arrowport delta list` - List all Delta tables
  - `arrowport delta history <table>` - Show table history
  - `arrowport delta vacuum <table>` - Clean up old files
  - `arrowport delta restore <table> <version>` - Restore to version
  - `--backend` flag for `arrowport ingest` command

- **Storage Backend Abstraction**
  - Pluggable storage backend architecture
  - Factory pattern for backend selection
  - Consistent API across backends

### Changed

- Updated stream configuration to support storage backend selection
- Enhanced `ArrowStreamConfig` model with Delta Lake options
- Improved CLI with backend-specific options
- Updated documentation with Delta Lake examples

### Technical Details

- Added `deltalake` Python package dependency (>= 0.15.0)
- Implemented `StorageBackend` ABC for extensibility
- Added comprehensive Delta Lake tests
- Created example scripts for Delta Lake usage

## [0.1.0] - 2024-01-XX

### Added

- Initial release with DuckDB support
- Zero-copy Arrow IPC to DuckDB ingestion
- REST API and Arrow Flight endpoints
- ZSTD and LZ4 compression support
- Configuration-driven stream routing
- CLI for server and data ingestion
- Prometheus metrics
- Transaction support for atomic writes
