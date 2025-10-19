"""
Self-healing mechanisms for service failures
Project Creator: Herman Swanepoel
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.models import HealthStatus, ServiceHealth

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern implementation
    Prevents cascading failures
    """

    def __init__(
        self, failure_threshold: int = 5, timeout: float = 60.0, success_threshold: int = 2
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Failures before opening circuit
            timeout: Time before attempting recovery (seconds)
            success_threshold: Successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change: float = time.time()

    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if time.time() - self.last_failure_time >= self.timeout:
                logger.info("Circuit breaker: Attempting recovery (HALF_OPEN)")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    async def call_async(self, func: Callable, *args, **kwargs):
        """Async version of call"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout:
                logger.info("Circuit breaker: Attempting recovery (HALF_OPEN)")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call"""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info("Circuit breaker: Recovery successful (CLOSED)")
                self.state = CircuitState.CLOSED
                self.last_state_change = time.time()

    def _on_failure(self) -> None:
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker: Recovery failed (OPEN)")
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif self.failure_count >= self.failure_threshold:
            logger.warning("Circuit breaker: Threshold reached (OPEN)")
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()

    def reset(self) -> None:
        """Reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = time.time()

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time,
            "time_in_state": time.time() - self.last_state_change,
        }


class SelfHealingManager:
    """
    Manages self-healing mechanisms for services
    Automatic recovery from failures
    """

    def __init__(self):
        """Initialize self-healing manager"""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.service_health: Dict[str, ServiceHealth] = {}
        self.recovery_strategies: Dict[str, Callable] = {}
        self.failure_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Statistics
        self.total_failures = 0
        self.total_recoveries = 0
        self.auto_recoveries = 0

    def register_service(
        self,
        service_name: str,
        health_check: Callable,
        recovery_strategy: Optional[Callable] = None,
        circuit_breaker_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a service for monitoring

        Args:
            service_name: Service identifier
            health_check: Function to check service health
            recovery_strategy: Function to attempt recovery
            circuit_breaker_config: Circuit breaker configuration
        """
        # Create circuit breaker
        config = circuit_breaker_config or {}
        self.circuit_breakers[service_name] = CircuitBreaker(
            failure_threshold=config.get("failure_threshold", 5),
            timeout=config.get("timeout", 60.0),
            success_threshold=config.get("success_threshold", 2),
        )

        # Register recovery strategy
        if recovery_strategy:
            self.recovery_strategies[service_name] = recovery_strategy

        # Initialize health status
        self.service_health[service_name] = ServiceHealth(
            service_name=service_name, status=HealthStatus.UNKNOWN
        )

        logger.info(f"Registered service for self-healing: {service_name}")

    async def check_service_health(self, service_name: str) -> ServiceHealth:
        """
        Check health of a service

        Args:
            service_name: Service identifier

        Returns:
            Service health status
        """
        if service_name not in self.circuit_breakers:
            return ServiceHealth(
                service_name=service_name,
                status=HealthStatus.UNKNOWN,
                details={"error": "Service not registered"},
            )

        circuit = self.circuit_breakers[service_name]

        # Determine health based on circuit state
        if circuit.state == CircuitState.CLOSED:
            status = HealthStatus.HEALTHY
        elif circuit.state == CircuitState.HALF_OPEN:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        health = ServiceHealth(
            service_name=service_name, status=status, details=circuit.get_state()
        )

        self.service_health[service_name] = health
        return health

    async def execute_with_healing(self, service_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with self-healing protection

        Args:
            service_name: Service identifier
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            Function result
        """
        if service_name not in self.circuit_breakers:
            raise ValueError(f"Service not registered: {service_name}")

        circuit = self.circuit_breakers[service_name]

        try:
            # Execute with circuit breaker
            if asyncio.iscoroutinefunction(func):
                result = await circuit.call_async(func, *args, **kwargs)
            else:
                result = circuit.call(func, *args, **kwargs)

            return result

        except Exception as e:
            self.total_failures += 1
            self.failure_history[service_name].append({"timestamp": time.time(), "error": str(e)})

            logger.error(f"Service failure: {service_name} - {e}")

            # Attempt recovery
            if service_name in self.recovery_strategies:
                try:
                    logger.info(f"Attempting auto-recovery: {service_name}")
                    recovery_func = self.recovery_strategies[service_name]

                    if asyncio.iscoroutinefunction(recovery_func):
                        await recovery_func()
                    else:
                        recovery_func()

                    self.auto_recoveries += 1
                    self.total_recoveries += 1
                    logger.info(f"✓ Auto-recovery successful: {service_name}")

                    # Reset circuit breaker
                    circuit.reset()

                    # Retry operation
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)

                except Exception as recovery_error:
                    logger.error(f"Auto-recovery failed: {service_name} - {recovery_error}")

            raise

    async def monitor_all_services(self) -> Dict[str, ServiceHealth]:
        """
        Check health of all registered services

        Returns:
            Dictionary of service health statuses
        """
        health_statuses = {}

        for service_name in self.circuit_breakers.keys():
            health = await self.check_service_health(service_name)
            health_statuses[service_name] = health

        return health_statuses

    async def attempt_recovery_all(self) -> Dict[str, bool]:
        """
        Attempt recovery for all unhealthy services

        Returns:
            Dictionary of recovery results
        """
        results = {}

        for service_name, health in self.service_health.items():
            if health.status == HealthStatus.UNHEALTHY:
                if service_name in self.recovery_strategies:
                    try:
                        logger.info(f"Attempting recovery: {service_name}")
                        recovery_func = self.recovery_strategies[service_name]

                        if asyncio.iscoroutinefunction(recovery_func):
                            await recovery_func()
                        else:
                            recovery_func()

                        self.total_recoveries += 1
                        results[service_name] = True

                        # Reset circuit breaker
                        self.circuit_breakers[service_name].reset()

                    except Exception as e:
                        logger.error(f"Recovery failed for {service_name}: {e}")
                        results[service_name] = False
                else:
                    results[service_name] = False

        return results

    def get_failure_history(self, service_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get failure history for a service

        Args:
            service_name: Service identifier
            limit: Maximum number of failures to return

        Returns:
            List of failure records
        """
        history = list(self.failure_history.get(service_name, []))
        return history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get self-healing statistics"""
        healthy_count = sum(
            1 for h in self.service_health.values() if h.status == HealthStatus.HEALTHY
        )

        return {
            "total_services": len(self.circuit_breakers),
            "healthy_services": healthy_count,
            "total_failures": self.total_failures,
            "total_recoveries": self.total_recoveries,
            "auto_recoveries": self.auto_recoveries,
            "recovery_rate": (
                self.auto_recoveries / self.total_failures if self.total_failures > 0 else 0.0
            ),
        }

    async def start_monitoring(self, interval: float = 30.0) -> None:
        """
        Start background monitoring of all services

        Args:
            interval: Check interval in seconds
        """
        logger.info(f"Starting service health monitoring (interval: {interval}s)")

        while True:
            try:
                await asyncio.sleep(interval)

                health_statuses = await self.monitor_all_services()

                # Log unhealthy services
                unhealthy = [
                    name
                    for name, health in health_statuses.items()
                    if health.status == HealthStatus.UNHEALTHY
                ]

                if unhealthy:
                    logger.warning(f"Unhealthy services: {', '.join(unhealthy)}")

                    # Attempt recovery
                    recovery_results = await self.attempt_recovery_all()
                    successful = [k for k, v in recovery_results.items() if v]

                    if successful:
                        logger.info(f"✓ Recovered services: {', '.join(successful)}")

            except asyncio.CancelledError:
                logger.info("Service monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Error in service monitoring: {e}")
