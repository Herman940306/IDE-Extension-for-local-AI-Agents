# Design Document - Foundation Hardening

**Project Creator:** Herman Swanepoel
**Feature:** Foundation Hardening & Code Quality Improvements
**Sprint:** Week 4 - Beta Deployment Phase
**Priority:** HIGH
**Document Version:** 1.0
**Last Updated:** 2025-10-13

---

## Overview

This design document outlines the technical approach for implementing foundation hardening improvements to the AuraIA backend system. The design focuses on creating reusable infrastructure components that improve reliability, performance, and maintainability across all agent adapters and services.

### Design Principles

1. **Fail-Safe Defaults:** All new components gracefully degrade when dependencies are unavailable
2. **Zero Breaking Changes:** Existing functionality remains intact; new features are additive
3. **Observable by Design:** All components emit metrics and structured logs
4. **Configuration Over Code:** Behavior is configurable via environment variables
5. **Test-Driven:** All components have comprehensive unit and integration tests

---

## Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Middleware Layer (NEW)                     │    │
│  │  • Rate Limiter Middleware                         │    │
│  │  • Request Size Validator                          │    │
│  │  • Correlation ID Injector                         │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │         API Routes (Enhanced)                      │    │
│  │  • OpenAPI Documentation                           │    │
│  │  • Standardized Error Responses                    │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Orchestration Layer                        │    │
│  │  • Meta-Orchestrator (Enhanced)                    │    │
│  │  • Circuit Breaker Integration                     │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Adapter Layer (Refactored)                 │    │
│  │  • Shared Utilities (NEW)                          │    │
│  │  • Response Cache Integration (NEW)                │    │
│  │  • Circuit Breaker Wrapper (NEW)                   │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Infrastructure Services                    │    │
│  │  • Response Cache Service (NEW)                    │    │
│  │  • Circuit Breaker Manager (NEW)                   │    │
│  │  • Rate Limiter Service (NEW)                      │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │         External Dependencies                      │    │
│  │  • Redis (Cache + Rate Limiting)                   │    │
│  │  • Ollama (LLM Inference)                          │    │
│  │  • ChromaDB (Vector Store)                         │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Components and Interfaces

### 1. Shared Adapter Utilities

**Location:** `backend/src/adapters/adapter_utils.py`

**Purpose:** Centralized utility functions for common adapter operations

#### Interface Design

```python
from typing import Callable, Any, Optional, Dict
from functools import wraps
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AdapterUtils:
    """Shared utilities for agent adapters"""

    @staticmethod
    async def exponential_backoff(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ) -> Any:
        """
        Execute function with exponential backoff retry logic.

        Args:
            func: Async function to execute
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential calculation
            jitter: Add random jitter to prevent thundering herd

        Returns:
            Result from successful function execution

        Raises:
            Exception: Last exception if all retries exhausted
        """

    @staticmethod
    def validate_response(
        response: Dict[str, Any],
        required_fields: list[str]
    ) -> Dict[str, Any]:
        """
        Validate adapter response structure.

        Args:
            response: Response dictionary from adapter
            required_fields: List of required field names

        Returns:
            Validated response dictionary

        Raises:
            ValidationException: If response is invalid
        """

    @staticmethod
    async def health_check_with_timeout(
        check_func: Callable,
        timeout: float = 5.0,
        service_name: str = "unknown"
    ) -> bool:
        """
        Execute health check with timeout protection.

        Args:
            check_func: Async health check function
            timeout: Timeout in seconds
            service_name: Name of service for logging

        Returns:
            True if healthy, False otherwise
        """

    @staticmethod
    def log_adapter_operation(
        adapter_name: str,
        operation: str,
        duration_ms: float,
        success: bool,
        error: Optional[Exception] = None
    ) -> None:
        """
        Log adapter operation with structured logging.

        Args:
            adapter_name: Name of the adapter
            operation: Operation being performed
            duration_ms: Operation duration in milliseconds
            success: Whether operation succeeded
            error: Exception if operation failed
        """
```

#### Implementation Strategy

1. **Exponential Backoff:**
   - Calculate delay: `min(base_delay * (exponential_base ** attempt), max_delay)`
   - Add jitter: `delay * (0.5 + random.random() * 0.5)` to prevent thundering herd
   - Log each retry attempt with context
   - Raise last exception if all retries exhausted

