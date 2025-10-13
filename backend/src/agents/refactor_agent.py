"""
Refactor Agent - Specialized agent for code refactoring suggestions

This agent analyzes code for refactoring opportunities using:
- AST-based static analysis
- Code smell detection
- Design pattern recognition
- LLM-powered suggestions

Project Creator: Herman Swanepoel
"""

import logging
import uuid
import ast
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from adapters.base_adapter import AgentAdapter, AgentConfig, Capability
from models.task import Task
from models.context import CodeContext
from models.response import AgentResponse, Suggestion, ConfidenceLevel
from services.llm_manager import LLMManager
from services.code_smell_detector import CodeSmellDetector
from services.memory_service import MemoryService, Message, MessageType

logger = logging.getLogger(__name__)


class RefactoringPattern:
    """Represents a refactoring pattern"""
    
    def __init__(
        self,
        name: str,
        description: str,
        detector: callable,
        suggestion_template: str,
        confidence: float = 0.8
    ):
        self.name = name
        self.description = description
        self.detector = detector
        self.suggestion_template = suggestion_template
        self.confidence = confidence


class RefactorAgent(AgentAdapter):
    """
    Specialized agent for code refactoring suggestions.
    
    Capabilities:
    - Code smell detection
    - Design pattern suggestions
    - Performance optimization
    - Code simplification
    - Best practices enforcement
    
    Architecture:
    - AST-based analysis for fast, deterministic detection
    - LLM-powered suggestions for complex refactorings
    - Memory integration for context-aware suggestions
    
    Usage:
        config = AgentConfig(
            name="Refactor Agent",
            description="Code refactoring specialist",
            capabilities=[Capability.REFACTORING]
        )
        agent = RefactorAgent(config, llm_manager, code_smell_detector)
        await agent.initialize()
        
        response = await agent.execute_task(task, context)
    """
    
    def __init__(
        self,
        config: AgentConfig,
        llm_manager: LLMManager,
        code_smell_detector: CodeSmellDetector,
        memory_service: Optional[MemoryService] = None
    ):
        """
        Initialize Refactor Agent
        
        Args:
            config: Agent configuration
            llm_manager: LLM manager for AI-powered suggestions
            code_smell_detector: Code smell detection service
            memory_service: Optional memory service for context
        """
        super().__init__(config)
        self.llm_manager = llm_manager
        self.code_smell_detector = code_smell_detector
        self.memory_service = memory_service
        self.refactoring_patterns: List[RefactoringPattern] = []
        
        logger.info(f"RefactorAgent initialized: {config.name}")
    
    async def initialize(self) -> None:
        """Initialize the agent and load refactoring patterns"""
        if self.is_initialized:
            return
        
        try:
            # Load refactoring patterns
            self._load_refactoring_patterns()
            
            # Verify LLM is available
            llm_healthy = await self.llm_manager.health_check()
            if not llm_healthy:
                logger.warning("LLM health check failed, agent will use AST-only analysis")
            
            self.is_initialized = True
            logger.info("✓ RefactorAgent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RefactorAgent: {e}")
            raise
    
    def _load_refactoring_patterns(self) -> None:
        """Load common refactoring patterns"""
        self.refactoring_patterns = [
            RefactoringPattern(
                name="Extract Method",
                description="Long method that should be split into smaller methods",
                detector=self._detect_long_method,
                suggestion_template="Consider extracting this logic into a separate method",
                confidence=0.85
            ),
            RefactoringPattern(
                name="Replace Magic Numbers",
                description="Magic numbers that should be named constants",
                detector=self._detect_magic_numbers,
                suggestion_template="Replace magic number with a named constant",
                confidence=0.9
            ),
            RefactoringPattern(
                name="Simplify Conditional",
                description="Complex conditional that can be simplified",
                detector=self._detect_complex_conditional,
                suggestion_template="Simplify this conditional expression",
                confidence=0.75
            ),
            RefactoringPattern(
                name="Remove Dead Code",
                description="Unreachable or unused code",
                detector=self._detect_dead_code,
                suggestion_template="This code appears to be unused and can be removed",
                confidence=0.8
            ),
        ]
        
        logger.info(f"Loaded {len(self.refactoring_patterns)} refactoring patterns")
    
    async def execute_task(self, task: Task, context: CodeContext) -> AgentResponse:
        """
        Execute refactoring analysis task
        
        Args:
            task: Task to execute
            context: Code context
            
        Returns:
            AgentResponse with refactoring suggestions
        """
        if not self.is_initialized:
            await self.initialize()
        
        logger.info(f"Executing refactoring task: {task.id}")
        
        try:
            # Store task in memory if available
            if self.memory_service:
                await self._store_task_in_memory(task, context)
            
            # Analyze code
            suggestions = await self._analyze_code(task.content, context)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(suggestions)
            
            # Generate reasoning
            reasoning = self._generate_reasoning(suggestions, context)
            
            # Create response
            response = AgentResponse(
                agent_id="refactor_agent",
                agent_name=self.config.name,
                suggestions=suggestions,
                confidence=confidence,
                reasoning=reasoning,
                metadata={
                    "task_id": task.id,
                    "patterns_detected": len(suggestions),
                    "language": context.language,
                    "analysis_type": "ast_and_llm"
                }
            )
            
            # Store response in memory
            if self.memory_service:
                await self._store_response_in_memory(task, response)
            
            logger.info(f"✓ Refactoring analysis complete: {len(suggestions)} suggestions")
            return response
            
        except Exception as e:
            logger.error(f"Failed to execute refactoring task: {e}")
            # Return empty response on error
            return AgentResponse(
                agent_id="refactor_agent",
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    async def _analyze_code(
        self,
        code: str,
        context: CodeContext
    ) -> List[Suggestion]:
        """
        Analyze code and generate refactoring suggestions
        
        Args:
            code: Code to analyze
            context: Code context
            
        Returns:
            List of refactoring suggestions
        """
        suggestions = []
        
        # 1. AST-based pattern detection (fast, deterministic)
        ast_suggestions = await self._detect_patterns_ast(code, context)
        suggestions.extend(ast_suggestions)
        
        # 2. Code smell detection (semantic analysis)
        smell_suggestions = await self._detect_code_smells(code, context)
        suggestions.extend(smell_suggestions)
        
        # 3. LLM-powered suggestions (deep analysis)
        if len(suggestions) > 0:
            # Only use LLM if we found issues
            llm_suggestions = await self._generate_llm_suggestions(code, context, suggestions)
            suggestions.extend(llm_suggestions)
        
        # Remove duplicates and rank by confidence
        suggestions = self._deduplicate_suggestions(suggestions)
        suggestions = sorted(suggestions, key=lambda s: self._confidence_to_float(s.confidence), reverse=True)
        
        return suggestions[:10]  # Return top 10 suggestions
    
    async def _detect_patterns_ast(
        self,
        code: str,
        context: CodeContext
    ) -> List[Suggestion]:
        """Detect refactoring patterns using AST analysis"""
        suggestions = []
        
        if context.language != 'python':
            # AST analysis currently only for Python
            return suggestions
        
        try:
            tree = ast.parse(code)
            
            # Apply each refactoring pattern
            for pattern in self.refactoring_patterns:
                pattern_suggestions = pattern.detector(tree, code, context)
                suggestions.extend(pattern_suggestions)
                
        except SyntaxError as e:
            logger.warning(f"Syntax error in code, skipping AST analysis: {e}")
        except Exception as e:
            logger.error(f"AST analysis failed: {e}")
        
        return suggestions
    
    def _detect_long_method(
        self,
        tree: ast.AST,
        code: str,
        context: CodeContext
    ) -> List[Suggestion]:
        """Detect long methods that should be refactored"""
        suggestions = []
        lines = code.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = (node.end_lineno or node.lineno) - node.lineno
                
                if func_lines > 30:  # Threshold: 30 lines
                    # Extract function code
                    func_code = '\n'.join(lines[node.lineno - 1:node.end_lineno])
                    
                    suggestions.append(Suggestion(
                        id=f"long_method_{node.name}_{uuid.uuid4().hex[:8]}",
                        code=func_code,
                        description=f"Function '{node.name}' is {func_lines} lines long. Consider breaking it into smaller, focused functions.",
                        confidence=ConfidenceLevel.HIGH if func_lines > 50 else ConfidenceLevel.MEDIUM,
                        diff=None,
                        applicable_range={
                            "start": {"line": node.lineno, "character": 0},
                            "end": {"line": node.end_lineno or node.lineno, "character": 0}
                        }
                    ))
        
        return suggestions
    
    def _detect_magic_numbers(
        self,
        tree: ast.AST,
        code: str,
        context: CodeContext
    ) -> List[Suggestion]:
        """Detect magic numbers that should be constants"""
        suggestions = []
        magic_numbers = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                # Skip common values (0, 1, -1, 2)
                if node.value in [0, 1, -1, 2, 0.0, 1.0]:
                    continue
                
                # Track occurrences
                value = node.value
                if value not in magic_numbers:
                    magic_numbers[value] = []
                magic_numbers[value].append(node.lineno)
        
        # Suggest constants for numbers used multiple times
        for value, lines in magic_numbers.items():
            if len(lines) >= 2:
                suggestions.append(Suggestion(
                    id=f"magic_number_{value}_{uuid.uuid4().hex[:8]}",
                    code=f"# Define constant\nMAGIC_VALUE = {value}",
                    description=f"Magic number {value} appears {len(lines)} times. Consider defining it as a named constant.",
                    confidence=ConfidenceLevel.HIGH,
                    diff=None,
                    applicable_range={
                        "start": {"line": lines[0], "character": 0},
                        "end": {"line": lines[-1], "character": 0}
                    }
                ))
        
        return suggestions
    
    def _detect_complex_conditional(
        self,
        tree: ast.AST,
        code: str,
        context: CodeContext
    ) -> List[Suggestion]:
        """Detect complex conditionals that can be simplified"""
        suggestions = []
        lines = code.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Count boolean operators in condition
                bool_ops = sum(1 for _ in ast.walk(node.test) if isinstance(_, (ast.And, ast.Or)))
                
                if bool_ops >= 3:  # 3+ boolean operators
                    condition_line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                    
                    suggestions.append(Suggestion(
                        id=f"complex_conditional_{node.lineno}_{uuid.uuid4().hex[:8]}",
                        code=condition_line.strip(),
                        description=f"Complex conditional with {bool_ops} boolean operators. Consider extracting into a well-named boolean variable or method.",
                        confidence=ConfidenceLevel.MEDIUM,
                        diff=None,
                        applicable_range={
                            "start": {"line": node.lineno, "character": 0},
                            "end": {"line": node.lineno, "character": len(condition_line)}
                        }
                    ))
        
        return suggestions
    
    def _detect_dead_code(
        self,
        tree: ast.AST,
        code: str,
        context: CodeContext
    ) -> List[Suggestion]:
        """Detect potentially dead/unused code"""
        suggestions = []
        
        # Detect unreachable code after return
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for i, stmt in enumerate(node.body):
                    if isinstance(stmt, ast.Return):
                        # Check if there's code after return
                        if i < len(node.body) - 1:
                            next_stmt = node.body[i + 1]
                            suggestions.append(Suggestion(
                                id=f"dead_code_{node.name}_{uuid.uuid4().hex[:8]}",
                                code="# Unreachable code detected",
                                description=f"Code after return statement in '{node.name}' is unreachable and can be removed.",
                                confidence=ConfidenceLevel.HIGH,
                                diff=None,
                                applicable_range={
                                    "start": {"line": next_stmt.lineno, "character": 0},
                                    "end": {"line": next_stmt.end_lineno or next_stmt.lineno, "character": 0}
                                }
                            ))
                            break
        
        return suggestions
    
    async def _detect_code_smells(
        self,
        code: str,
        context: CodeContext
    ) -> List[Suggestion]:
        """Detect code smells using semantic analysis"""
        suggestions = []
        
        try:
            # Use code smell detector
            smells = await self.code_smell_detector.detect_smells(
                context.file_path,
                code,
                context.language
            )
            
            # Convert code smells to suggestions
            for smell in smells:
                suggestions.append(Suggestion(
                    id=f"smell_{smell.id}",
                    code=smell.suggestion,
                    description=f"{smell.smell_type.upper()}: {smell.description}",
                    confidence=self._float_to_confidence(smell.confidence),
                    diff=None,
                    applicable_range={
                        "start": {"line": smell.line_start, "character": 0},
                        "end": {"line": smell.line_end, "character": 0}
                    }
                ))
                
        except Exception as e:
            logger.error(f"Code smell detection failed: {e}")
        
        return suggestions
    
    async def _generate_llm_suggestions(
        self,
        code: str,
        context: CodeContext,
        existing_suggestions: List[Suggestion]
    ) -> List[Suggestion]:
        """Generate additional suggestions using LLM"""
        suggestions = []
        
        try:
            # Build prompt with context
            prompt = self._build_refactoring_prompt(code, context, existing_suggestions)
            
            # Generate LLM response
            response = await self.llm_manager.generate(
                prompt=prompt,
                system_prompt="You are an expert code refactoring assistant. Provide concise, actionable refactoring suggestions.",
                temperature=0.3,  # Lower temperature for more focused suggestions
                max_tokens=500
            )
            
            # Parse LLM response into suggestions
            llm_suggestions = self._parse_llm_response(response, context)
            suggestions.extend(llm_suggestions)
            
        except Exception as e:
            logger.warning(f"LLM suggestion generation failed: {e}")
        
        return suggestions
    
    def _build_refactoring_prompt(
        self,
        code: str,
        context: CodeContext,
        existing_suggestions: List[Suggestion]
    ) -> str:
        """Build prompt for LLM refactoring suggestions"""
        prompt = f"""Analyze this {context.language} code and suggest refactorings:

```{context.language}
{code}
```

File: {context.file_path}

Already detected issues:
"""
        for sugg in existing_suggestions[:3]:  # Include top 3 existing suggestions
            prompt += f"- {sugg.description}\n"
        
        prompt += """
Provide 1-2 additional high-value refactoring suggestions focusing on:
1. Design patterns that could improve the code
2. Performance optimizations
3. Readability improvements

Format each suggestion as:
SUGGESTION: [brief description]
REASON: [why this improves the code]
"""
        
        return prompt
    
    def _parse_llm_response(
        self,
        response: str,
        context: CodeContext
    ) -> List[Suggestion]:
        """Parse LLM response into structured suggestions"""
        suggestions = []
        
        # Simple parsing: look for SUGGESTION: and REASON: patterns
        pattern = r'SUGGESTION:\s*(.+?)\s*REASON:\s*(.+?)(?=SUGGESTION:|$)'
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
        
        for description, reason in matches:
            suggestions.append(Suggestion(
                id=f"llm_{uuid.uuid4().hex[:8]}",
                code="",  # LLM doesn't provide code, just suggestions
                description=description.strip(),
                confidence=ConfidenceLevel.MEDIUM,  # LLM suggestions are medium confidence
                diff=None,
                applicable_range=None
            ))
        
        return suggestions
    
    def _deduplicate_suggestions(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """Remove duplicate suggestions"""
        seen = set()
        unique = []
        
        for sugg in suggestions:
            # Use description as key for deduplication
            key = sugg.description.lower()
            if key not in seen:
                seen.add(key)
                unique.append(sugg)
        
        return unique
    
    def _calculate_confidence(self, suggestions: List[Suggestion]) -> float:
        """Calculate overall confidence score"""
        if not suggestions:
            return 0.0
        
        total = sum(self._confidence_to_float(s.confidence) for s in suggestions)
        return min(total / len(suggestions), 1.0)
    
    def _confidence_to_float(self, confidence: ConfidenceLevel) -> float:
        """Convert confidence level to float"""
        mapping = {
            ConfidenceLevel.HIGH: 0.9,
            ConfidenceLevel.MEDIUM: 0.7,
            ConfidenceLevel.LOW: 0.5
        }
        return mapping.get(confidence, 0.5)
    
    def _float_to_confidence(self, value: float) -> ConfidenceLevel:
        """Convert float to confidence level"""
        if value >= 0.8:
            return ConfidenceLevel.HIGH
        elif value >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _generate_reasoning(
        self,
        suggestions: List[Suggestion],
        context: CodeContext
    ) -> str:
        """Generate reasoning explanation"""
        if not suggestions:
            return "No refactoring opportunities detected. Code appears to follow best practices."
        
        reasoning = f"Analyzed {context.language} code and found {len(suggestions)} refactoring opportunities:\n"
        
        # Summarize by confidence level
        high_conf = sum(1 for s in suggestions if s.confidence == ConfidenceLevel.HIGH)
        medium_conf = sum(1 for s in suggestions if s.confidence == ConfidenceLevel.MEDIUM)
        low_conf = sum(1 for s in suggestions if s.confidence == ConfidenceLevel.LOW)
        
        if high_conf > 0:
            reasoning += f"- {high_conf} high-confidence suggestions (recommended to apply)\n"
        if medium_conf > 0:
            reasoning += f"- {medium_conf} medium-confidence suggestions (review before applying)\n"
        if low_conf > 0:
            reasoning += f"- {low_conf} low-confidence suggestions (optional improvements)\n"
        
        reasoning += "\nFocus on high-confidence suggestions first for maximum impact."
        
        return reasoning
    
    async def _store_task_in_memory(self, task: Task, context: CodeContext) -> None:
        """Store task in memory service"""
        if not self.memory_service:
            return
        
        try:
            session_id = context.workspace_path or "default"
            message = Message(
                id=f"task_{task.id}",
                session_id=session_id,
                type=MessageType.USER_QUERY,
                content=f"Refactor request: {task.content[:100]}...",
                metadata={
                    "task_id": task.id,
                    "task_type": task.type.value,
                    "file_path": context.file_path,
                    "language": context.language
                },
                timestamp=task.timestamp
            )
            await self.memory_service.store_message(session_id, message)
        except Exception as e:
            logger.warning(f"Failed to store task in memory: {e}")
    
    async def _store_response_in_memory(self, task: Task, response: AgentResponse) -> None:
        """Store response in memory service"""
        if not self.memory_service:
            return
        
        try:
            session_id = task.context.get("workspace_path", "default")
            message = Message(
                id=f"response_{task.id}",
                session_id=session_id,
                type=MessageType.AGENT_RESPONSE,
                content=f"Found {len(response.suggestions)} refactoring suggestions",
                metadata={
                    "task_id": task.id,
                    "agent_id": response.agent_id,
                    "confidence": response.confidence,
                    "suggestion_count": len(response.suggestions)
                },
                timestamp=task.timestamp
            )
            await self.memory_service.store_message(session_id, message)
        except Exception as e:
            logger.warning(f"Failed to store response in memory: {e}")
    
    async def get_capabilities(self) -> List[Capability]:
        """Get agent capabilities"""
        return self.config.capabilities
    
    async def health_check(self) -> bool:
        """Check if agent is healthy"""
        if not self.is_initialized:
            return False
        
        # Check LLM availability (optional, agent can work without it)
        llm_healthy = await self.llm_manager.health_check()
        if not llm_healthy:
            logger.warning("LLM unavailable, agent will use AST-only mode")
        
        return True  # Agent can function without LLM

