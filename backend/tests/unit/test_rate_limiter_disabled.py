import pytest


@pytest.mark.asyncio
async def test_rate_limiter_disabled_paths():
    from src.services.rate_limiter import RateLimiter

    rl = RateLimiter(redis_client=None)

    allowed, remaining = await rl.check_rate_limit("k")
    assert allowed is True and remaining == -1

    assert await rl.reset("k") is False