2. **Response Validation:**
   - Check for required fields in response
   - Validate data types
   - Sanitize error messages
   - Return validated response or raise ValidationException

3. **Health Check:**
   - Wrap health check in asyncio.wait_for with timeout
   - Catch all exceptions and return False
   - Log health check results with service name

---

### 2. Response Cache Service

**Location:** `backend/src/services/response_cache.py`

**Purpose:** Cache LLM responses to reduce duplicate API calls

#### Interface Design

```python
from typing import Optional, Dict, Any
import hashlib
import json
from redis.asyncio import Redis
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class ResponseCache:
    """LLM response caching service using Redis"""

    def __init__(
        self,
        redis_client: Redis,
        default_ttl: int = 3600,
        key_prefix: str = "llm_cache"
    ):
        """
        Initialize response cache.

        Args:
            redis_client: Async Redis client
            default_ttl: Default TTL in seconds (1 hour)
            key_prefix: Prefix for cache keys
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

    async def get(
        self,
        prompt: str,
        model: str,
        context_params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response.

        Args:
            prompt: LLM prompt
            model: Model name
            context_params: Additional context parameters

        Returns:
            Cached response or None if not found
        """

    async def set(
        self,
        prompt: str,
        model: str,
        response: Dict[str, Any],
        context_params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache LLM response.

        Args:
            prompt: LLM prompt
            model: Model name
            response: Response to cache
            context_params: Additional context parameters
            ttl: TTL in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise
        """

    def _generate_cache_key(
        self,
        prompt: str,
        model: str,
        context_params: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate cache key from prompt and parameters.

        Args:
            prompt: LLM prompt
            model: Model name
            context_params: Additional context parameters

        Returns:
            SHA-256 hash as cache key
        """

    async def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""

    async def clear(self) -> bool:
        """Clear all cached responses"""
```

#### Implementation Strategy

1. **Cache Key Generation:**
   - Combine prompt + model + sorted context params
   - Hash with SHA-256 for consistent key length
   - Prefix with namespace: `llm_cache:{hash}`

2. **Cache Operations:**
   - Use Redis GET/SET with TTL
   - Serialize responses as JSON
   - Track hits/misses/errors for monitoring
   - Gracefully handle Redis unavailability (return None, log warning)

3. **TTL Strategy:**
   - Default: 1 hour (3600 seconds)
   - Configurable per request
   - Use Redis EXPIRE for automatic cleanup

---

### 3. Circuit Breaker Manager

**Location:** `backend/src/utils/circuit_breaker.py`

**Purpose:** Prevent cascading failures when external services are unhealthy

#### Interface Design

```python
from typing import Callable, Any, Optional
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for external service calls"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: float = 60.0,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Failures before opening circuit
            timeout_seconds: Time to wait before half-open
            success_threshold: Successes needed to close from half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout_seconds)
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None

    async def call(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from function execution

        Raises:
            CircuitBreakerOpenException: If circuit is open
            Exception: Original exception from func
        """

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should transition to half-open"""

    def _on_success(self) -> None:
        """Handle successful call"""

    def _on_failure(self) -> None:
        """Handle failed call"""

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
```

#### Implementation Strategy

1. **State Machine:**

   ```
   CLOSED → (failures >= threshold) → OPEN
   OPEN → (timeout elapsed) → HALF_OPEN
   HALF_OPEN → (success) → CLOSED
   HALF_OPEN → (failure) → OPEN
   ```

2. **Failure Tracking:**
   - Increment failure count on exception
   - Reset count on success
   - Track last failure timestamp

3. **Half-Open Logic:**
   - Allow single test request
   - Close on success, reopen on failure
   - Require multiple successes before closing (configurable)

---

### 4. Exception Hierarchy

**Location:** `backend/src/utils/exceptions.py`

**Purpose:** Standardized exception handling across the codebase

#### Interface Design

