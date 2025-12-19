import time
from collections import deque
import requests
from threading import Lock

import logging
log = logging.getLogger(__name__)

class LimitSession(requests.Session):
    def __init__(self, calls: int = 120, period: float = 60.0):
        """
        :param calls: Maximum number of requests allowed in the period.
        :param period: Time window in seconds.
        """
        if calls <= 0:
            raise ValueError("calls must be positive")
        if period <= 0:
            raise ValueError("period must be positive")

        super().__init__()
        self.calls = calls
        self.period = period
        self._timestamps = deque(maxlen=calls)
        self._lock = Lock()  # Protects the deque in multithreaded use

    def _enforce_rate_limit(self) -> None:
        with self._lock:
            now = time.time()

            # Expire old timestamps
            while self._timestamps and self._timestamps[0] <= now - self.period:
                self._timestamps.popleft()

            # If at limit, sleep until the next slot opens
            if len(self._timestamps) >= self.calls:
                sleep_time = self._timestamps[0] + self.period - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self._timestamps.popleft()

            # Record this request
            self._timestamps.append(now)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Override the core request method to enforce rate limiting before every request.
        """
        self._enforce_rate_limit()

        try:
            response = super().request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            log.warning(f"Request failed ({method} {url}): {e}")
            raise
session = LimitSession()
