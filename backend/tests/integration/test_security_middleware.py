"""
Integration coverage for security middleware
Project Creator: Herman Swanepoel
"""

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.middleware import RateLimitMiddleware
from src.main import app as main_app
from src.main import settings as main_settings


def test_rate_limit_middleware_enforces_limits():
    limiter = AsyncMock()
    limiter.check_rate_limit.side_effect = [(True, 5), (False, 0)]

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, rate_limiter=limiter, enabled=True)

    @app.get("/api/analytics")
    async def analytics_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    first_response = client.get("/api/analytics")
    assert first_response.status_code == 200
    assert first_response.headers["X-RateLimit-Limit"] == "50"
    assert first_response.headers["X-RateLimit-Remaining"] == "5"

    second_response = client.get("/api/analytics")
    assert second_response.status_code == 429
    assert second_response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert second_response.headers["Retry-After"] == "60"
    assert limiter.check_rate_limit.await_count == 2


def test_rate_limit_middleware_disabled_bypasses_checks():
    limiter = AsyncMock()

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, rate_limiter=limiter, enabled=False)

    @app.get("/api/suggestions")
    async def suggestions_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    response = client.get("/api/suggestions")
    assert response.status_code == 200
    assert limiter.check_rate_limit.await_count == 0


def test_main_app_uses_configured_cors_origins():
    cors_middlewares = [m for m in main_app.user_middleware if m.cls.__name__ == "CORSMiddleware"]
    assert cors_middlewares, "CORS middleware missing"

    cors_config = cors_middlewares[0].options
    assert cors_config["allow_origins"] == main_settings.cors_allowed_origins
    assert "*" not in cors_config["allow_origins"]
