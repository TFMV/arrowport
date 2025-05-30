from typing import Dict, Optional
import yaml
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import structlog
from pydantic import BaseModel, Field

from .settings import settings
from ..models.arrow import ArrowStreamConfig

logger = structlog.get_logger()


class StreamsConfig(BaseModel):
    """Root configuration for all streams."""

    streams: Dict[str, ArrowStreamConfig] = Field(
        default_factory=dict, description="Stream configurations keyed by stream name"
    )


class StreamConfigManager:
    """Manages stream configurations with hot-reload support."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/streams.yaml")
        self._config: StreamsConfig = StreamsConfig()
        self._observer: Optional[Observer] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load stream configurations from YAML file."""
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    config_dict = yaml.safe_load(f)
                self._config = StreamsConfig.model_validate(config_dict)
                logger.info("Loaded stream configurations", path=str(self.config_path))
            else:
                logger.warning(
                    "Stream config file not found", path=str(self.config_path)
                )
        except Exception as e:
            logger.error("Failed to load stream configurations", error=str(e))
            # Keep existing config if loading fails

    def get_stream_config(self, stream_name: str) -> Optional[ArrowStreamConfig]:
        """Get configuration for a specific stream."""
        return self._config.streams.get(stream_name)

    def start_watching(self) -> None:
        """Start watching config file for changes."""
        if self._observer is not None:
            return

        class ConfigHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path == str(self.config_path.absolute()):
                    logger.info("Stream config file modified, reloading")
                    self._load_config()

        self._observer = Observer()
        self._observer.schedule(
            ConfigHandler(), str(self.config_path.parent.absolute()), recursive=False
        )
        self._observer.start()
        logger.info("Started watching stream config file", path=str(self.config_path))

    def stop_watching(self) -> None:
        """Stop watching config file."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Stopped watching stream config file")


# Create global stream config manager instance
stream_config_manager = StreamConfigManager()
