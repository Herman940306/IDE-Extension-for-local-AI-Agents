"""
Predictive caching based on user behavior patterns
Project Creator: Herman Swanepoel
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from src.models import CachePrediction

logger = logging.getLogger(__name__)


class AccessPattern:
    """Tracks access patterns for a resource"""

    def __init__(self, resource_id: str):
        self.resource_id = resource_id
        self.access_times: deque = deque(maxlen=100)  # Last 100 accesses
        self.access_count = 0
        self.last_access = None
        self.access_intervals: deque = deque(maxlen=50)

    def record_access(self) -> None:
        """Record an access"""
        now = time.time()

        if self.last_access:
            interval = now - self.last_access
            self.access_intervals.append(interval)

        self.access_times.append(now)
        self.access_count += 1
        self.last_access = now

    def get_average_interval(self) -> Optional[float]:
        """Get average time between accesses"""
        if not self.access_intervals:
            return None
        return sum(self.access_intervals) / len(self.access_intervals)

    def predict_next_access(self) -> Optional[float]:
        """Predict next access time"""
        if not self.last_access or not self.access_intervals:
            return None

        avg_interval = self.get_average_interval()
        if avg_interval:
            return self.last_access + avg_interval
        return None

    def get_confidence(self) -> float:
        """Get prediction confidence based on pattern consistency"""
        if len(self.access_intervals) < 3:
            return 0.0

        # Calculate variance in intervals
        avg = self.get_average_interval()
        if not avg:
            return 0.0

        variance = sum((x - avg) ** 2 for x in self.access_intervals) / len(self.access_intervals)
        stddev = variance**0.5

        # Lower variance = higher confidence
        coefficient_of_variation = stddev / avg if avg > 0 else 1.0
        confidence = max(0.0, 1.0 - coefficient_of_variation)

        return min(1.0, confidence)


class PredictiveCacheManager:
    """
    Manages predictive caching based on user behavior
    Pre-loads frequently accessed resources
    """

    def __init__(self, prediction_threshold: float = 0.6, preload_window: float = 60.0):
        """
        Initialize predictive cache manager

        Args:
            prediction_threshold: Minimum confidence for predictions
            preload_window: Time window (seconds) for preloading
        """
        self.prediction_threshold = prediction_threshold
        self.preload_window = preload_window

        # Track access patterns
        self.patterns: Dict[str, AccessPattern] = {}

        # Track resource relationships (co-access patterns)
        self.co_access: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.recent_accesses: deque = deque(maxlen=10)

        # Preload callbacks
        self.preload_callbacks: Dict[str, Callable] = {}

        # Statistics
        self.predictions_made = 0
        self.predictions_correct = 0
        self.cache_hits_saved = 0

    def record_access(self, resource_id: str) -> None:
        """
        Record resource access

        Args:
            resource_id: Resource identifier
        """
        # Update access pattern
        if resource_id not in self.patterns:
            self.patterns[resource_id] = AccessPattern(resource_id)

        self.patterns[resource_id].record_access()

        # Update co-access patterns
        for recent_id in self.recent_accesses:
            if recent_id != resource_id:
                self.co_access[recent_id][resource_id] += 1

        self.recent_accesses.append(resource_id)

        logger.debug(f"Recorded access: {resource_id}")

    def get_predictions(self, top_k: int = 5) -> List[CachePrediction]:
        """
        Get predictions for resources likely to be accessed soon

        Args:
            top_k: Number of predictions to return

        Returns:
            List of cache predictions
        """
        predictions = []
        current_time = time.time()

        # Predict based on access patterns
        for resource_id, pattern in self.patterns.items():
            next_access = pattern.predict_next_access()
            if not next_access:
                continue

            confidence = pattern.get_confidence()
            if confidence < self.prediction_threshold:
                continue

            # Check if predicted access is within preload window
            time_until_access = next_access - current_time
            if 0 < time_until_access <= self.preload_window:
                predictions.append(
                    CachePrediction(
                        key=resource_id,
                        predicted_access_time=datetime.fromtimestamp(next_access),
                        confidence=confidence,
                        access_pattern="temporal",
                        metadata={
                            "access_count": pattern.access_count,
                            "avg_interval": pattern.get_average_interval(),
                            "time_until_access": time_until_access,
                        },
                    )
                )

        # Predict based on co-access patterns
        if self.recent_accesses:
            last_access = self.recent_accesses[-1]
            if last_access in self.co_access:
                for related_id, count in self.co_access[last_access].items():
                    # Calculate confidence based on co-access frequency
                    total_accesses = self.patterns[last_access].access_count
                    confidence = min(1.0, count / total_accesses) if total_accesses > 0 else 0.0

                    if confidence >= self.prediction_threshold:
                        predictions.append(
                            CachePrediction(
                                key=related_id,
                                predicted_access_time=datetime.fromtimestamp(
                                    current_time + 5
                                ),  # Soon
                                confidence=confidence,
                                access_pattern="co-access",
                                metadata={
                                    "trigger": last_access,
                                    "co_access_count": count,
                                },
                            )
                        )

        # Sort by confidence and return top_k
        predictions.sort(key=lambda x: x.confidence, reverse=True)
        return predictions[:top_k]

    def register_preload_callback(self, resource_type: str, callback: Callable[[str], Any]) -> None:
        """
        Register callback for preloading resources

        Args:
            resource_type: Type of resource
            callback: Async function to preload resource
        """
        self.preload_callbacks[resource_type] = callback
        logger.info(f"Registered preload callback for: {resource_type}")

    async def execute_predictions(self) -> Dict[str, Any]:
        """
        Execute predictions by preloading resources

        Returns:
            Results of preloading operations
        """
        predictions = self.get_predictions()
        results = {
            "predictions": len(predictions),
            "preloaded": 0,
            "failed": 0,
            "skipped": 0,
        }

        for prediction in predictions:
            try:
                # Extract resource type from key
                resource_type = prediction.key.split(":")[0] if ":" in prediction.key else "default"

                if resource_type in self.preload_callbacks:
                    callback = self.preload_callbacks[resource_type]
                    await callback(prediction.key)
                    results["preloaded"] += 1
                    self.predictions_made += 1
                    logger.debug(
                        f"Preloaded: {prediction.key} (confidence: {prediction.confidence:.2f})"  # noqa: E501
                    )
                else:
                    results["skipped"] += 1

            except Exception as e:
                logger.error(f"Failed to preload {prediction.key}: {e}")
                results["failed"] += 1

        return results

    def validate_prediction(self, resource_id: str) -> None:
        """
        Validate that a prediction was correct

        Args:
            resource_id: Resource that was accessed
        """
        # Check if this was predicted
        predictions = self.get_predictions(top_k=10)
        if any(p.key == resource_id for p in predictions):
            self.predictions_correct += 1
            self.cache_hits_saved += 1
            logger.debug(f"Prediction validated: {resource_id}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get predictive caching statistics"""
        accuracy = (
            self.predictions_correct / self.predictions_made if self.predictions_made > 0 else 0.0
        )

        return {
            "tracked_resources": len(self.patterns),
            "predictions_made": self.predictions_made,
            "predictions_correct": self.predictions_correct,
            "accuracy": round(accuracy, 3),
            "cache_hits_saved": self.cache_hits_saved,
            "co_access_patterns": len(self.co_access),
            "active_predictions": len(self.get_predictions()),
        }

    def get_top_resources(self, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Get most frequently accessed resources

        Args:
            top_k: Number of resources to return

        Returns:
            List of top resources with statistics
        """
        resources = []

        for resource_id, pattern in self.patterns.items():
            resources.append(
                {
                    "resource_id": resource_id,
                    "access_count": pattern.access_count,
                    "avg_interval": pattern.get_average_interval(),
                    "confidence": pattern.get_confidence(),
                }
            )

        resources.sort(key=lambda x: x["access_count"], reverse=True)
        return resources[:top_k]

    def clear_patterns(self) -> None:
        """Clear all learned patterns"""
        self.patterns.clear()
        self.co_access.clear()
        self.recent_accesses.clear()
        logger.info("Predictive cache patterns cleared")

    async def start_background_preloading(self, interval: float = 30.0) -> None:
        """
        Start background task for predictive preloading

        Args:
            interval: Interval between preload checks (seconds)
        """
        logger.info(f"Starting background preloading (interval: {interval}s)")

        while True:
            try:
                await asyncio.sleep(interval)
                results = await self.execute_predictions()

                if results["preloaded"] > 0:
                    logger.info(
                        f"Predictive preload: {results['preloaded']} resources "
                        f"(predictions: {results['predictions']})"
                    )

            except asyncio.CancelledError:
                logger.info("Background preloading stopped")
                break
            except Exception as e:
                logger.error(f"Error in background preloading: {e}")
