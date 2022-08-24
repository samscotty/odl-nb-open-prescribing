import threading
from functools import wraps
from time import time
from typing import Union


class RateLimiter:

    """Ensure an operation is not executed more than a given number of times over a given period.

    Args:
        calls: Maximum number of requests to make per `period`.
        period: Maximum number of `calls` per second.

    """

    def __init__(self, calls: int = 1, period: Union[int, float] = 1):
        self.calls = max(1, int(calls))
        self.period = float(period)

        self.number_of_calls = 0
        self.last_reset = time()

        self._lock = threading.RLock()

    def __call__(self, func):
        """Enables usage as a decorator.

        Args:
            func: Function to wrap with rate-limiting.

        """

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
