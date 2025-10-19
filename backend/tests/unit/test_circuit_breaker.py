"""
Unit tests for Circuit Breaker

Project Creator: Herman Swanepoel
Date: 2025-10-13
Target Coverage: 90%
"""

import pytest
import asyncio
from src.utils.circuit_breaker import CircuitBreaker, CircuitState
from src.utils.exceptions import CircuitBreakerOpenException


class TestCircuitBreakerInitialization:
    """Test circuit breaker initialization"""

    def test_initialization_with_defaults(self):
        """Test circuit breaker initialization with default values"""
        cb = CircuitBreaker(name="test_service")

        assert cb.name == "test_service"
        assert cb.failure_threshold == 5
        assert cb.timeout.total_seconds() == 60.0
        assert cb.success_threshold == 2
        assert cb._state == CircuitState.CLOSED
        assert cb._failure_count == 0
        assert cb._success_count == 0

    def test_initialization_with_custom_values(self):
        """Test circuit breaker initialization with custom values"""
        cb = CircuitBreaker(
            name="test_service", failure_threshold=10, timeout_seconds=120.0, success_threshold=3
        )

        assert cb.name == "test_service"
        assert cb.failure_threshold == 10
        assert cb.timeout.total_seconds() == 120.0
        assert cb.success_threshold == 3


@pytest.mark.asyncio
class TestCircuitBreakerClosedState:
    """Test circuit breaker in CLOSED state"""

    async def test_successful_call_in_closed_state(self):
        """Test successful call when circuit is closed"""
        cb = CircuitBreaker(name="test_service")

        async def successful_func():
            return "success"

        result = await cb.call(successful_func)

        assert result == "success"
        assert cb._state == CircuitState.CLOSED
        assert cb._failure_count == 0

    async def test_failed_call_below_threshold(self):
        """Test failed call below failure threshold"""
        cb = CircuitBreaker(name="test_service", failure_threshold=5)

        async def failing_func():
            raise Exception("Test error")

        # Fail 4 times (below threshold)
        for i in range(4):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Circuit should still be closed
        assert cb._state == CircuitState.CLOSED
        assert cb._failure_count == 4

    async def test_failed_call_at_threshold(self):
        """Test failed call at failure threshold opens circuit"""
        cb = CircuitBreaker(name="test_service", failure_threshold=5)

        async def failing_func():
            raise Exception("Test error")

        # Fail 5 times (at threshold)
        for i in range(5):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Circuit should be open
        assert cb._state == CircuitState.OPEN
        assert cb._failure_count == 5

    async def test_success_resets_failure_count(self):
        """Test that success resets failure count in closed state"""
        cb = CircuitBreaker(name="test_service", failure_threshold=5)

        async def failing_func():
            raise Exception("Test error")

        async def successful_func():
            return "success"

        # Fail 3 times
        for i in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb._failure_count == 3

        # Succeed once
        await cb.call(successful_func)

        # Failure count should be reset
        assert cb._failure_count == 0
        assert cb._state == CircuitState.CLOSED


