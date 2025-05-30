import uvicorn
from api.app import app
from config.settings import settings


def main() -> None:
    """Run the FastAPI application using uvicorn."""
    uvicorn.run(
        "api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,  # Enable auto-reload during development
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
