"""
Telemetry service for ML-driven optimization
Project Creator: Herman Swanepoel
"""

import asyncio
import logging
import statistics
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from src.models import Metric, MetricType

logger = logging.getLogger(__name__)


class TelemetryService:
    """
    Collects and analyzes metrics for ML-driven optimization
    Privacy-preserving, local-only telemetry
    """

    def __init__(self, max_metrics: int = 10000):
        """
        Initialize telemetry service

        Args:
            max_metrics: Maximum number of metrics to store in memory
        """
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.aggregated_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.enabled = True

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a metric

        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            unit: Unit of measurement
            tags: Tags for filtering/grouping
            metadata: Additional metadata
        """
        if not self.enabled:
            return

        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            unit=unit,
            tags=tags or {},
            metadata=metadata or {},
        )

        self.metrics.append(metric)
        self._update_aggregations(metric)

    def _update_aggregations(self, metric: Metric) -> None:
        """Update aggregated metrics"""
        key = f"{metric.name}_{metric.type.value}"

        if key not in self.aggregated_metrics:
            self.aggregated_metrics[key] = {
                "count": 0,
                "sum": 0.0,
                "min": float("inf"),
                "max": float("-inf"),
                "values": deque(maxlen=1000),  # Keep last 1000 values
            }

        agg = self.aggregated_metrics[key]
        agg["count"] += 1
        agg["sum"] += metric.value
        agg["min"] = min(agg["min"], metric.value)
        agg["max"] = max(agg["max"], metric.value)
        agg["values"].append(metric.value)

    def get_metric_stats(self, name: str, metric_type: MetricType) -> Dict[str, Any]:
        """
        Get statistics for a metric

        Args:
            name: Metric name
            metric_type: Metric type

        Returns:
            Statistics dictionary
        """
        key = f"{name}_{metric_type.value}"
        agg = self.aggregated_metrics.get(key)

        if not agg or agg["count"] == 0:
            return {"error": "No data available"}

        values = list(agg["values"])

        return {
            "count": agg["count"],
            "mean": agg["sum"] / agg["count"],
            "min": agg["min"],
            "max": agg["max"],
            "median": statistics.median(values) if values else 0,
            "stddev": statistics.stdev(values) if len(values) > 1 else 0,
            "p95": (statistics.quantiles(values, n=20)[18] if len(values) >= 20 else agg["max"]),
            "p99": (statistics.quantiles(values, n=100)[98] if len(values) >= 100 else agg["max"]),
        }

    def get_all_metrics(self) -> List[Dict[str, Any]]:
        """Get all recorded metrics"""
        return [
            {
                "name": m.name,
                "type": m.type.value,
                "value": m.value,
                "unit": m.unit,
                "timestamp": m.timestamp.isoformat(),
                "tags": m.tags,
            }
            for m in self.metrics
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Get telemetry summary"""
        summary = {
            "total_metrics": len(self.metrics),
            "enabled": self.enabled,
            "metrics_by_type": defaultdict(int),
            "top_metrics": [],
        }

        # Count by type
        for metric in self.metrics:
            summary["metrics_by_type"][metric.type.value] += 1

        # Top metrics by count
        metric_counts = defaultdict(int)
        for metric in self.metrics:
            metric_counts[metric.name] += 1

        summary["top_metrics"] = sorted(
            [{"name": k, "count": v} for k, v in metric_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        return summary

    def clear_metrics(self) -> None:
        """Clear all metrics"""
        self.metrics.clear()
        self.aggregated_metrics.clear()
        logger.info("Telemetry metrics cleared")

    def enable(self) -> None:
        """Enable telemetry collection"""
        self.enabled = True
        logger.info("Telemetry enabled")

    def disable(self) -> None:
        """Disable telemetry collection"""
        self.enabled = False
        logger.info("Telemetry disabled")


# Global telemetry instance
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """Get global telemetry service instance"""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service


def track_latency(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """
    Decorator to track function latency

    Args:
        metric_name: Name of the metric
        tags: Optional tags

    Example:
        @track_latency("embedding_generation")
        async def generate_embedding(code: str):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                latency = (time.time() - start_time) * 1000  # Convert to ms

                telemetry = get_telemetry_service()
                telemetry.record_metric(
                    name=metric_name,
                    value=latency,
                    metric_type=MetricType.LATENCY,
                    unit="ms",
                    tags=tags or {},
                )

                return result
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                telemetry = get_telemetry_service()
                telemetry.record_metric(
                    name=f"{metric_name}_error",
                    value=latency,
                    metric_type=MetricType.ERROR,
                    unit="ms",
                    tags={**(tags or {}), "error": str(e)},
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                latency = (time.time() - start_time) * 1000

                telemetry = get_telemetry_service()
                telemetry.record_metric(
                    name=metric_name,
                    value=latency,
                    metric_type=MetricType.LATENCY,
                    unit="ms",
                    tags=tags or {},
                )

                return result
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                telemetry = get_telemetry_service()
                telemetry.record_metric(
                    name=f"{metric_name}_error",
                    value=latency,
                    metric_type=MetricType.ERROR,
                    unit="ms",
                    tags={**(tags or {}), "error": str(e)},
                )
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_accuracy(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """
    Decorator to track accuracy metrics

    Args:
        metric_name: Name of the metric
        tags: Optional tags
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Expect result to have 'accuracy' or 'confidence' field
            accuracy = None
            if isinstance(result, dict):
                accuracy = result.get("accuracy") or result.get("confidence")
            elif hasattr(result, "confidence"):
                accuracy = result.confidence

            if accuracy is not None:
                telemetry = get_telemetry_service()
                telemetry.record_metric(
                    name=metric_name,
                    value=float(accuracy),
                    metric_type=MetricType.ACCURACY,
                    unit="score",
                    tags=tags or {},
                )

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            accuracy = None
            if isinstance(result, dict):
                accuracy = result.get("accuracy") or result.get("confidence")
            elif hasattr(result, "confidence"):
                accuracy = result.confidence

            if accuracy is not None:
                telemetry = get_telemetry_service()
                telemetry.record_metric(
                    name=metric_name,
                    value=float(accuracy),
                    metric_type=MetricType.ACCURACY,
                    unit="score",
                    tags=tags or {},
                )

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_cache_hit(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """
    Track cache hit/miss

    Args:
        metric_name: Name of the metric
        tags: Optional tags
    """

    def record_hit():
        telemetry = get_telemetry_service()
        telemetry.record_metric(
            name=metric_name,
            value=1.0,
            metric_type=MetricType.CACHE_HIT,
            unit="hit",
            tags={**(tags or {}), "result": "hit"},
        )

    def record_miss():
        telemetry = get_telemetry_service()
        telemetry.record_metric(
            name=metric_name,
            value=0.0,
            metric_type=MetricType.CACHE_HIT,
            unit="miss",
            tags={**(tags or {}), "result": "miss"},
        )

    return record_hit, record_miss


def track_usage(metric_name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
    """
    Track usage metric

    Args:
        metric_name: Name of the metric
        value: Usage value
        tags: Optional tags
    """
    telemetry = get_telemetry_service()
    telemetry.record_metric(
        name=metric_name,
        value=value,
        metric_type=MetricType.USAGE,
        unit="count",
        tags=tags or {},
    )
