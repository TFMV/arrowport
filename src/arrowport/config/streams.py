from typing import Dict

import structlog
from pydantic import BaseModel, Field

from ..models.arrow import ArrowStreamConfig

logger = structlog.get_logger()


class StreamConfig(BaseModel):
    """Root configuration for all streams."""

    streams: dict[str, ArrowStreamConfig] = Field(
        default_factory=dict,
        description="Stream configurations keyed by stream name",
    )


class StreamConfigManager:
    """Stream configuration manager."""

    def __init__(self) -> None:
        self._configs: Dict[str, ArrowStreamConfig] = {}

    def get_config(self, stream_name: str) -> ArrowStreamConfig:
        """Get stream configuration for the given stream."""
        if stream_name not in self._configs:
            self._configs[stream_name] = ArrowStreamConfig(target_table=stream_name)
        return self._configs[stream_name]

    # Backwards compatibility
    get_stream_config = get_config

    def set_config(self, stream_name: str, config: ArrowStreamConfig) -> None:
        """Set stream configuration."""
        self._configs[stream_name] = config


# Create global stream config manager instance
stream_config_manager = StreamConfigManager()
