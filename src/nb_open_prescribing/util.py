import threading
from functools import wraps
from time import time
from typing import Union


class RateLimiter:

    """ """

    def __init__(self, calls: int = 1, period: Union[int, float] = 1):
        self.calls = max(1, int(calls))
        self.period = float(period)

        self.number_of_calls = 0
        self.last_reset = time()

        self._lock = threading.RLock()

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self._lock:

                elapsed = time() - self.last_reset
                if self.period - elapsed <= 0:
                    self.number_of_calls = 0
                    self.last_reset = time()

                self.number_of_calls += 1

                if self.number_of_calls > self.calls:
                    return None

            return func(*args, **kwargs)

        return wrapper
