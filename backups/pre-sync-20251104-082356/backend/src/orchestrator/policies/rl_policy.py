"""
Reinforcement Learning Policy for Predictive Caching
Project Creator: Herman Swanepoel
"""

import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from catboost import CatBoostClassifier

logger = logging.getLogger(__name__)


class PredictivePolicy:
    """
    Reinforcement learning policy for predictive caching.

    Uses CatBoost to predict next likely actions based on user activity
    patterns, enabling pre-warming of models and memory segments.
    """

    def __init__(self, model_path: Optional[str] = None, min_history_size: int = 100) -> None:
        """
        Initialize predictive policy.

        Args:
            model_path: Path to saved model (optional)
            min_history_size: Minimum history size before training
        """
        self.model = CatBoostClassifier(
            iterations=100,
            depth=4,
            learning_rate=0.1,
            loss_function="MultiClass",
            verbose=False,
            random_seed=42,
        )

        self.history: List[Dict[str, Any]] = []
        self.min_history_size = min_history_size
        self.is_trained = False
        self.model_path = Path(model_path) if model_path else None

        # Load existing model if available
        if self.model_path and self.model_path.exists():
            self._load_model()

        # Action mapping
        self.action_types = [
            "code_completion",
            "refactor",
            "explain",
            "generate",
            "debug",
            "optimize",
            "test",
        ]

        logger.info("PredictivePolicy initialized")

    def observe(
        self,
        event: str,
        language: str,
        hour: int,
        file_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record user activity.

        Args:
            event: Event type (action taken)
            language: Programming language
            hour: Hour of day (0-23)
            file_type: File extension
            context: Additional context
        """
        observation = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "language": language,
            "hour": hour,
            "file_type": file_type,
            "context": context or {},
        }

        self.history.append(observation)

        # Limit history size
        if len(self.history) > 10000:
            self.history = self.history[-5000:]

        logger.debug(f"Observed event: {event} ({language})")

        # Auto-train if enough data
        if len(self.history) >= self.min_history_size and not self.is_trained:
            self.train()

    def predict(self, current_context: Dict[str, Any]) -> List[str]:
        """
        Predict next likely actions.

        Args:
            current_context: Current context dict with keys:
                - hour: int
                - language: str
                - file_type: str
                - recent_actions: List[str] (optional)

        Returns:
            List of models to pre-warm
        """
        if not self.is_trained or len(self.history) < self.min_history_size:
            logger.debug("Model not trained, returning default predictions")
            return self._get_default_predictions(current_context)

        try:
            # Extract features
            features = self._extract_features(current_context)

            # Predict
            prediction_probs = self.model.predict_proba([features])[0]

            # Get top 3 predictions
            top_indices = np.argsort(prediction_probs)[-3:][::-1]
            top_actions = [self.action_types[i] for i in top_indices]

            # Map to models
            models = []
            for action in top_actions:
                models.extend(self._action_to_models(action))

            # Remove duplicates while preserving order
            models = list(dict.fromkeys(models))

            logger.info(f"Predicted actions: {top_actions}")
            return models[:3]  # Return top 3 models

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return self._get_default_predictions(current_context)

    def train(self) -> bool:
        """
        Train the prediction model on accumulated history.

        Returns:
            True if training successful
        """
        if len(self.history) < self.min_history_size:
            logger.warning(f"Insufficient history for training: {len(self.history)}")
            return False

        try:
            logger.info(f"Training model on {len(self.history)} observations")

            # Prepare training data
            X = []
            y = []

            for i in range(len(self.history) - 1):
                current = self.history[i]
                next_event = self.history[i + 1]["event"]

                # Extract features from current observation
                features = self._extract_features(
                    {
                        "hour": current["hour"],
                        "language": current["language"],
                        "file_type": current["file_type"],
                    }
                )

                X.append(features)

                # Map event to action type
                if next_event in self.action_types:
                    y.append(next_event)
                else:
                    y.append("code_completion")  # Default

            # Train model
            self.model.fit(X, y)
            self.is_trained = True

            # Save model if path provided
            if self.model_path:
                self._save_model()

            logger.info("Model training complete")
            return True

        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False

    def evaluate(self) -> Dict[str, float]:
        """
        Evaluate model accuracy on recent history.

        Returns:
            Dict with evaluation metrics
        """
        if not self.is_trained or len(self.history) < 50:
            return {"accuracy": 0.0, "samples": 0}

        try:
            # Use last 50 observations for evaluation
            eval_data = self.history[-50:]
            correct = 0
            total = 0

            for i in range(len(eval_data) - 1):
                current = eval_data[i]
                actual_next = eval_data[i + 1]["event"]

                # Predict
                predicted_models = self.predict(
                    {
                        "hour": current["hour"],
                        "language": current["language"],
                        "file_type": current["file_type"],
                    }
                )

                # Check if prediction matches
                predicted_actions = [self._model_to_action(m) for m in predicted_models]

                if actual_next in predicted_actions:
                    correct += 1
                total += 1

            accuracy = correct / total if total > 0 else 0.0

            logger.info(f"Model accuracy: {accuracy:.2%}")
            return {"accuracy": accuracy, "samples": total, "correct": correct}

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {"accuracy": 0.0, "samples": 0}

    def _extract_features(self, context: Dict[str, Any]) -> List[float]:
        """Extract features from context"""
        hour = context.get("hour", 12)
        language = context.get("language", "python")
        file_type = context.get("file_type", ".py")

        # Encode features
        features = [
            float(hour),
            float(hash(language) % 100),
            float(hash(file_type) % 100),
            # Add time-based features
            float(hour < 12),  # Morning
            float(12 <= hour < 18),  # Afternoon
            float(hour >= 18),  # Evening
        ]

        return features

    def _action_to_models(self, action: str) -> List[str]:
        """Map predicted action to required models"""
        mapping = {
            # Inline completions and snippet continuations
            "code_completion": ["codellama:7b-instruct"],
            # Refactors and deep reasoning (default 7B; upgrade to 8B/12B
            # when GPU allows)
            "refactor": ["mistral:7b"],
            # Conversational explanations and UX layer
            "explain": ["gemma2:9b"],
            # Code generation
            "generate": ["codellama:7b-instruct"],
            # Debugging and analytical review
            "debug": ["mistral:7b"],
            # Performance optimization and tests scaffolding
            "optimize": ["codellama:7b-instruct"],
            "test": ["codellama:7b-instruct"],
        }
        return mapping.get(action, ["codellama:7b-instruct"])

    def _model_to_action(self, model: str) -> str:
        """Map model to action type"""
        if "codellama" in model:
            return "code_completion"
        elif "llama3.2" in model:
            return "explain"
        elif "mistral-nemo" in model or "mistral" in model:
            return "refactor"
        return "code_completion"

    def _get_default_predictions(self, context: Dict[str, Any]) -> List[str]:
        """Get default predictions when model not trained"""
        # Return most common models
        return ["codellama:7b-instruct", "mistral:7b"]

    def _save_model(self) -> bool:
        """Save model to disk"""
        if self.model_path is None:
            return False

        try:
            model_path = self.model_path
            # mypy: model_path is not None here
            model_path.parent.mkdir(parents=True, exist_ok=True)

            # Save model
            self.model.save_model(str(model_path))

            # Save history
            history_path = model_path.with_suffix(".history.pkl")
            with open(history_path, "wb") as f:
                pickle.dump(self.history, f)

            logger.info(f"Saved model to {model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False

    def _load_model(self) -> bool:
        """Load model from disk"""
        try:
            if self.model_path is None:
                return False
            model_path = self.model_path
            # Load model
            self.model.load_model(str(model_path))
            self.is_trained = True

            # Load history
            history_path = model_path.with_suffix(".history.pkl")
            if history_path.exists():
                with open(history_path, "rb") as f:
                    self.history = pickle.load(f)

            logger.info(f"Loaded model from {model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get policy statistics"""
        return {
            "history_size": len(self.history),
            "is_trained": self.is_trained,
            "min_history_size": self.min_history_size,
            "action_types": self.action_types,
        }
