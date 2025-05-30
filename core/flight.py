"""Arrow Flight server implementation for Arrowport."""

import argparse
import json
import socket
import threading
import time
from collections.abc import Iterator
from typing import Any, Dict, Optional, Tuple

import pyarrow as pa
import structlog
from pyarrow import flight

from ..config.streams import stream_config_manager
from ..core.db import db_manager

logger = structlog.get_logger()


class FlightServer(flight.FlightServerBase):
    """Arrow Flight server for Arrowport."""

    def __init__(
        self, host: str = "0.0.0.0", port: int = 8889, location: Optional[str] = None
    ) -> None:
        """Initialize the Flight server."""
        if location is None:
            location = f"grpc://{host}:{port}"
        super().__init__(location)
        self._host = host
        self._port = port
        self._location = location
        self._ready = threading.Event()
        logger.info("Flight server initialized", location=location)

    @property
    def host(self) -> str:
        """Get the host."""
        return self._host

    @property
    def port(self) -> int:
        """Get the port."""
        return self._port

    @property
    def location(self) -> str:
        """Get the server location."""
        return self._location

    def wait_for_available(self, timeout: int = 10) -> bool:
        """Wait for the server to be available."""
        return self._ready.wait(timeout)

    def serve(self) -> None:
        """Start serving."""
        try:
            logger.info("Starting Flight server", location=self.location)

            # Start server in a separate thread
            server_thread = threading.Thread(target=super().serve)
            server_thread.daemon = True
            server_thread.start()

            # Wait for server to be available
            start_time = time.time()
            while time.time() - start_time < 10:  # 10 second timeout
                try:
                    with socket.create_connection((self.host, self.port), timeout=1):
                        self._ready.set()
                        logger.info("Flight server is ready", location=self.location)
                        server_thread.join()
                        return
                except (socket.timeout, ConnectionRefusedError):
                    time.sleep(0.1)

            raise RuntimeError("Flight server failed to start within timeout")

        except Exception as e:
            logger.error(
                "Failed to start Flight server", error=str(e), location=self.location
            )
            raise

    def do_put(
        self,
        context: flight.ServerCallContext,
        descriptor: flight.FlightDescriptor,
        reader: flight.FlightStreamReader,
        writer: flight.FlightMetadataWriter,
    ) -> None:
        """Handle incoming data."""
        try:
            # Parse stream configuration from descriptor
            config = json.loads(descriptor.command.decode())
            stream_name = config.get("stream_name", "default")

            # Read the table from the stream
            table = reader.read_all()

            # Get stream configuration
            stream_config = stream_config_manager.get_config(stream_name)

            # Write to DuckDB
            db_manager.register_arrow(stream_config.target_table, table)

            logger.info(
                "Successfully processed Flight data",
                stream=stream_name,
                rows=len(table),
            )
        except Exception as e:
            logger.error("Failed to process Flight data", error=str(e))
            raise

    def list_flights(
        self, context: flight.ServerCallContext, criteria: bytes
    ) -> Iterator[flight.FlightInfo]:
        """List available flights."""
        return []

    def get_flight_info(
        self, context: flight.ServerCallContext, descriptor: flight.FlightDescriptor
    ) -> flight.FlightInfo:
        """Get information about a flight."""
        raise NotImplementedError

    def do_get(
        self, context: flight.ServerCallContext, ticket: flight.Ticket
    ) -> flight.RecordBatchStream:
        """Handle data retrieval requests."""
        raise NotImplementedError

    def list_actions(
        self, context: flight.ServerCallContext
    ) -> Iterator[flight.ActionType]:
        """List available actions."""
        return []

    def do_action(
        self, context: flight.ServerCallContext, action: flight.Action
    ) -> Iterator[flight.Result]:
        """Handle action requests."""
        return []


def main():
    """Run the Flight server."""
    parser = argparse.ArgumentParser(description="Arrowport Flight Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8889, help="Port to bind to")
    args = parser.parse_args()

    try:
        server = FlightServer(host=args.host, port=args.port)
        logger.info(
            "Starting Arrow Flight server",
            host=args.host,
            port=args.port,
        )
        server.serve()
    except Exception as e:
        logger.error("Failed to start Arrow Flight server", error=str(e))
        raise


if __name__ == "__main__":
    main()
