"""Storage backend abstraction for Arrowport."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyarrow as pa
import structlog
from deltalake import DeltaTable, write_deltalake

from ..config.settings import settings
from ..core.db import db_manager

logger = structlog.get_logger()


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def write(
        self,
        table: pa.Table,
        target_table: str,
        mode: str = "append",
        **kwargs,
    ) -> int:
        """Write Arrow Table to storage backend."""
        pass

    @abstractmethod
    def read(
        self, target_table: str, columns: Optional[List[str]] = None, **kwargs
    ) -> pa.Table:
        """Read data from storage backend."""
        pass

    @abstractmethod
    def table_exists(self, target_table: str) -> bool:
        """Check if table exists."""
        pass

    @abstractmethod
    def get_table_info(self, target_table: str) -> Dict[str, Any]:
        """Get table metadata."""
        pass


class DuckDBBackend(StorageBackend):
    """DuckDB storage backend implementation."""

    def write(
        self,
        table: pa.Table,
        target_table: str,
        mode: str = "append",
        **kwargs,
    ) -> int:
        """Write Arrow Table to DuckDB."""
        rows_count = len(table)

        with db_manager.transaction() as conn:
            # Create table if it doesn't exist
            if not self.table_exists(target_table):
                # Register empty table for schema
                conn.register("arrow_schema_table", table.slice(0, 0))
                create_sql = f"""
                CREATE TABLE {target_table} AS 
                SELECT * FROM arrow_schema_table LIMIT 0
                """
                conn.execute(create_sql)
                conn.unregister("arrow_schema_table")

            # Register full table and insert data
            conn.register("arrow_table", table)

            if mode == "overwrite":
                conn.execute(f"DELETE FROM {target_table}")

            insert_sql = f"INSERT INTO {target_table} SELECT * FROM arrow_table"
            conn.execute(insert_sql)
            conn.unregister("arrow_table")

        logger.info(
            "Wrote data to DuckDB",
            table=target_table,
            rows=rows_count,
            mode=mode,
        )
        return rows_count

    def read(
        self, target_table: str, columns: Optional[List[str]] = None, **kwargs
    ) -> pa.Table:
        """Read data from DuckDB."""
        with db_manager.connection() as conn:
            if columns:
                cols = ", ".join(columns)
                query = f"SELECT {cols} FROM {target_table}"
            else:
                query = f"SELECT * FROM {target_table}"

            return conn.execute(query).arrow()

    def table_exists(self, target_table: str) -> bool:
        """Check if table exists in DuckDB."""
        with db_manager.connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                [target_table],
            ).fetchone()
            return result[0] > 0

    def get_table_info(self, target_table: str) -> Dict[str, Any]:
        """Get DuckDB table metadata."""
        with db_manager.connection() as conn:
            # Get row count
            row_count = conn.execute(f"SELECT COUNT(*) FROM {target_table}").fetchone()[
                0
            ]

            # Get schema
            schema_info = conn.execute(f"DESCRIBE {target_table}").arrow().to_pydict()

            return {
                "backend": "duckdb",
                "table": target_table,
                "row_count": row_count,
                "schema": schema_info,
            }


class DeltaLakeBackend(StorageBackend):
    """Delta Lake storage backend implementation."""

    def __init__(self, base_path: str = "./delta_tables"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def _get_table_path(self, target_table: str) -> str:
        """Get the path for a Delta table."""
        return str(self.base_path / target_table)

    def write(
        self,
        table: pa.Table,
        target_table: str,
        mode: str = "append",
        **kwargs,
    ) -> int:
        """Write Arrow Table to Delta Lake."""
        rows_count = len(table)
        table_path = self._get_table_path(target_table)

        # Extract Delta-specific options
        partition_by = kwargs.get("partition_by", [])
        schema_mode = kwargs.get("schema_mode", "merge")

        write_deltalake(
            table_path,
            table,
            mode=mode,
            partition_by=partition_by,
            schema_mode=schema_mode,
        )

        logger.info(
            "Wrote data to Delta Lake",
            table=target_table,
            rows=rows_count,
            mode=mode,
            path=table_path,
        )
        return rows_count

    def read(
        self, target_table: str, columns: Optional[List[str]] = None, **kwargs
    ) -> pa.Table:
        """Read data from Delta Lake."""
        table_path = self._get_table_path(target_table)
        dt = DeltaTable(table_path)

        # Support time travel queries
        version = kwargs.get("version")
        if version is not None:
            dt.load_as_version(version)

        # Read with optional column selection
        return dt.to_pyarrow_table(columns=columns)

    def table_exists(self, target_table: str) -> bool:
        """Check if Delta table exists."""
        table_path = self._get_table_path(target_table)
        try:
            DeltaTable(table_path)
            return True
        except Exception:
            return False

    def get_table_info(self, target_table: str) -> Dict[str, Any]:
        """Get Delta Lake table metadata."""
        table_path = self._get_table_path(target_table)
        dt = DeltaTable(table_path)

        # Get table history
        history = dt.history()

        # Get file statistics
        files = dt.files()
        total_size_bytes = sum(
            Path(f).stat().st_size for f in files if Path(f).exists()
        )
        return {
            "backend": "delta",
            "table": target_table,
            "path": table_path,
            "version": dt.version(),
            "row_count": len(dt.to_pyarrow_table()),
            "history_count": len(history),
            "file_count": len(files),
            "total_size_bytes": total_size_bytes,
            "partitions": dt.metadata().partition_columns,
        }

    def vacuum(self, target_table: str, retention_hours: int = 168) -> Dict[str, Any]:
        """Run vacuum operation on Delta table."""
        table_path = self._get_table_path(target_table)
        dt = DeltaTable(table_path)

        # Get initial file count
        initial_files = len(dt.files())

        # Run vacuum
        dt.vacuum(
            retention_hours=retention_hours,
            dry_run=False,
            enforce_retention_duration=False,
        )

        # Get final file count
        dt = DeltaTable(table_path)  # Reload
        final_files = len(dt.files())

        return {
            "table": target_table,
            "files_removed": initial_files - final_files,
            "files_remaining": final_files,
        }

    def restore(self, target_table: str, version: int) -> Dict[str, Any]:
        """Restore Delta table to a specific version."""
        table_path = self._get_table_path(target_table)
        dt = DeltaTable(table_path)

        current_version = dt.version()
        dt.restore(version)

        return {
            "table": target_table,
            "restored_from": current_version,
            "restored_to": version,
        }


# Storage backend factory
def get_storage_backend(backend_type: str = "duckdb", **kwargs) -> StorageBackend:
    """Factory function to get storage backend instance."""
    if backend_type == "duckdb":
        return DuckDBBackend()
    elif backend_type == "delta":
        base_path = kwargs.get("base_path", settings.delta_config.table_path)
        return DeltaLakeBackend(base_path=base_path)
    else:
        raise ValueError(f"Unknown storage backend: {backend_type}")
