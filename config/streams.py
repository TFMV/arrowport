from pathlib import Path
from typing import Optional

import structlog
import yaml
from pydantic import BaseModel, Field
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..models.arrow import ArrowStreamConfig

logger = structlog.get_logger()


class StreamConfig(BaseModel):
    """Root configuration for all streams."""

    streams: dict[str, ArrowStreamConfig] = Field(
        default_factory=dict, description="Stream configurations keyed by stream name"
    )


class StreamConfigManager:
    """Manager for stream configurations."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize the stream configuration manager."""
        self._config = StreamConfig()
        self._config_path = config_path
        self._observer: Optional[Observer] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load stream configurations from YAML file."""
        try:
            if self._config_path and self._config_path.exists():
                with open(self._config_path) as f:
                    config_dict = yaml.safe_load(f)
                self._config = StreamConfig.model_validate(config_dict)
                logger.info("Loaded stream configurations", path=str(self._config_path))
            else:
                logger.warning(
                    "Stream config file not found", path=str(self._config_path)
                )
        except Exception as e:
            logger.error("Failed to load stream configurations", error=str(e))
            # Keep existing config if loading fails

    def get_stream_config(self, stream_name: str) -> Optional[ArrowStreamConfig]:
        """Get configuration for a stream."""
        return self._config.streams.get(stream_name)

    def start_watching(self) -> None:
        """Start watching config file for changes."""
        if self._observer is not None:
            return

        class ConfigHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path == str(self._config_path.absolute()):
                    logger.info("Stream config file modified, reloading")
                    self._load_config()

        self._observer = Observer()
        self._observer.schedule(
            ConfigHandler(), str(self._config_path.parent.absolute()), recursive=False
        )
        self._observer.start()
        logger.info("Started watching stream config file", path=str(self._config_path))

    def stop_watching(self) -> None:
        """Stop watching config file."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Stopped watching stream config file")


# Create global stream config manager instance
stream_config_manager = StreamConfigManager()
