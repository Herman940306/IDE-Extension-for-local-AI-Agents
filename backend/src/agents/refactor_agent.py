"""
Refactor Agent - Specialized agent for code refactoring suggestions

This agent analyzes code for refactoring opportunities using:
- AST-based static analysis
- Code smell detection
- Design pattern recognition
- LLM-powered suggestions

Project Creator: Herman Swanepoel
"""

import ast
import asyncio
import hashlib
import logging
import re
import textwrap
import uuid
from typing import Callable, Dict, List, Optional

from src.adapters.base_adapter import AgentAdapter, AgentConfig, Capability
from src.models.context import CodeContext
from src.models.response import AgentResponse, ConfidenceLevel, Suggestion
from src.models.task import Task
from src.services.code_smell_detector import CodeSmellDetector
from src.services.llm_manager import LLMError, LLMManager
from src.services.memory_service import MemoryService, Message, MessageType

logger = logging.getLogger(__name__)


class RefactoringPattern:
    """Represents a refactoring pattern"""

    def __init__(
        self,
        name: str,
        description: str,
        detector: Callable[[ast.AST, str, CodeContext], List[Suggestion]],
        suggestion_template: str,
        confidence: float = 0.8,
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
    - Parallel analysis for performance
    - AST caching for repeated analysis

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

    # Configuration constants
    LONG_METHOD_THRESHOLD = 30
    VERY_LONG_METHOD_THRESHOLD = 50
    MAGIC_NUMBER_MIN_OCCURRENCES = 2
    COMPLEX_CONDITIONAL_THRESHOLD = 3
    MAX_AST_NODES = 10000
    MAX_SUGGESTIONS = 10

    def __init__(
        self,
        config: AgentConfig,
        llm_manager: LLMManager,
        code_smell_detector: CodeSmellDetector,
        memory_service: Optional[MemoryService] = None,
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
        self._ast_cache: Dict[str, ast.AST] = {}

        logger.info(
            "RefactorAgent initialized",
            extra={
                "agent_name": config.name,
                "capabilities": [c.value for c in config.capabilities],
            },
        )

    async def initialize(self) -> None:
        """
        Initialize the agent and load refactoring patterns

        Raises:
            RuntimeError: If initialization fails
        """
        if self.is_initialized:
            return

        try:
            # Load refactoring patterns
            self._load_refactoring_patterns()

            # Verify LLM is available
            llm_healthy = await self.llm_manager.health_check()
            if not llm_healthy:
                logger.warning(
                    "LLM health check failed, agent will use AST-only analysis"
                )

            self.is_initialized = True
            logger.info(
                "✓ RefactorAgent initialized successfully",
                extra={"pattern_count": len(self.refactoring_patterns)},
            )

        except Exception as e:
            logger.error(f"Failed to initialize RefactorAgent: {e}", exc_info=True)
            raise RuntimeError(f"RefactorAgent initialization failed: {e}") from e

    def _load_refactoring_patterns(self) -> None:
        """Load common refactoring patterns"""
        self.refactoring_patterns = [
            RefactoringPattern(
                name="Extract Method",
                description="Long method that should be split into smaller methods",
                detector=self._detect_long_method,
                suggestion_template="Consider extracting this logic into a separate method",  # noqa: E501
                confidence=0.85,
            ),
            RefactoringPattern(
                name="Replace Magic Numbers",
                description="Magic numbers that should be named constants",
                detector=self._detect_magic_numbers,
                suggestion_template="Replace magic number with a named constant",
                confidence=0.9,
            ),
            RefactoringPattern(
                name="Simplify Conditional",
                description="Complex conditional that can be simplified",
                detector=self._detect_complex_conditional,
                suggestion_template="Simplify this conditional expression",
                confidence=0.75,
            ),
            RefactoringPattern(
                name="Remove Dead Code",
                description="Unreachable or unused code",
                detector=self._detect_dead_code,
                suggestion_template="This code appears to be unused and can be removed",
                confidence=0.8,
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

        Raises:
            ValueError: If task or context is invalid
        """
        if not self.is_initialized:
            await self.initialize()

        source_code = task.content or ""
        normalized_code = textwrap.dedent(source_code).rstrip()

        logger.info(
            "Executing refactoring task",
            extra={
                "task_id": task.id,
                "file_path": context.file_path,
                "language": context.language,
                "code_length": len(normalized_code),
            },
        )

        try:
            # Store task in memory if available
            if self.memory_service:
                await self._store_task_in_memory(task, context)

            # Analyze code
            suggestions = await self._analyze_code(normalized_code, context)

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
                    "analysis_type": "ast_and_llm",
                },
            )

            # Store response in memory
            if self.memory_service:
                await self._store_response_in_memory(task, response)

            logger.info(
                "✓ Refactoring analysis complete",
                extra={
                    "task_id": task.id,
                    "suggestion_count": len(suggestions),
                    "confidence": confidence,
                },
            )
            return response

        except SyntaxError as e:
            logger.error(f"Code analysis failed - syntax error: {e}", exc_info=True)
            return AgentResponse(
                agent_id="refactor_agent",
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Syntax error in code: {str(e)}",
                metadata={"error": "syntax_error", "details": str(e)},
            )
        except ValueError as e:
            logger.error(f"Code analysis failed - invalid input: {e}", exc_info=True)
            return AgentResponse(
                agent_id="refactor_agent",
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Invalid input: {str(e)}",
                metadata={"error": "value_error", "details": str(e)},
            )
        except LLMError as e:
            logger.warning(f"LLM unavailable, using AST-only analysis: {e}")
            # Continue with AST-only analysis
            suggestions = await self._analyze_code_ast_only(normalized_code, context)
            return AgentResponse(
                agent_id="refactor_agent",
                agent_name=self.config.name,
                suggestions=suggestions,
                confidence=self._calculate_confidence(suggestions),
                reasoning=self._generate_reasoning(suggestions, context),
                metadata={"analysis_type": "ast_only", "llm_error": str(e)},
            )
        except Exception as e:
            logger.critical(f"Unexpected error in refactoring task: {e}", exc_info=True)
            return AgentResponse(
                agent_id="refactor_agent",
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                metadata={"error": "unexpected_error", "details": str(e)},
            )

    async def _analyze_code(self, code: str, context: CodeContext) -> List[Suggestion]:
        """
        Analyze code and generate refactoring suggestions using parallel execution

        Args:
            code: Source code to analyze
            context: Code context including file path and language

        Returns:
            List of refactoring suggestions sorted by confidence

        Raises:
            SyntaxError: If code cannot be parsed
            ValueError: If context is invalid
        """
        # Run analyses in parallel for performance
        results = await asyncio.gather(
            self._detect_patterns_ast(code, context),
            self._detect_code_smells(code, context),
            return_exceptions=True,
        )

        suggestions: List[Suggestion] = []

        ast_suggestions = results[0]
        if isinstance(ast_suggestions, Exception):
            logger.warning(
                "AST analysis failed",
                extra={"error": str(ast_suggestions), "file_path": context.file_path},
            )
        else:
            suggestions.extend(ast_suggestions)

        smell_suggestions = results[1]
        if isinstance(smell_suggestions, Exception):
            logger.warning(
                "Code smell detection failed",
                extra={"error": str(smell_suggestions), "file_path": context.file_path},
            )
        else:
            suggestions.extend(smell_suggestions)

        # 3. LLM-powered suggestions (deep analysis) - only if issues found
        if len(suggestions) > 0:
            try:
                llm_suggestions = await self._generate_llm_suggestions(
                    code, context, suggestions
                )
                suggestions.extend(llm_suggestions)
            except LLMError as e:
                logger.warning(f"LLM suggestions skipped: {e}")
            except Exception as e:
                logger.error(f"LLM suggestion generation failed: {e}")

        # Remove duplicates and rank by confidence
        suggestions = self._deduplicate_suggestions(suggestions)
        suggestions = sorted(
            suggestions,
            key=lambda s: self._confidence_to_float(s.confidence),
            reverse=True,
        )

        return suggestions[: self.MAX_SUGGESTIONS]

    async def _analyze_code_ast_only(
        self, code: str, context: CodeContext
    ) -> List[Suggestion]:
        """
        Analyze code using only AST (fallback when LLM unavailable)

        Args:
            code: Source code to analyze
            context: Code context

        Returns:
            List of refactoring suggestions
        """
        suggestions = []

        # AST-based pattern detection
        ast_suggestions = await self._detect_patterns_ast(code, context)
        suggestions.extend(ast_suggestions)

        smell_suggestions = await self._detect_code_smells(code, context)
        suggestions.extend(smell_suggestions)

        # Remove duplicates and rank
        suggestions = self._deduplicate_suggestions(suggestions)
        suggestions = sorted(
            suggestions,
            key=lambda s: self._confidence_to_float(s.confidence),
            reverse=True,
        )

        return suggestions[: self.MAX_SUGGESTIONS]

    def _parse_code_cached(self, code: str) -> ast.AST:
        """
        Parse code with caching for performance

        Args:
            code: Source code to parse

        Returns:
            Parsed AST tree

        Raises:
            SyntaxError: If code has syntax errors
        """
        # Generate cache key (MD5 used for non-security caching only)
        code_hash = hashlib.md5(code.encode(), usedforsecurity=False).hexdigest()

        # Check cache
        if code_hash in self._ast_cache:
            logger.debug(f"AST cache hit for hash {code_hash[:8]}")
            return self._ast_cache[code_hash]

        # Parse and cache
        tree = ast.parse(code)

        # Limit cache size
        if len(self._ast_cache) > 128:
            # Remove oldest entry (simple FIFO)
            self._ast_cache.pop(next(iter(self._ast_cache)))

        self._ast_cache[code_hash] = tree
        logger.debug(f"AST cached for hash {code_hash[:8]}")

        return tree

    async def _detect_patterns_ast(
        self, code: str, context: CodeContext
    ) -> List[Suggestion]:
        """
        Detect refactoring patterns using AST analysis with node count limits

        Args:
            code: Source code to analyze
            context: Code context

        Returns:
            List of suggestions from pattern detection

        Raises:
            SyntaxError: If code has syntax errors
        """
        suggestions = []

        if context.language != "python":
            # AST analysis currently only for Python
            return suggestions

        try:
            # Parse with caching
            tree = self._parse_code_cached(code)

            # Check AST size to prevent memory issues
            node_count = sum(1 for _ in ast.walk(tree))

            if node_count > self.MAX_AST_NODES:
                logger.warning(
                    f"File too large ({node_count} nodes), skipping AST analysis",
                    extra={"file_path": context.file_path, "node_count": node_count},
                )
                return suggestions

            # Apply each refactoring pattern
            for pattern in self.refactoring_patterns:
                try:
                    pattern_suggestions = pattern.detector(tree, code, context)
                    suggestions.extend(pattern_suggestions)
                except Exception as e:
                    logger.error(
                        f"Pattern detector '{pattern.name}' failed: {e}", exc_info=True
                    )

        except SyntaxError as e:
            logger.warning(f"Syntax error in code, skipping AST analysis: {e}")
            raise
        except Exception as e:
            logger.error(f"AST analysis failed: {e}", exc_info=True)
            raise

        return suggestions

    def _detect_long_method(
        self, tree: ast.AST, code: str, context: CodeContext
    ) -> List[Suggestion]:
        """Detect long methods that should be refactored"""
        suggestions = []
        lines = code.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = (node.end_lineno or node.lineno) - node.lineno

                if func_lines > self.LONG_METHOD_THRESHOLD:
                    # Extract function code
                    func_code = "\n".join(lines[node.lineno - 1 : node.end_lineno])

                    suggestions.append(
                        Suggestion(
                            id=f"long_method_{node.name}_{uuid.uuid4().hex[:8]}",
                            code=func_code,
                            description=f"Function '{node.name}' is {func_lines} lines long. Consider breaking it into smaller, focused functions.",  # noqa: E501
                            confidence=(
                                ConfidenceLevel.HIGH
                                if func_lines > self.VERY_LONG_METHOD_THRESHOLD
                                else ConfidenceLevel.MEDIUM
                            ),
                            diff=None,
                            applicable_range={
                                "start": {"line": node.lineno, "character": 0},
                                "end": {
                                    "line": node.end_lineno or node.lineno,
                                    "character": 0,
                                },
                            },
                        )
                    )

        return suggestions

    def _detect_magic_numbers(
        self, tree: ast.AST, code: str, context: CodeContext
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

        # Suggest constants for numbers used multiple times or medium-risk single occurrences  # noqa: E501
        for value, lines in magic_numbers.items():
            occurrences = len(lines)
            min_occurrences = self.MAGIC_NUMBER_MIN_OCCURRENCES

            if isinstance(value, float) or abs(value) >= 10:
                min_occurrences = 1

            if occurrences >= min_occurrences:
                confidence = (
                    ConfidenceLevel.HIGH
                    if occurrences >= self.MAGIC_NUMBER_MIN_OCCURRENCES
                    else ConfidenceLevel.MEDIUM
                )

                suggestions.append(
                    Suggestion(
                        id=f"magic_number_{value}_{uuid.uuid4().hex[:8]}",
                        code=f"# Define constant\nMAGIC_VALUE = {value}",
                        description=(
                            f"Magic number {value} appears {occurrences} time(s). "
                            "Consider defining it as a named constant."
                        ),
                        confidence=confidence,
                        diff=None,
                        applicable_range={
                            "start": {"line": lines[0], "character": 0},
                            "end": {"line": lines[-1], "character": 0},
                        },
                    )
                )

        return suggestions

    def _detect_complex_conditional(
        self, tree: ast.AST, code: str, context: CodeContext
    ) -> List[Suggestion]:
        """Detect complex conditionals that can be simplified"""
        suggestions = []
        lines = code.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Count boolean operations and negations in condition
                bool_ops = 0
                for sub_node in ast.walk(node.test):
                    if isinstance(sub_node, ast.BoolOp):
                        bool_ops += max(len(getattr(sub_node, "values", [])) - 1, 1)
                    if isinstance(sub_node, ast.UnaryOp) and isinstance(
                        sub_node.op, ast.Not
                    ):
                        bool_ops += 1

                if bool_ops >= self.COMPLEX_CONDITIONAL_THRESHOLD:
                    condition_line = (
                        lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                    )

                    suggestions.append(
                        Suggestion(
                            id=(
                                f"complex_conditional_{node.lineno}_"
                                f"{uuid.uuid4().hex[:8]}"
                            ),
                            code=condition_line.strip(),
                            description=(
                                f"Complex conditional with {bool_ops} boolean "
                                "operators. Consider extracting into a well-named "
                                "boolean variable or method."
                            ),
                            confidence=ConfidenceLevel.MEDIUM,
                            diff=None,
                            applicable_range={
                                "start": {"line": node.lineno, "character": 0},
                                "end": {
                                    "line": node.lineno,
                                    "character": len(condition_line),
                                },
                            },
                        )
                    )

        return suggestions

    def _detect_dead_code(
        self, tree: ast.AST, code: str, context: CodeContext
    ) -> List[Suggestion]:
        """Detect potentially dead/unused code"""
        suggestions = []

        def _statement_range(node: ast.AST) -> Dict[str, Dict[str, int]]:
            start_line = getattr(node, "lineno", 0)
            end_line = getattr(node, "end_lineno", start_line)
            return {
                "start": {"line": start_line, "character": 0},
                "end": {"line": end_line, "character": 0},
            }

        def _is_terminal(stmt: ast.stmt) -> bool:
            return isinstance(stmt, (ast.Return, ast.Raise, ast.Continue, ast.Break))

        def _collect_blocks(stmt: ast.stmt) -> List[List[ast.stmt]]:
            blocks: List[List[ast.stmt]] = []
            for attr in ("body", "orelse", "finalbody"):
                block = getattr(stmt, attr, None)
                if block:
                    blocks.append(block)
            for handler in getattr(stmt, "handlers", []):
                if handler.body:
                    blocks.append(handler.body)
                if handler.orelse:
                    blocks.append(handler.orelse)
            return blocks

        def _mark_unreachable(block: List[ast.stmt], scope: str) -> None:
            reached_terminal = False
            for stmt in block:
                if reached_terminal:
                    suggestions.append(
                        Suggestion(
                            id=(
                                f"dead_code_{scope}_{stmt.lineno}_"
                                f"{uuid.uuid4().hex[:8]}"
                            ),
                            code="# Unreachable code detected",
                            description=(
                                f"Code at line {stmt.lineno} in '{scope}' is "
                                "unreachable because a previous control-flow "
                                "statement exits this block."
                            ),
                            confidence=ConfidenceLevel.HIGH,
                            diff=None,
                            applicable_range=_statement_range(stmt),
                        )
                    )
                    continue

                if _is_terminal(stmt):
                    reached_terminal = True
                else:
                    for child_block in _collect_blocks(stmt):
                        _mark_unreachable(child_block, scope)

        def _body_has_terminal(block: List[ast.stmt]) -> bool:
            return any(_is_terminal(stmt) for stmt in block)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _mark_unreachable(list(node.body), node.name)

                # Guard clause detection: if branch returns and subsequent statements exist  # noqa: E501
                for index, stmt in enumerate(node.body):
                    if (
                        isinstance(stmt, ast.If)
                        and not stmt.orelse
                        and _body_has_terminal(stmt.body)
                        and index < len(node.body) - 1
                    ):
                        follow_stmt = node.body[index + 1]
                        suggestions.append(
                            Suggestion(
                                id=(
                                    f"guard_unreachable_{follow_stmt.lineno}_"
                                    f"{uuid.uuid4().hex[:8]}"
                                ),
                                code="# Potential unreachable code after guard clause",
                                description=(
                                    "Guard clause returns from the function; "
                                    "subsequent statements are unreachable when "
                                    "the guard condition is met. Consider using "
                                    "an else block or reorganizing the flow."
                                ),
                                confidence=ConfidenceLevel.MEDIUM,
                                diff=None,
                                applicable_range=_statement_range(follow_stmt),
                            )
                        )

        return suggestions

    async def _detect_code_smells(
        self, code: str, context: CodeContext
    ) -> List[Suggestion]:
        """Detect code smells using semantic analysis"""
        suggestions = []

        try:
            # Use code smell detector
            smells = await self.code_smell_detector.detect_smells(
                context.file_path, code, context.language
            )

            # Convert code smells to suggestions
            for smell in smells:
                suggestions.append(
                    Suggestion(
                        id=f"smell_{smell.id}",
                        code=smell.suggestion,
                        description=f"{smell.smell_type.upper()}: {smell.description}",
                        confidence=self._float_to_confidence(smell.confidence),
                        diff=None,
                        applicable_range={
                            "start": {"line": smell.line_start, "character": 0},
                            "end": {"line": smell.line_end, "character": 0},
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Code smell detection failed: {e}")

        return suggestions

    async def _generate_llm_suggestions(
        self, code: str, context: CodeContext, existing_suggestions: List[Suggestion]
    ) -> List[Suggestion]:
        """Generate additional suggestions using LLM"""
        suggestions = []

        try:
            # Build prompt with context
            prompt = self._build_refactoring_prompt(code, context, existing_suggestions)

            # Generate LLM response
            response = await self.llm_manager.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an expert code refactoring assistant. "
                    "Provide concise, actionable refactoring suggestions."
                ),
                temperature=0.3,  # Lower temperature for more focused suggestions
                max_tokens=500,
            )

            # Parse LLM response into suggestions
            llm_suggestions = self._parse_llm_response(response, context)
            suggestions.extend(llm_suggestions)

        except Exception as e:
            logger.warning(f"LLM suggestion generation failed: {e}")

        return suggestions

    def _build_refactoring_prompt(
        self, code: str, context: CodeContext, existing_suggestions: List[Suggestion]
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
        self, response: str, context: CodeContext
    ) -> List[Suggestion]:
        """Parse LLM response into structured suggestions"""
        suggestions = []

        # Simple parsing: look for SUGGESTION: and REASON: patterns
        pattern = r"SUGGESTION:\s*(.+?)\s*REASON:\s*(.+?)(?=SUGGESTION:|$)"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

        for description, _reason in matches:
            suggestions.append(
                Suggestion(
                    id=f"llm_{uuid.uuid4().hex[:8]}",
                    code="",  # LLM doesn't provide code, just suggestions
                    description=description.strip(),
                    confidence=ConfidenceLevel.MEDIUM,  # LLM suggestions are medium confidence  # noqa: E501
                    diff=None,
                    applicable_range=None,
                )
            )

        return suggestions

    def _deduplicate_suggestions(
        self, suggestions: List[Suggestion]
    ) -> List[Suggestion]:
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
            ConfidenceLevel.LOW: 0.5,
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
        self, suggestions: List[Suggestion], context: CodeContext
    ) -> str:
        """Generate reasoning explanation"""
        if not suggestions:
            return "No refactoring opportunities detected. Code appears to follow best practices."  # noqa: E501

        reasoning = (
            f"Analyzed {context.language} code and found "
            f"{len(suggestions)} refactoring opportunities:\n"
        )

        # Summarize by confidence level
        high_conf = sum(1 for s in suggestions if s.confidence == ConfidenceLevel.HIGH)
        medium_conf = sum(
            1 for s in suggestions if s.confidence == ConfidenceLevel.MEDIUM
        )
        low_conf = sum(1 for s in suggestions if s.confidence == ConfidenceLevel.LOW)

        if high_conf > 0:
            reasoning += (
                f"- {high_conf} high-confidence suggestions (recommended to apply)\n"
            )
        if medium_conf > 0:
            reasoning += f"- {medium_conf} medium-confidence suggestions (review before applying)\n"  # noqa: E501
        if low_conf > 0:
            reasoning += (
                f"- {low_conf} low-confidence suggestions (optional improvements)\n"
            )

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
                    "language": context.language,
                },
                timestamp=task.timestamp,
            )
            await self.memory_service.store_message(session_id, message)
        except Exception as e:
            logger.warning(f"Failed to store task in memory: {e}")

    async def _store_response_in_memory(
        self, task: Task, response: AgentResponse
    ) -> None:
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
                    "suggestion_count": len(response.suggestions),
                },
                timestamp=task.timestamp,
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