@pytest.mark.asyncio
class TestCircuitBreakerOpenState:
    """Test circuit breaker in OPEN state"""

    async def test_open_circuit_rejects_calls(self):
        """Test that open circuit rejects all calls"""
        cb = CircuitBreaker(name="test_service", failure_threshold=3)

        async def failing_func():
            raise Exception("Test error")

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb._state == CircuitState.OPEN

        # Try to call - should raise CircuitBreakerOpenException
        async def any_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenException) as exc_info:
            await cb.call(any_func)

        assert "test_service" in str(exc_info.value)

    async def test_open_circuit_transitions_to_half_open_after_timeout(self):
        """Test that open circuit transitions to half-open after timeout"""
        cb = CircuitBreaker(
            name="test_service",
            failure_threshold=2,
            timeout_seconds=0.1,  # Short timeout for testing
        )

        async def failing_func():
            raise Exception("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb._state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Next call should transition to half-open
        async def successful_func():
            return "success"

        result = await cb.call(successful_func)

        assert result == "success"
        assert cb._state == CircuitState.HALF_OPEN

    async def test_open_circuit_exception_details(self):
        """Test that open circuit exception includes details"""
        cb = CircuitBreaker(name="test_service", failure_threshold=2)

        async def failing_func():
            raise Exception("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Try to call
        async def any_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenException) as exc_info:
            await cb.call(any_func)

        exc = exc_info.value
        assert exc.details["service"] == "test_service"
        assert exc.details["failure_count"] == 2
        assert "last_failure" in exc.details


@pytest.mark.asyncio
class TestCircuitBreakerHalfOpenState:
    """Test circuit breaker in HALF_OPEN state"""

    async def test_half_open_success_increments_count(self):
        """Test that success in half-open increments success count"""
        cb = CircuitBreaker(
            name="test_service", failure_threshold=2, timeout_seconds=0.1, success_threshold=2
        )

        async def failing_func():
            raise Exception("Test error")

        async def successful_func():
            return "success"

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(0.15)

        # First success in half-open
        result = await cb.call(successful_func)
        assert result == "success"
        assert cb._state == CircuitState.HALF_OPEN
        assert cb._success_count == 1

    async def test_half_open_closes_after_success_threshold(self):
        """Test that circuit closes after success threshold in half-open"""
        cb = CircuitBreaker(
            name="test_service", failure_threshold=2, timeout_seconds=0.1, success_threshold=2
        )

        async def failing_func():
            raise Exception("Test error")

        async def successful_func():
            return "success"

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Succeed twice (at threshold)
        await cb.call(successful_func)
        await cb.call(successful_func)

        # Circuit should be closed
        assert cb._state == CircuitState.CLOSED
        assert cb._success_count == 0
        assert cb._failure_count == 0

    async def test_half_open_reopens_on_failure(self):
        """Test that circuit reopens immediately on failure in half-open"""
        cb = CircuitBreaker(
            name="test_service", failure_threshold=2, timeout_seconds=0.1, success_threshold=2
        )

        async def failing_func():
            raise Exception("Test error")

        async def successful_func():
            return "success"

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(0.15)

        # First success
        await cb.call(successful_func)
        assert cb._state == CircuitState.HALF_OPEN

        # Fail once - should reopen immediately
        with pytest.raises(Exception):
            await cb.call(failing_func)

        assert cb._state == CircuitState.OPEN


class TestCircuitBreakerGetState:
    """Test circuit breaker state retrieval"""

    def test_get_state_closed(self):
        """Test getting state when circuit is closed"""
        cb = CircuitBreaker(name="test_service")

        state = cb.get_state()

        assert state["name"] == "test_service"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["success_count"] == 0
        assert state["failure_threshold"] == 5
        assert state["success_threshold"] == 2
        assert state["timeout_seconds"] == 60.0

    @pytest.mark.asyncio
    async def test_get_state_open(self):
        """Test getting state when circuit is open"""
        cb = CircuitBreaker(name="test_service", failure_threshold=2)

        async def failing_func():
            raise Exception("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        state = cb.get_state()

        assert state["state"] == "open"
        assert state["failure_count"] == 2
        assert state["last_failure_time"] is not None

    @pytest.mark.asyncio
    async def test_get_state_half_open(self):
        """Test getting state when circuit is half-open"""
        cb = CircuitBreaker(name="test_service", failure_threshold=2, timeout_seconds=0.1)

        async def failing_func():
            raise Exception("Test error")

        async def successful_func():
            return "success"

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Transition to half-open
        await cb.call(successful_func)

        state = cb.get_state()

        assert state["state"] == "half_open"
        assert state["success_count"] == 1


class TestCircuitBreakerReset:
    """Test circuit breaker manual reset"""

    @pytest.mark.asyncio
    async def test_manual_reset_from_open(self):
        """Test manual reset from open state"""
        cb = CircuitBreaker(name="test_service", failure_threshold=2)

        async def failing_func():
            raise Exception("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb._state == CircuitState.OPEN

        # Manual reset
        cb.reset()

        assert cb._state == CircuitState.CLOSED
        assert cb._failure_count == 0
        assert cb._success_count == 0

    @pytest.mark.asyncio
    async def test_manual_reset_from_half_open(self):
        """Test manual reset from half-open state"""
        cb = CircuitBreaker(name="test_service", failure_threshold=2, timeout_seconds=0.1)

        async def failing_func():
            raise Exception("Test error")

        async def successful_func():
            return "success"

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Wait for timeout and transition to half-open
        await asyncio.sleep(0.15)
        await cb.call(successful_func)

        assert cb._state == CircuitState.HALF_OPEN

        # Manual reset
        cb.reset()

        assert cb._state == CircuitState.CLOSED
        assert cb._failure_count == 0
        assert cb._success_count == 0

    def test_manual_reset_from_closed(self):
        """Test manual reset from closed state"""
        cb = CircuitBreaker(name="test_service")

        assert cb._state == CircuitState.CLOSED

        # Manual reset (should remain closed)
        cb.reset()

        assert cb._state == CircuitState.CLOSED


class TestCircuitBreakerEdgeCases:
    """Test edge cases"""

    @pytest.mark.asyncio
    async def test_zero_failure_threshold(self):
        """Test with zero failure threshold"""
        cb = CircuitBreaker(name="test_service", failure_threshold=0)

        async def failing_func():
            raise Exception("Test error")

        # Circuit should never open with 0 threshold
        for i in range(5):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Should still be closed (0 threshold means never open)
        assert cb._state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_very_short_timeout(self):
        """Test with very short timeout"""
        cb = CircuitBreaker(name="test_service", failure_threshold=1, timeout_seconds=0.01)  # 10ms

        async def failing_func():
            raise Exception("Test error")

        async def successful_func():
            return "success"

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_func)

        # Wait for very short timeout
        await asyncio.sleep(0.02)

        # Should transition to half-open
        result = await cb.call(successful_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_exception_propagation(self):
        """Test that original exceptions are propagated"""
        cb = CircuitBreaker(name="test_service")

        class CustomException(Exception):
            pass

        async def failing_func():
            raise CustomException("Custom error")

        with pytest.raises(CustomException) as exc_info:
            await cb.call(failing_func)

        assert str(exc_info.value) == "Custom error"

    @pytest.mark.asyncio
    async def test_async_function_with_args(self):
        """Test circuit breaker with async function that takes arguments"""
        cb = CircuitBreaker(name="test_service")

        async def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = await cb.call(func_with_args, "x", "y", c="z")

        assert result == "x-y-z"

    @pytest.mark.asyncio
    async def test_multiple_circuit_breakers(self):
        """Test multiple independent circuit breakers"""
        cb1 = CircuitBreaker(name="service1", failure_threshold=2)
        cb2 = CircuitBreaker(name="service2", failure_threshold=2)

        async def failing_func():
            raise Exception("Test error")

        # Open circuit 1
        for i in range(2):
            with pytest.raises(Exception):
                await cb1.call(failing_func)

        # Circuit 1 should be open, circuit 2 should be closed
        assert cb1._state == CircuitState.OPEN
        assert cb2._state == CircuitState.CLOSED
