"""Arrow IPC handling functionality."""

from pathlib import Path
from typing import Optional, Union

import pyarrow as pa


class ArrowStream:
    """Handler for Arrow IPC streams."""

    def __init__(self, compression: Optional[str] = None, compression_level: int = 3):
        """Initialize Arrow stream handler.

        Args:
            compression: Compression algorithm ('zstd' or 'lz4')
            compression_level: Compression level (not used in Arrow IPC)
        """
        self.compression = compression

    def write_table(
        self,
        table: pa.Table,
        path: Union[str, Path],
    ) -> None:
        """Write Arrow table to IPC stream format.

        Args:
            table: PyArrow table to write
            path: Path to write to
        """
        path = Path(path)

        # Configure IPC write options with compression
        options = None
        if self.compression:
            options = pa.ipc.IpcWriteOptions(compression=self.compression)

        # Write Arrow IPC stream with optional compression
        with pa.ipc.new_stream(path, table.schema, options=options) as writer:
            writer.write_table(table)

    def read_table(self, path: Union[str, Path]) -> pa.Table:
        """Read Arrow table from IPC stream format.

        Args:
            path: Path to read from

        Returns:
            PyArrow table
        """
        path = Path(path)
        with pa.ipc.open_stream(path) as reader:
            return reader.read_all()
