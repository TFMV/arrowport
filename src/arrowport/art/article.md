# Arrowport: A High-Performance Bridge Between Arrow IPC Streams and DuckDB

## Introduction

The ability to efficiently move and process data between different systems is crucial. Apache Arrow has emerged as a standard for in-memory columnar data representation, while DuckDB has established itself as a powerful analytical database engine. Arrowport bridges these two technologies, providing a high-performance solution for landing Arrow IPC streams directly into DuckDB's analytical engine.

## What is Arrowport?

Arrowport is an open-source project that acts as a specialized air traffic controller for your data, ensuring Arrow streams land safely and efficiently in DuckDB's analytical engine. It provides both a REST API and an Arrow Flight interface for high-throughput data ingestion, with built-in support for compression, transaction management, and monitoring.

### Key Features

- **Native Arrow IPC Support**: Direct ingestion of Arrow IPC streams with zero-copy optimizations
- **ZSTD Compression**: Built-in support for ZSTD compression to optimize network transfer
- **Transaction Safety**: Atomic operations ensure data consistency
- **REST and Flight Interfaces**: Multiple protocols for different use cases
- **Prometheus Metrics**: Built-in monitoring capabilities
- **Hot-Reload Configuration**: Dynamic stream configuration management
- **Modern Python Implementation**: Built with FastAPI, Pydantic, and modern Python practices

## Technical Architecture

Arrowport is built on modern Python technologies and follows a modular architecture:

```
arrowport/
├── api/          # FastAPI application and endpoints
├── core/         # Core functionality (Arrow, DuckDB)
├── config/       # Configuration management
├── models/       # Pydantic models
└── utils/        # Utility functions
```

### Data Flow

1. **Client Sends Data**: Clients can send data through either:
   - REST API with base64-encoded Arrow IPC streams
   - Arrow Flight protocol for high-performance streaming

2. **Stream Processing**:

Arrowport provides two methods for processing Arrow streams, both optimized for zero-copy operations:

a) **REST API Implementation**:

```python
@app.post("/stream/{stream_name}")
async def process_stream(stream_name: str, config: ArrowStreamConfig, batch: ArrowBatch):
    # Convert batch to Arrow Table
    table = batch.to_arrow_table()
    
    # Process in transaction with zero-copy
    with db_manager.transaction() as conn:
        # Create table if needed using schema
        conn.register("arrow_schema_table", table.slice(0, 0))
        conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {config.target_table} AS 
        SELECT * FROM arrow_schema_table LIMIT 0
        """)
        
        # Register and insert data directly
        conn.register("arrow_table", table)
        conn.execute(f"""
        INSERT INTO {config.target_table} 
        SELECT * FROM arrow_table
        """)
```

b) **Arrow Flight Implementation**:

```python
def do_put(self, descriptor: flight.FlightDescriptor, reader: flight.FlightStreamReader):
    with db_manager.transaction() as conn:
        # Process batches directly from stream
        while True:
            batch = reader.read_chunk()
            if batch is None:
                break
                
            # Register batch directly with DuckDB
            conn.register("arrow_table", batch.data)
            conn.execute(f"""
            INSERT INTO {config.target_table} 
            SELECT * FROM arrow_table
            """)
```

Both implementations provide excellent performance through:

- Zero-copy data transfer using DuckDB's native Arrow registration
- Direct streaming without temporary files
- Efficient batch processing
- Transaction safety

3. **DuckDB Integration**: Arrowport leverages DuckDB's native Arrow support through direct Arrow table registration, enabling efficient data transfer without unnecessary conversions or temporary storage.

## Arrow IPC and DuckDB: A Perfect Match

The Apache Arrow project has revolutionized data interchange with its columnar format. The Arrow IPC (Inter-Process Communication) format extends this by providing an efficient serialization mechanism for Arrow data. When combined with DuckDB's native Arrow support, this creates a powerful pipeline for analytical workloads.

### Why Arrow IPC?

Compared to other formats like Parquet, Arrow IPC offers:

1. **Simpler Implementation**: The Arrow IPC format is less complex than Parquet, making it easier to implement and maintain.
2. **Faster Processing**: Minimal encoding/decoding overhead means faster data processing.
3. **Zero-Copy Optimizations**: When possible, data can be read without copying memory.

### DuckDB's Arrow Integration

DuckDB's Arrow integration, available through the arrow community extension, provides native support for consuming and producing Arrow data. This integration is particularly powerful because:

1. **No Conversion Overhead**: Data stays in columnar format throughout the pipeline
2. **Memory Efficiency**: Zero-copy optimizations reduce memory usage
3. **Type Preservation**: Arrow's rich type system maps cleanly to DuckDB's types

## Implementation Details

### Configuration Management

Arrowport uses Pydantic for configuration management, with support for hot-reloading:

```python
class ArrowStreamConfig(BaseModel):
    """Configuration for an Arrow stream."""
    target_table: str = Field(..., description="Target table in DuckDB")
    chunk_size: int = Field(default=10000, description="Chunk size for processing")
    compression: Optional[dict[str, Any]] = Field(
        default=None, description="Compression settings"
    )
```

### Arrow Flight Server

For high-performance scenarios, Arrowport provides an Arrow Flight server:

```python
class FlightServer(flight.FlightServerBase):
    def do_put(self, descriptor: flight.FlightDescriptor, 
               reader: flight.FlightStreamReader) -> None:
        """Process an incoming Flight stream."""
        with db_manager.transaction() as conn:
            while True:
                batch = reader.read_chunk()
                if batch is None:
                    break
                    
                conn.register("arrow_table", batch.data)
                conn.execute(
                    f"INSERT INTO {config.target_table} "
                    "SELECT * FROM arrow_table"
                )
```

### Transaction Management

All operations in Arrowport are transactional, ensuring data consistency:

```python
@contextmanager
def transaction(self):
    """Execute operations in a transaction."""
    conn = self.get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

## Performance Considerations

Arrowport is designed for high performance:

1. **Batch Processing**: Data is processed in configurable batch sizes
2. **Native Compression**: ZSTD compression reduces network transfer
3. **Zero-Copy Operations**: Minimizes memory copies when possible
4. **Transaction Optimization**: Batches are processed in single transactions

## Future Developments

The Arrowport project has several planned enhancements:

1. **LZ4 Compression Support**: Adding LZ4 as an alternative compression option
2. **Arrow Flight SQL**: Implementation of the Arrow Flight SQL protocol
3. **Enhanced Monitoring**: More detailed metrics and monitoring capabilities
4. **Schema Evolution**: Automatic handling of schema changes
5. **Parallel Processing**: Multi-threaded batch processing
