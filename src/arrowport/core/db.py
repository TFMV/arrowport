"""DuckDB connection management."""

import contextlib
from typing import Iterator

import duckdb
import pyarrow as pa
import structlog

logger = structlog.get_logger()


class DuckDBManager:
    """DuckDB connection manager."""

    def __init__(self, database: str = ":memory:") -> None:
        """Initialize the DuckDB manager."""
        self._database = database
        self._conn = None

    @contextlib.contextmanager
    def get_connection(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """Get a DuckDB connection."""
        if self._conn is None:
            self._conn = duckdb.connect(self._database)
            self._conn.install_extension("arrow")
            self._conn.load_extension("arrow")
        try:
            yield self._conn
        except Exception as e:
            logger.error("DuckDB operation failed", error=str(e))
            raise

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @contextlib.contextmanager
    def transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """Context manager for DuckDB transactions."""
        with self.get_connection() as conn:
            try:
                conn.begin()
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

    def register_arrow(self, table_name: str, table: pa.Table) -> None:
        """Register an Arrow table with DuckDB."""
        with self.transaction() as conn:
            # Create table from Arrow schema
            schema_sql = []
            for field in table.schema:
                sql_type = {
                    pa.int8(): "TINYINT",
                    pa.int16(): "SMALLINT",
                    pa.int32(): "INTEGER",
                    pa.int64(): "BIGINT",
                    pa.float32(): "REAL",
                    pa.float64(): "DOUBLE",
                    pa.string(): "VARCHAR",
                    pa.bool_(): "BOOLEAN",
                    pa.timestamp("ns"): "TIMESTAMP",
                }.get(field.type, "VARCHAR")
                schema_sql.append(f"{field.name} {sql_type}")

            create_sql = (
                f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(schema_sql)})"
            )
            conn.execute(create_sql)

            # Register Arrow table and insert data
            conn.register("_temp_arrow", table)
            conn.execute(f"INSERT INTO {table_name} SELECT * FROM _temp_arrow")
            conn.unregister("_temp_arrow")


# Create global DuckDB manager instance
db_manager = DuckDBManager()
