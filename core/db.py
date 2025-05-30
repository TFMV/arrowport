"""DuckDB connection and transaction management."""

from collections.abc import Generator
from contextlib import contextmanager

import duckdb
import pyarrow as pa

from ..config.settings import settings


class DuckDBManager:
    """Manages DuckDB connections and transactions."""

    def __init__(self, db_path: str):
        """Initialize DuckDB manager.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self._conn = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Get or create DuckDB connection."""
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)
            self._conn.install_extension("arrow")
            self._conn.load_extension("arrow")
        return self._conn

    @contextmanager
    def transaction(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Context manager for DuckDB transactions."""
        try:
            self.conn.begin()
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def import_arrow(
        self,
        table: pa.Table,
        target_table: str,
        mode: str = "create",
    ) -> None:
        """Import Arrow table into DuckDB.

        Args:
            table: PyArrow table to import
            target_table: Name of target table in DuckDB
            mode: Import mode ('create' or 'append')
        """
        with self.transaction() as conn:
            if mode == "create":
                conn.execute(f"DROP TABLE IF EXISTS {target_table}")
                conn.execute(
                    f"CREATE TABLE {target_table} AS SELECT * FROM arrow_table"
                )
            else:
                conn.execute(f"INSERT INTO {target_table} SELECT * FROM arrow_table")

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None


# Create global database manager instance
db_manager = DuckDBManager(settings.db_path)
