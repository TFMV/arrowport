from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
import duckdb
import structlog

from ..config.settings import settings

logger = structlog.get_logger()


class DuckDBManager:
    """Manages DuckDB connections and transactions."""

    def __init__(self, db_path: str = settings.db_path):
        self.db_path = db_path
        self._connection = None

    @contextmanager
    def get_connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Get a DuckDB connection with proper resource management."""
        if self._connection is None:
            try:
                self._connection = duckdb.connect(self.db_path)
                logger.info("Created new DuckDB connection", db_path=self.db_path)
            except Exception as e:
                logger.error(
                    "Failed to connect to DuckDB", error=str(e), db_path=self.db_path
                )
                raise

        try:
            yield self._connection
        except Exception as e:
            logger.error("Error during DuckDB operation", error=str(e))
            raise

    @contextmanager
    def transaction(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Execute operations within a transaction context."""
        with self.get_connection() as conn:
            try:
                conn.begin()
                yield conn
                conn.commit()
                logger.debug("Transaction committed successfully")
            except Exception as e:
                conn.rollback()
                logger.error("Transaction rolled back due to error", error=str(e))
                raise

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._connection is not None:
            try:
                self._connection.close()
                self._connection = None
                logger.info("Closed DuckDB connection", db_path=self.db_path)
            except Exception as e:
                logger.error("Error closing DuckDB connection", error=str(e))
                raise


# Create global database manager instance
db_manager = DuckDBManager()
