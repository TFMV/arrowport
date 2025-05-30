"""Arrow Flight server implementation for Arrowport."""

import json
from collections.abc import Iterator

import structlog
from pyarrow import flight

from ..config.streams import stream_config_manager
from ..core.db import db_manager

logger = structlog.get_logger()


class FlightServer(flight.FlightServerBase):
    """Arrow Flight server for Arrowport."""

    def __init__(self, location: str = "grpc://0.0.0.0:8815") -> None:
        """Initialize the Flight server."""
        super().__init__(location)
        self._location = location

    def do_put(
        self, descriptor: flight.FlightDescriptor, reader: flight.FlightStreamReader
    ) -> None:
        """Process an incoming Flight stream."""
        try:
            # Parse stream name from descriptor
            command = json.loads(descriptor.command.decode())
            stream_name = command.get("stream_name")
            if not stream_name:
                raise flight.FlightError("Stream name not provided")

            # Get stream configuration
            config = stream_config_manager.get_stream_config(stream_name)
            if not config:
                raise flight.FlightError(f"Stream {stream_name} not found")

            total_rows = 0
            with db_manager.transaction() as conn:
                # Create table if it doesn't exist
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {config.target_table} AS 
                SELECT * FROM arrow_table LIMIT 0
                """
                conn.execute(create_table_sql)

                # Process batches
                while True:
                    try:
                        batch = reader.read_chunk()
                        if batch is None:
                            break

                        # Register batch as arrow table
                        conn.register("arrow_table", batch.data)
                        rows = len(batch.data)
                        total_rows += rows

                        # Insert data
                        conn.execute(
                            f"INSERT INTO {config.target_table} "
                            "SELECT * FROM arrow_table"
                        )

                    except StopIteration:
                        break

            logger.info(
                "Flight stream processed",
                stream=stream_name,
                rows=total_rows,
            )

        except Exception as e:
            logger.error("Failed to process Flight stream", error=str(e))
            raise flight.FlightError(f"Failed to process stream: {e!s}") from e

    def list_flights(
        self, context: flight.ServerCallContext, criteria: bytes
    ) -> Iterator[flight.FlightInfo]:
        """List available streams."""
        for name, _ in stream_config_manager._config.streams.items():
            descriptor = flight.FlightDescriptor.for_command(
                json.dumps({"stream_name": name}).encode()
            )
            yield flight.FlightInfo(
                descriptor,
                None,
                [],
                -1,
                -1,
            )

    def get_flight_info(
        self, context: flight.ServerCallContext, descriptor: flight.FlightDescriptor
    ) -> flight.FlightInfo:
        """Get information about a stream."""
        try:
            command = json.loads(descriptor.command.decode())
            stream_name = command.get("stream_name")
            if not stream_name:
                raise flight.FlightError("Stream name not provided")

            config = stream_config_manager.get_stream_config(stream_name)
            if not config:
                raise flight.FlightError(f"Stream {stream_name} not found")

            return flight.FlightInfo(
                descriptor,
                None,
                [],
                -1,
                -1,
            )

        except Exception as e:
            logger.error("Failed to get Flight info", error=str(e))
            raise flight.FlightError(f"Failed to get stream info: {e!s}") from e


def start_flight_server() -> None:
    """Start the Arrow Flight server."""
    try:
        server = FlightServer()
        server.serve()
        logger.info("Started Arrow Flight server", location=server._location)
    except Exception as e:
        logger.error("Failed to start Arrow Flight server", error=str(e))
        raise
