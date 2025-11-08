"""
Metrics Service - Performance Tracking and Auto-Tuning
Project Creator: Herman Swanepoel

Tracks model performance metrics: latency, success rate, call count.
Provides auto-tuning recommendations based on performance thresholds.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Performance metrics tracking and analysis service.

    Tracks per-model:
    - Total calls
    - Average latency
    - Success rate
    - Error count
    - Last used timestamp
    """

    def __init__(self, metrics_path: Optional[Path] = None) -> None:
        """
        Initialize metrics service.

        Args:
            metrics_path: Path to metrics persistence file
        """
        self.metrics_path = metrics_path or Path("aura_metrics.json")
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

        # Performance thresholds for auto-tuning
        self.high_latency_threshold = 5.0  # seconds
        self.low_success_threshold = 0.7  # 70%

        # Load existing metrics
        self._load_metrics()
        logger.info("Metrics Service initialized")

    def _load_metrics(self) -> None:
        """Load metrics from persistence file."""
        if self.metrics_path.exists():
            try:
                with open(self.metrics_path, "r") as f:
                    self.metrics = json.load(f)
                logger.info("Loaded metrics for %d models", len(self.metrics))
            except Exception as e:
                logger.warning("Failed to load metrics: %s", e)
                self.metrics = {}
        else:
            self.metrics = {}

    def _persist_metrics(self) -> None:
        """Persist metrics to file."""
        try:
            with open(self.metrics_path, "w") as f:
                json.dump(self.metrics, f, indent=2)
            logger.debug("Persisted metrics for %d models", len(self.metrics))
        except Exception as e:
            logger.error("Failed to persist metrics: %s", e)

    def record_call(
        self,
        model: str,
        latency: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Record a model call with performance data.

        Args:
            model: Model name
            latency: Call duration in seconds
            success: Whether call succeeded
            error: Error message if failed
        """
        with self.lock:
            if model not in self.metrics:
                self.metrics[model] = {
                    "calls": 0,
                    "total_latency": 0.0,
                    "avg_latency": 0.0,
                    "success_count": 0,
                    "error_count": 0,
                    "success_rate": 0.0,
                    "last_used": None,
                    "errors": [],
                }

            m = self.metrics[model]
            m["calls"] += 1
            m["total_latency"] += latency
            m["avg_latency"] = m["total_latency"] / m["calls"]

            if success:
                m["success_count"] += 1
            else:
                m["error_count"] += 1
                if error and len(m["errors"]) < 10:  # Keep last 10 errors
                    m["errors"].append(
                        {
                            "timestamp": time.time(),
                            "error": error,
                        }
                    )

            m["success_rate"] = m["success_count"] / m["calls"]
            m["last_used"] = time.time()

            # Persist after each update
            self._persist_metrics()

            logger.debug(
                "Recorded call for %s: %.2fs, success=%s (total=%d)",
                model,
                latency,
                success,
                m["calls"],
            )

    def get_model_metrics(self, model: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific model.

        Args:
            model: Model name

        Returns:
            Metrics dict or None if no data
        """
        with self.lock:
            return self.metrics.get(model)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all models."""
        with self.lock:
            return dict(self.metrics)  # Return copy

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.

        Returns:
            Report with summary stats and per-model details
        """
        with self.lock:
            total_calls = sum(m["calls"] for m in self.metrics.values())
            total_success = sum(m["success_count"] for m in self.metrics.values())
            total_errors = sum(m["error_count"] for m in self.metrics.values())

            # Calculate weighted average latency
            weighted_latency = 0.0
            if total_calls > 0:
                weighted_latency = (
                    sum(m["avg_latency"] * m["calls"] for m in self.metrics.values()) / total_calls
                )

            # Identify problematic models
            high_latency_models = [
                model
                for model, m in self.metrics.items()
                if m["avg_latency"] > self.high_latency_threshold
            ]

            low_success_models = [
                model
                for model, m in self.metrics.items()
                if m["success_rate"] < self.low_success_threshold
                and m["calls"] >= 5  # Minimum sample size
            ]

            return {
                "summary": {
                    "total_calls": total_calls,
                    "total_success": total_success,
                    "total_errors": total_errors,
                    "overall_success_rate": (
                        total_success / total_calls if total_calls > 0 else 0.0
                    ),
                    "avg_latency": weighted_latency,
                    "models_tracked": len(self.metrics),
                },
                "issues": {
                    "high_latency_models": high_latency_models,
                    "low_success_models": low_success_models,
                },
                "models": dict(self.metrics),
            }

    def get_auto_tune_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate auto-tuning recommendations based on metrics.

        Returns:
            List of recommendation dicts with:
                - model: Model name
                - issue: Issue type
                - recommendation: Suggested action
                - severity: 'high', 'medium', 'low'
        """
        recommendations = []

        with self.lock:
            for model, m in self.metrics.items():
                # Skip models with insufficient data
                if m["calls"] < 3:
                    continue

                # High latency check
                if m["avg_latency"] > self.high_latency_threshold:
                    recommendations.append(
                        {
                            "model": model,
                            "issue": "high_latency",
                            "recommendation": (
                                f"Model {model} has high avg latency "
                                f"({m['avg_latency']:.2f}s). "
                                f"Consider using a smaller/quantized version "
                                f"or enabling CPU fallback."
                            ),
                            "severity": "high",
                            "avg_latency": m["avg_latency"],
                        }
                    )

                # Low success rate check
                if m["success_rate"] < self.low_success_threshold and m["calls"] >= 5:
                    recommendations.append(
                        {
                            "model": model,
                            "issue": "low_success_rate",
                            "recommendation": (
                                f"Model {model} has low success rate "
                                f"({m['success_rate']:.1%}). "
                                f"Check model availability and configuration."
                            ),
                            "severity": "high",
                            "success_rate": m["success_rate"],
                        }
                    )

                # Moderate latency check
                elif m["avg_latency"] > 3.0:
                    recommendations.append(
                        {
                            "model": model,
                            "issue": "moderate_latency",
                            "recommendation": (
                                f"Model {model} has moderate latency "
                                f"({m['avg_latency']:.2f}s). "
                                f"Monitor for performance degradation."
                            ),
                            "severity": "medium",
                            "avg_latency": m["avg_latency"],
                        }
                    )

        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: severity_order[x["severity"]])

        logger.info("Generated %d auto-tune recommendations", len(recommendations))
        return recommendations

    def reset_model_metrics(self, model: str) -> None:
        """Reset metrics for a specific model."""
        with self.lock:
            if model in self.metrics:
                del self.metrics[model]
                self._persist_metrics()
                logger.info("Reset metrics for model: %s", model)

    def reset_all_metrics(self) -> None:
        """Reset all metrics."""
        with self.lock:
            self.metrics.clear()
            self._persist_metrics()
            logger.info("Reset all metrics")

    def get_model_usage_stats(self) -> List[Dict[str, Any]]:
        """
        Get model usage statistics sorted by call count.

        Returns:
            List of model stats sorted by usage
        """
        with self.lock:
            stats = []
            for model, m in self.metrics.items():
                stats.append(
                    {
                        "model": model,
                        "calls": m["calls"],
                        "avg_latency": m["avg_latency"],
                        "success_rate": m["success_rate"],
                        "last_used": m["last_used"],
                    }
                )

            # Sort by call count descending
            stats.sort(key=lambda x: x["calls"], reverse=True)
            return stats