```python
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class AuraIAException(Exception):
    """Base exception for all AuraIA errors"""

    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp
            }
        }


class AdapterException(AuraIAException):
    """Adapter-specific errors"""

    def __init__(self, message: str, adapter_name: str, **kwargs):
        super().__init__(
            message=message,
            error_code="ADAPTER_ERROR",
            details={"adapter": adapter_name},
            **kwargs
        )


class LLMException(AuraIAException):
    """LLM inference errors"""

    def __init__(self, message: str, model: str, **kwargs):
        super().__init__(
            message=message,
            error_code="LLM_ERROR",
            details={"model": model},
            **kwargs
        )


class ValidationException(AuraIAException):
    """Input validation errors"""

    def __init__(self, message: str, field: str, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field},
            **kwargs
        )


class CircuitBreakerOpenException(AuraIAException):
    """Circuit breaker is open"""

    def __init__(self, service_name: str, **kwargs):
        super().__init__(
            message=f"Circuit breaker open for {service_name}",
            error_code="CIRCUIT_BREAKER_OPEN",
            details={"service": service_name},
            **kwargs
        )


class RateLimitExceededException(AuraIAException):
    """Rate limit exceeded"""

    def __init__(self, limit: int, window: int, **kwargs):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window} seconds",
            error_code="RATE_LIMIT_EXCEEDED",
            details={"limit": limit, "window": window},
            **kwargs
        )
```

---

### 5. Rate Limiter Service

**Location:** `backend/src/services/rate_limiter.py`

**Purpose:** Protect API endpoints from abuse

#### Interface Design

```python
from typing import Optional
from redis.asyncio import Redis
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter using sliding window"""

    def __init__(
        self,
        redis_client: Redis,
        default_limit: int = 100,
        default_window: int = 60
    ):
        """
        Initialize rate limiter.

        Args:
            redis_client: Async Redis client
            default_limit: Default requests per window
            default_window: Default window in seconds
        """
        self.redis = redis_client
        self.default_limit = default_limit
        self.default_window = default_window

    async def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key (e.g., client_id, ip_address)
            limit: Request limit (uses default if None)
            window: Time window in seconds (uses default if None)

        Returns:
            Tuple of (allowed: bool, remaining: int)
        """

    async def reset(self, key: str) -> bool:
        """Reset rate limit for key"""
```

#### Implementation Strategy

1. **Sliding Window Algorithm:**
   - Use Redis sorted set with timestamps as scores
   - Remove expired entries: `ZREMRANGEBYSCORE key 0 (now - window)`
   - Count current entries: `ZCARD key`
   - Add new entry if under limit: `ZADD key now now`
   - Set expiration: `EXPIRE key window`

2. **Graceful Degradation:**
   - If Redis unavailable, allow request (fail-open)
   - Log warning for monitoring

---

### 6. Middleware Layer

**Location:** `backend/src/api/middleware.py`

**Purpose:** Request/response processing pipeline

