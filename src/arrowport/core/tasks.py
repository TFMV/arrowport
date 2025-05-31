import asyncio
from typing import Any, Callable

import structlog
from prometheus_client import Counter, Histogram

logger = structlog.get_logger()

# Prometheus metrics
TASK_COUNTER = Counter(
    "arrowport_background_tasks_total",
    "Total number of background tasks",
    ["task_type", "status"],
)
TASK_DURATION = Histogram(
    "arrowport_background_task_duration_seconds",
    "Background task duration in seconds",
    ["task_type"],
)


class BackgroundTaskManager:
    """Manages background tasks with retry support."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._tasks = set()

    async def add_task(
        self, func: Callable, *args: Any, task_type: str = "default", **kwargs: Any
    ) -> None:
        """
        Add a task to be executed in the background.

        Args:
            func: The function to execute
            task_type: Type of task for metrics and logging
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        task = asyncio.create_task(
            self._execute_with_retry(func, task_type, *args, **kwargs)
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _execute_with_retry(
        self, func: Callable, task_type: str, *args: Any, **kwargs: Any
    ) -> None:
        """Execute a function with retry logic."""
        retries = 0
        while retries <= self.max_retries:
            try:
                with TASK_DURATION.labels(task_type).time():
                    if asyncio.iscoroutinefunction(func):
                        await func(*args, **kwargs)
                    else:
                        await asyncio.to_thread(func, *args, **kwargs)

                TASK_COUNTER.labels(task_type=task_type, status="success").inc()
                return

            except Exception as e:
                retries += 1
                logger.error(
                    "Background task failed",
                    task_type=task_type,
                    error=str(e),
                    retry=retries,
                )

                if retries <= self.max_retries:
                    await asyncio.sleep(self.retry_delay * retries)
                else:
                    TASK_COUNTER.labels(task_type=task_type, status="failure").inc()
                    raise

    async def wait_all(self) -> None:
        """Wait for all background tasks to complete."""
        if self._tasks:
            await asyncio.gather(*self._tasks)


# Create global task manager instance
task_manager = BackgroundTaskManager()
