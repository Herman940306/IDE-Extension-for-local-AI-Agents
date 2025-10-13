"""
Task Router for intent detection and assignment
Project Creator: Herman Swanepoel
"""

from typing import Dict, Any, Optional
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class TaskIntent(str, Enum):
    """Task intent categories"""
    REFACTOR = "refactor"
    EXPLAIN = "explain"
    GENERATE = "generate"
    DEBUG = "debug"
    OPTIMIZE = "optimize"
    TEST = "test"
    DOCUMENT = "document"
    REVIEW = "review"
    UNKNOWN = "unknown"


class TaskRouter:
    """
    Task router for intent detection and agent assignment.
    
    Analyzes task descriptions and code context to determine
    the appropriate intent and routing strategy.
    """
    
    def __init__(self):
        """Initialize task router with intent patterns"""
        self.intent_patterns = self._build_intent_patterns()
        logger.info("TaskRouter initialized")
    
    def _build_intent_patterns(self) -> Dict[TaskIntent, list]:
        """Build regex patterns for intent detection"""
        return {
            TaskIntent.REFACTOR: [
                r"\brefactor\b",
                r"\brestructure\b",
                r"\bimprove\b.*\bcode\b",
                r"\bclean\s+up\b",
                r"\bsimplify\b"
            ],
            TaskIntent.EXPLAIN: [
                r"\bexplain\b",
                r"\bwhat\s+does\b",
                r"\bhow\s+does\b",
                r"\bwhy\b",
                r"\bdescribe\b",
                r"\bunderstand\b"
            ],
            TaskIntent.GENERATE: [
                r"\bgenerate\b",
                r"\bcreate\b",
                r"\bwrite\b",
                r"\bimplement\b",
                r"\badd\b.*\bfunction\b",
                r"\bmake\b.*\bclass\b"
            ],
            TaskIntent.DEBUG: [
                r"\bdebug\b",
                r"\bfix\b",
                r"\berror\b",
                r"\bbug\b",
                r"\bissue\b",
                r"\bproblem\b",
                r"\bnot\s+working\b"
            ],
            TaskIntent.OPTIMIZE: [
                r"\boptimize\b",
                r"\bperformance\b",
                r"\bfaster\b",
                r"\befficient\b",
                r"\bspeed\s+up\b"
            ],
            TaskIntent.TEST: [
                r"\btest\b",
                r"\bunit\s+test\b",
                r"\bintegration\s+test\b",
                r"\btest\s+case\b",
                r"\bcoverage\b"
            ],
            TaskIntent.DOCUMENT: [
                r"\bdocument\b",
                r"\bdocstring\b",
                r"\bcomment\b",
                r"\bdocumentation\b",
                r"\bREADME\b"
            ],
            TaskIntent.REVIEW: [
                r"\breview\b",
                r"\bcheck\b",
                r"\bvalidate\b",
                r"\binspect\b",
                r"\baudit\b"
            ]
        }
    
    def detect_intent(self, description: str) -> TaskIntent:
        """
        Detect task intent from description.
        
        Args:
            description: Task description text
            
        Returns:
            Detected TaskIntent
        """
        description_lower = description.lower()
        
        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description_lower):
                    logger.info(f"Detected intent: {intent.value}")
                    return intent
        
        logger.warning(f"Could not detect intent, defaulting to UNKNOWN")
        return TaskIntent.UNKNOWN
    
    def analyze_task(
        self,
        description: str,
        code_context: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze task and provide routing recommendations.
        
        Args:
            description: Task description
            code_context: Optional code context
            language: Optional programming language
            
        Returns:
            Dict containing intent, complexity, and routing info
        """
        intent = self.detect_intent(description)
        
        # Estimate complexity
        complexity = self._estimate_complexity(
            description,
            code_context,
            language
        )
        
        # Determine required capabilities
        capabilities = self._get_required_capabilities(intent)
        
        # Suggest agent priority
        agent_priority = self._suggest_agent_priority(intent, complexity)
        
        analysis = {
            "intent": intent.value,
            "complexity": complexity,
            "capabilities": capabilities,
            "agent_priority": agent_priority,
            "requires_verification": complexity > 0.5 or intent in [
                TaskIntent.GENERATE,
                TaskIntent.REFACTOR,
                TaskIntent.DEBUG
            ]
        }
        
        logger.info(f"Task analysis: intent={intent.value}, complexity={complexity:.2f}")
        return analysis
    
    def _estimate_complexity(
        self,
        description: str,
        code_context: Optional[str],
        language: Optional[str]
    ) -> float:
        """Estimate task complexity"""
        complexity = 0.5  # Base complexity
        
        # Description length factor
        if len(description) > 200:
            complexity += 0.1
        
        # Code context factor
        if code_context:
            lines = len(code_context.split('\n'))
            if lines > 100:
                complexity += 0.2
            elif lines > 50:
                complexity += 0.1
        
        # Language complexity factor
        complex_languages = ["rust", "c++", "haskell", "scala"]
        if language and language.lower() in complex_languages:
            complexity += 0.1
        
        return min(complexity, 1.0)
    
    def _get_required_capabilities(self, intent: TaskIntent) -> list:
        """Get required agent capabilities for intent"""
        capability_map = {
            TaskIntent.REFACTOR: ["code_analysis", "refactoring", "optimization"],
            TaskIntent.EXPLAIN: ["code_analysis", "documentation"],
            TaskIntent.GENERATE: ["code_generation", "syntax_checking"],
            TaskIntent.DEBUG: ["bug_detection", "code_analysis"],
            TaskIntent.OPTIMIZE: ["performance_analysis", "optimization"],
            TaskIntent.TEST: ["test_generation", "code_analysis"],
            TaskIntent.DOCUMENT: ["documentation", "code_analysis"],
            TaskIntent.REVIEW: ["code_analysis", "security_analysis"],
            TaskIntent.UNKNOWN: ["code_analysis"]
        }
        
        return capability_map.get(intent, ["code_analysis"])
    
    def _suggest_agent_priority(
        self,
        intent: TaskIntent,
        complexity: float
    ) -> list:
        """Suggest agent priority order"""
        # Simple tasks
        if complexity < 0.3:
            return ["Reasoner", "Aggregator"]
        
        # Complex tasks requiring verification
        if intent in [TaskIntent.GENERATE, TaskIntent.REFACTOR, TaskIntent.DEBUG]:
            return ["Planner", "Reasoner", "Verifier", "Aggregator"]
        
        # Standard tasks
        return ["Reasoner", "Verifier", "Aggregator"]
