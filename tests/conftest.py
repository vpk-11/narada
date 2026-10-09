import pytest

from api.limiter import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
