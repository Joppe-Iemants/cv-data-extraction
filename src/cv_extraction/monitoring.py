from threading import Event, Thread

import psutil


class MemoryMonitor:
    def __init__(self, enabled: bool, sample_interval_ms: float):
        self.enabled = enabled
        self.sample_interval_ms = sample_interval_ms

        self._process = psutil.Process()
        self._stop_event = Event()
        self._thread = None

        self._start_rss = None
        self._end_rss = None
        self._peak_rss = None
        self._sample_count = 0
        self._error = None

    def _sample(self):
        try:
            rss = self._process.memory_info().rss
        except psutil.Error as error:
            self._error = {
                "type": type(error).__name__,
                "message": str(error)
            }
            return None

        self._sample_count += 1

        if self._peak_rss is None or rss > self._peak_rss:
            self._peak_rss = rss

        return rss

    def _sample_loop(self):
        interval_seconds = self.sample_interval_ms / 1000

        while not self._stop_event.wait(interval_seconds):
            self._sample()

            if self._error is not None:
                break

    def start(self):
        if not self.enabled:
            return

        self._start_rss = self._sample()

        if self._error is not None:
            return

        self._thread = Thread(
            target=self._sample_loop,
            daemon=True
        )
        self._thread.start()

    def stop(self):
        if not self.enabled:
            return

        self._stop_event.set()

        if self._thread is not None:
            self._thread.join()

        if self._error is None:
            self._end_rss = self._sample()

    def report(self) -> dict:
        if not self.enabled:
            return {
                "enabled": False
            }

        return {
            "enabled": True,
            "collection_status": (
                "completed" if self._error is None else "error"
            ),
            "metric": "process_rss",
            "scope": "current_process",
            "sample_interval_ms": self.sample_interval_ms,
            "sample_count": self._sample_count,
            "start_rss_bytes": self._start_rss,
            "end_rss_bytes": self._end_rss,
            "sampled_peak_rss_bytes": (
                self._peak_rss if self._error is None else None
            ),
            "error": self._error
        }