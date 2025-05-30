"""Arrow Flight server implementation for Arrowport."""

import pyarrow as pa
import pyarrow.flight as flight
from typing import Dict, Optional, Iterator
import json
import structlog

from ..config.settings import settings
from ..config.streams import stream_config_manager
from ..core.db import db_manager
from ..core.metrics import STREAM_ROWS_TOTAL, STREAM_BYTES_TOTAL

logger = structlog.get_logger()


class ArrowportFlightServer(flight.FlightServerBase):
    """Arrow Flight server for Arrowport."""

    def __init__(
        self, location: str = f"grpc://{settings.api_host}:{settings.flight_port}"
    ):
        super().__init__(location)
        self._location = location

    def do_put(
        self,
        context: flight.ServerCallContext,
        descriptor: flight.FlightDescriptor,
        reader: flight.FlightMessageReader,
        writer: flight.FlightMetadataWriter,
    ) -> None:
        """Handle PUT requests for streaming data."""
        try:
            # Parse stream name from descriptor
            command = json.loads(descriptor.command.decode())
            stream_name = command.get("stream_name")
            if not stream_name:
                raise ValueError("Stream name not provided")

            # Get stream configuration
            config = stream_config_manager.get_stream_config(stream_name)
            if not config:
                raise ValueError(f"Stream '{stream_name}' not found in configuration")

            # Process the data
            total_rows = 0
            with db_manager.transaction() as conn:
                # Create table if it doesn't exist
                schema = reader.schema
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {config.target_table} AS 
                SELECT * FROM arrow_table LIMIT 0
                """
                conn.execute(create_table_sql)

                # Process chunks
                while True:
                    try:
                        chunk = reader.read_chunk()
                        if chunk is None:
                            break

                        # Insert data
                        table = chunk.data
                        rows = len(table)
                        total_rows += rows

                        insert_sql = f"INSERT INTO {config.target_table} SELECT * FROM arrow_table"
                        conn.execute(insert_sql)

                        # Update metrics
                        STREAM_ROWS_TOTAL.labels(
                            stream_name=stream_name, target_table=config.target_table
                        ).inc(rows)

                        STREAM_BYTES_TOTAL.labels(
                            stream_name=stream_name,
                            compression_algorithm=config.compression.get(
                                "algorithm", "none"
                            ),
                        ).inc(chunk.data_size())

                    except Exception as e:
                        logger.error(
                            "Error processing Flight chunk",
                            stream_name=stream_name,
                            error=str(e),
                        )
                        raise

            logger.info(
                "Successfully processed Flight stream",
                stream_name=stream_name,
                rows_processed=total_rows,
            )

            # Send completion metadata
            writer.write_metadata(
                json.dumps({"status": "success", "rows_processed": total_rows}).encode()
            )

        except Exception as e:
            logger.error("Failed to process Flight stream", error=str(e))
            raise flight.FlightError(f"Failed to process stream: {str(e)}")

    def list_flights(
        self, context: flight.ServerCallContext, criteria: bytes
    ) -> Iterator[flight.FlightInfo]:
        """List available streams."""
        for name, config in stream_config_manager._config.streams.items():
            descriptor = flight.FlightDescriptor.for_command(
                json.dumps({"stream_name": name}).encode()
            )
            yield flight.FlightInfo(
                descriptor,
                None,  # No schema until data is received
                [],  # No endpoints until data is received
                -1,  # Total records unknown
                -1,  # Total bytes unknown
            )

    def get_flight_info(
        self, context: flight.ServerCallContext, descriptor: flight.FlightDescriptor
    ) -> flight.FlightInfo:
        """Get information about a specific stream."""
        try:
            command = json.loads(descriptor.command.decode())
            stream_name = command.get("stream_name")
            if not stream_name:
                raise ValueError("Stream name not provided")

            config = stream_config_manager.get_stream_config(stream_name)
            if not config:
                raise ValueError(f"Stream '{stream_name}' not found")

            return flight.FlightInfo(
                descriptor,
                None,  # No schema until data is received
                [],  # No endpoints until data is received
                -1,  # Total records unknown
                -1,  # Total bytes unknown
            )

        except Exception as e:
            logger.error("Failed to get Flight info", error=str(e))
            raise flight.FlightError(f"Failed to get stream info: {str(e)}")


def start_flight_server() -> None:
    """Start the Arrow Flight server."""
    try:
        server = ArrowportFlightServer()
        server.serve()
        logger.info("Started Arrow Flight server", location=server._location)
    except Exception as e:
        logger.error("Failed to start Arrow Flight server", error=str(e))
        raise
