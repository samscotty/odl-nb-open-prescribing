from nb_open_prescribing.util import RateLimiter


def test_calls_is_always_one_or_more():
    rate_limiter = RateLimiter(calls=-5)
    assert rate_limiter.calls == 1
    rate_limiter = RateLimiter(calls=10)
    assert rate_limiter.calls == 10


def test_rate_limiter_decoration_prevents_calls():
    class Counter:
        def __init__(self):
            self.count = 0

        @RateLimiter(calls=1, period=10)
        def increment(self):
            self.count += 1

    counter = Counter()

    for _ in range(10):
        counter.increment()
    assert counter.count == 1
