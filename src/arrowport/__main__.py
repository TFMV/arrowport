import threading

import uvicorn

from config.settings import settings
from core.flight import start_flight_server


def run_flight_server():
    """Run the Arrow Flight server in a separate thread."""
    start_flight_server()


def main() -> None:
    """Run the FastAPI and Arrow Flight servers."""
    # Start Flight server in a separate thread if enabled
    if settings.enable_flight:
        flight_thread = threading.Thread(target=run_flight_server, daemon=True)
        flight_thread.start()

    # Start FastAPI server
    uvicorn.run(
        "api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,  # Enable auto-reload during development
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
