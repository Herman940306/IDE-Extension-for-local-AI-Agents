"""
AI-powered code smell detection using semantic embeddings
Project Creator: Herman Swanepoel
"""

import ast
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

from src.models import CodeSmell, Priority
from src.services.embeddings_service import EmbeddingsService

logger = logging.getLogger(__name__)


class CodeSmellDetector:
    """
    Detects code smells using semantic analysis and embeddings
    Goes beyond traditional static analysis
    """

    def __init__(self, embeddings_service: EmbeddingsService):
        """
        Initialize code smell detector

        Args:
            embeddings_service: Embeddings service for semantic analysis
        """
        self.embeddings_service = embeddings_service
        self.similarity_threshold = 0.85  # 85% similarity = potential duplication
        self.god_class_threshold = 10  # Methods/responsibilities

    async def detect_smells(self, file_path: str, content: str, language: str) -> List[CodeSmell]:
        """
        Detect code smells in a file

        Args:
            file_path: Path to file
            content: File content
            language: Programming language

        Returns:
            List of detected code smells
        """
        smells = []

        try:
            # Run different detection strategies
            if language == "python":
                smells.extend(await self._detect_python_smells(file_path, content))
            elif language in ["javascript", "typescript"]:
                smells.extend(await self._detect_js_smells(file_path, content))

            # Semantic duplication detection (language-agnostic)
            dup_smells = await self._detect_semantic_duplication(file_path, content)
            smells.extend(dup_smells)

        except Exception as e:
            logger.error(f"Failed to detect smells in {file_path}: {e}")

        return smells

    async def _detect_python_smells(self, file_path: str, content: str) -> List[CodeSmell]:
        """Detect Python-specific code smells"""
        smells = []

        try:
            tree = ast.parse(content)

            # Detect God classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                    if len(methods) > self.god_class_threshold:
                        smells.append(
                            CodeSmell(
                                id=f"god_class_{node.name}",
                                file_path=file_path,
                                smell_type="god_class",
                                severity=Priority.HIGH,
                                description=f"Class '{node.name}' has {len(methods)} methods (threshold: {self.god_class_threshold})",  # noqa: E501
                                line_start=node.lineno,
                                line_end=node.end_lineno or node.lineno,
                                suggestion="Consider splitting into smaller, focused classes using Single Responsibility Principle",  # noqa: E501
                                confidence=0.9,
                            )
                        )

            # Detect long functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_lines = (node.end_lineno or node.lineno) - node.lineno
                    if func_lines > 50:
                        smells.append(
                            CodeSmell(
                                id=f"long_function_{node.name}",
                                file_path=file_path,
                                smell_type="long_function",
                                severity=Priority.MEDIUM,
                                description=f"Function '{node.name}' is {func_lines} lines long",  # noqa: E501
                                line_start=node.lineno,
                                line_end=node.end_lineno or node.lineno,
                                suggestion="Consider breaking into smaller functions",
                                confidence=0.85,
                            )
                        )

            # Detect too many parameters
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    param_count = len(node.args.args)
                    if param_count > 5:
                        smells.append(
                            CodeSmell(
                                id=f"too_many_params_{node.name}",
                                file_path=file_path,
                                smell_type="too_many_parameters",
                                severity=Priority.MEDIUM,
                                description=f"Function '{node.name}' has {param_count} parameters",  # noqa: E501
                                line_start=node.lineno,
                                line_end=node.lineno,
                                suggestion="Consider using a configuration object or builder pattern",  # noqa: E501
                                confidence=0.8,
                            )
                        )

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to detect Python smells: {e}")

        return smells

    async def _detect_js_smells(self, file_path: str, content: str) -> List[CodeSmell]:
        """Detect JavaScript/TypeScript-specific code smells"""
        smells = []

        try:
            # Detect callback hell (nested callbacks)
            callback_pattern = r"function\s*\([^)]*\)\s*\{[^}]*function\s*\([^)]*\)\s*\{[^}]*function\s*\([^)]*\)\s*\{"  # noqa: E501
            if re.search(callback_pattern, content):
                smells.append(
                    CodeSmell(
                        id="callback_hell",
                        file_path=file_path,
                        smell_type="callback_hell",
                        severity=Priority.HIGH,
                        description="Deeply nested callbacks detected (callback hell)",
                        line_start=1,
                        line_end=1,
                        suggestion="Refactor to use Promises or async/await",
                        confidence=0.9,
                    )
                )

            # Detect var usage (should use let/const)
            var_pattern = r"\bvar\s+\w+"
            var_matches = list(re.finditer(var_pattern, content))
            if len(var_matches) > 3:
                smells.append(
                    CodeSmell(
                        id="var_usage",
                        file_path=file_path,
                        smell_type="outdated_syntax",
                        severity=Priority.LOW,
                        description=f"Found {len(var_matches)} uses of 'var' keyword",
                        line_start=1,
                        line_end=1,
                        suggestion="Use 'let' or 'const' instead of 'var'",
                        confidence=0.95,
                    )
                )

        except Exception as e:
            logger.error(f"Failed to detect JS smells: {e}")

        return smells

    async def _detect_semantic_duplication(self, file_path: str, content: str) -> List[CodeSmell]:
        """
        Detect semantic code duplication using embeddings
        Finds similar code even with different variable names
        """
        smells = []

        try:
            # Extract functions/methods from content
            functions = self._extract_functions(content)

            if len(functions) < 2:
                return smells

            # Generate embeddings for each function
            function_embeddings = []
            for func_name, func_code, line_start, line_end in functions:
                embedding = await self.embeddings_service.embed_code(func_code)
                function_embeddings.append((func_name, embedding, line_start, line_end))

            # Compare embeddings to find similar functions
            for i in range(len(function_embeddings)):
                for j in range(i + 1, len(function_embeddings)):
                    name1, emb1, line1_start, line1_end = function_embeddings[i]
                    name2, emb2, line2_start, line2_end = function_embeddings[j]

                    similarity = self._cosine_similarity(emb1, emb2)

                    if similarity > self.similarity_threshold:
                        smells.append(
                            CodeSmell(
                                id=f"duplication_{name1}_{name2}",
                                file_path=file_path,
                                smell_type="semantic_duplication",
                                severity=Priority.MEDIUM,
                                description=f"Functions '{name1}' and '{name2}' are {int(similarity * 100)}% similar",  # noqa: E501
                                line_start=line1_start,
                                line_end=line2_end,
                                suggestion="Consider extracting common logic into a shared function",  # noqa: E501
                                confidence=similarity,
                            )
                        )

        except Exception as e:
            logger.error(f"Failed to detect semantic duplication: {e}")

        return smells

    def _extract_functions(self, content: str) -> List[Tuple[str, str, int, int]]:
        """
        Extract functions from code

        Returns:
            List of (function_name, function_code, line_start, line_end)
        """
        functions = []

        try:
            # Try Python AST
            tree = ast.parse(content)
            lines = content.split("\n")

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_lines = lines[node.lineno - 1 : node.end_lineno]
                    func_code = "\n".join(func_lines)
                    functions.append(
                        (
                            node.name,
                            func_code,
                            node.lineno,
                            node.end_lineno or node.lineno,
                        )
                    )
        except Exception as e:
            logger.debug(f"AST parsing failed, using regex fallback: {e}")
            # Fallback: simple regex-based extraction
            func_pattern = r"(function\s+(\w+)|(\w+)\s*=\s*function|(\w+)\s*=\s*\([^)]*\)\s*=>)"
            matches = re.finditer(func_pattern, content)
            for match in matches:
                func_name = match.group(2) or match.group(3) or match.group(4) or "anonymous"
                # Extract function body (simplified)
                start_pos = match.start()
                line_num = content[:start_pos].count("\n") + 1
                functions.append((func_name, match.group(0), line_num, line_num))

        return functions

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np

            v1 = np.array(vec1)
            v2 = np.array(vec2)
            return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
        except Exception as e:
            logger.debug(f"Numpy cosine similarity failed, using fallback: {e}")
            # Fallback without numpy
            dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            return dot_product / (magnitude1 * magnitude2)

    async def analyze_codebase(
        self, workspace_path: str, file_extensions: List[str] = None
    ) -> Dict[str, List[CodeSmell]]:
        """
        Analyze entire codebase for code smells

        Args:
            workspace_path: Path to workspace
            file_extensions: File extensions to analyze

        Returns:
            Dictionary mapping file paths to detected smells
        """
        if file_extensions is None:
            file_extensions = [".py", ".ts", ".js"]
        results = {}
        workspace = Path(workspace_path)

        try:
            # Find all code files
            code_files = []
            for ext in file_extensions:
                code_files.extend(workspace.rglob(f"*{ext}"))

            logger.info(f"Analyzing {len(code_files)} files for code smells")

            # Analyze each file
            for file_path in code_files:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    language = self._detect_language(file_path)

                    smells = await self.detect_smells(
                        str(file_path.relative_to(workspace)), content, language
                    )

                    if smells:
                        results[str(file_path.relative_to(workspace))] = smells

                except Exception as e:
                    logger.warning(f"Failed to analyze {file_path}: {e}")

            logger.info(f"✓ Code smell analysis complete: {len(results)} files with issues")

        except Exception as e:
            logger.error(f"Failed to analyze codebase: {e}")

        return results

    def _detect_language(self, file_path: Path) -> str:
        """Detect language from file extension"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
        }
        return ext_map.get(file_path.suffix, "unknown")