#### Components

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import time


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Inject correlation ID into requests"""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce rate limits on requests"""

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        # Extract client identifier (IP or API key)
        client_id = request.client.host

        # Check rate limit
        allowed, remaining = await self.rate_limiter.check_rate_limit(client_id)

        if not allowed:
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": "60"}
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Enforce request size limits"""

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > self.max_size:
            return Response(
                content=f"Request too large. Max size: {self.max_size} bytes",
                status_code=413
            )

        return await call_next(request)
```

---

## Data Models

### Cache Entry Model

```python
from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime


class CacheEntry(BaseModel):
    """Cached LLM response"""
    prompt_hash: str
    model: str
    response: Dict[str, Any]
    cached_at: datetime
    ttl: int
    hit_count: int = 0
```

### Circuit Breaker State Model

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CircuitBreakerState(BaseModel):
    """Circuit breaker state snapshot"""
    name: str
    state: str  # "closed", "open", "half_open"
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime]
    last_state_change: datetime
```

### Rate Limit State Model

```python
from pydantic import BaseModel
from datetime import datetime


class RateLimitState(BaseModel):
    """Rate limit state for a key"""
    key: str
    current_count: int
    limit: int
    window_seconds: int
    window_start: datetime
    reset_at: datetime
```

---

## Error Handling

### Global Exception Handler

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.utils.exceptions import AuraIAException
import logging

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI):
    """Register global exception handlers"""

    @app.exception_handler(AuraIAException)
    async def aura_exception_handler(request: Request, exc: AuraIAException):
        logger.error(
            f"AuraIA exception: {exc.error_code}",
            extra={
                "correlation_id": exc.correlation_id,
                "error_code": exc.error_code,
                "details": exc.details
            }
        )
        return JSONResponse(
            status_code=500,
            content=exc.to_dict()
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.exception(
            "Unhandled exception",
            extra={"correlation_id": correlation_id}
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "correlation_id": correlation_id
                }
            }
        )
```

---

## Testing Strategy

### Unit Tests

```python
# Test adapter utilities
def test_exponential_backoff_success()
def test_exponential_backoff_max_retries()
def test_exponential_backoff_with_jitter()
def test_validate_response_success()
def test_validate_response_missing_fields()
def test_health_check_timeout()

# Test response cache
async def test_cache_hit()
async def test_cache_miss()
async def test_cache_expiration()
async def test_cache_redis_unavailable()

# Test circuit breaker
async def test_circuit_closed_to_open()
async def test_circuit_open_to_half_open()
async def test_circuit_half_open_to_closed()
async def test_circuit_half_open_to_open()

# Test rate limiter
async def test_rate_limit_allowed()
async def test_rate_limit_exceeded()
async def test_rate_limit_sliding_window()
async def test_rate_limit_redis_unavailable()
```

### Integration Tests

```python
# Test end-to-end flows
async def test_adapter_with_cache_and_circuit_breaker()
async def test_rate_limited_endpoint()
async def test_request_size_limit()
async def test_error_handling_pipeline()
```

### Test Coverage Goals

- Adapter utilities: 90%+
- Response cache: 85%+
- Circuit breaker: 90%+
- Rate limiter: 85%+
- Exception handling: 80%+
- Overall: 60%+

---

## Configuration

### Environment Variables

```bash
# Response Cache
REDIS_URL=redis://localhost:6379
CACHE_DEFAULT_TTL=3600
CACHE_KEY_PREFIX=llm_cache

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2

# Rate Limiting
RATE_LIMIT_DEFAULT_LIMIT=100
RATE_LIMIT_DEFAULT_WINDOW=60
RATE_LIMIT_ENABLED=true

# Request Limits
MAX_REQUEST_SIZE=10485760  # 10MB
MAX_FILE_SIZE=1048576      # 1MB
MAX_WEBSOCKET_MESSAGE_SIZE=1048576  # 1MB

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Deployment Considerations

### Redis Setup

```yaml
# docker-compose.yml addition
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis-data:/data
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    return {
        "status": "healthy",
        "components": {
            "redis": await check_redis_health(),
            "ollama": await check_ollama_health(),
            "chromadb": await check_chromadb_health()
        },
        "circuit_breakers": get_all_circuit_states()
    }
```

### Monitoring Metrics

```python
# Prometheus metrics to expose
- llm_cache_hits_total
- llm_cache_misses_total
- circuit_breaker_state{name, state}
- rate_limit_exceeded_total
- request_size_bytes{endpoint}
- adapter_operation_duration_seconds{adapter, operation}
```

---

## Migration Plan

### Phase 1: Infrastructure (Days 1-2)

1. Create shared utilities module
2. Implement response cache service
3. Implement circuit breaker
4. Add exception hierarchy
5. Write unit tests

### Phase 2: Integration (Days 3-4)

1. Refactor adapters to use shared utilities
2. Integrate response cache into LLM manager
3. Wrap adapter calls with circuit breakers
4. Add middleware layer
5. Write integration tests

### Phase 3: Documentation (Day 5)

1. Generate OpenAPI documentation
2. Write deployment runbook
3. Update developer guide
4. Create troubleshooting guide

---

## Success Criteria

1. ✅ All adapters use shared utilities (zero code duplication)
2. ✅ Response cache achieves 30%+ hit rate in testing
3. ✅ Circuit breakers prevent cascading failures in load tests
4. ✅ Rate limiting blocks excessive requests
5. ✅ Test coverage reaches 60%+
6. ✅ OpenAPI docs cover 100% of endpoints
7. ✅ Deployment runbook enables successful deployment

---

**Project Creator:** Herman Swanepoel
**Document Version:** 1.0
**Last Updated:** 2025-10-13
