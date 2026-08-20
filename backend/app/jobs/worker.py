import os
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional


class WorkerPool:
    """
    Worker pool managing background execution with thread limits
    tuned per Section 74: min(max(cpu_count - 1, 1), 4).
    """
    def __init__(self, max_workers: Optional[int] = None):
        if max_workers is None:
            cpu_count = os.cpu_count() or 4
            self.max_workers = min(max(cpu_count - 1, 1), 4)
        else:
            self.max_workers = max_workers

        self._executor: Optional[ThreadPoolExecutor] = None
        self._running_futures: Dict[str, Future] = {}

    def start(self):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

    def stop(self, wait: bool = True):
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
            self._executor = None

    def submit(self, fn: Callable[..., Any], *args, **kwargs) -> Future:
        if self._executor is None:
            self.start()
        return self._executor.submit(fn, *args, **kwargs)


# Global singleton instance
worker_pool = WorkerPool()

