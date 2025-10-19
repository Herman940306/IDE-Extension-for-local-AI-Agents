"""
AST Checker for syntax validation
Project Creator: Herman Swanepoel
"""

import ast
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ASTChecker:
    """
    Syntax validation using AST parsing.

    Provides fast, deterministic syntax checking for Python code
    and can be extended for other languages using Tree-sitter.
    """

    def __init__(self):
        """Initialize AST checker"""
        self.supported_languages = ["python"]
        logger.info("ASTChecker initialized")

    def validate(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Check if code is syntactically valid.

        Args:
            code: Source code to validate
            language: Programming language

        Returns:
            Dict containing validation result and details
        """
        if language.lower() not in self.supported_languages:
            logger.warning(f"Language {language} not supported, skipping validation")
            return {
                "valid": True,  # Assume valid for unsupported languages
                "language": language,
                "message": f"Validation not supported for {language}",
            }

        if language.lower() == "python":
            return self._validate_python(code)

        return {"valid": False, "message": "Unknown language"}

    def _validate_python(self, code: str) -> Dict[str, Any]:
        """
        Validate Python code using AST.

        Args:
            code: Python source code

        Returns:
            Validation result dict
        """
        try:
            # Parse code into AST
            tree = ast.parse(code)

            # Calculate AST metrics
            depth = self._calculate_ast_depth(tree)
            node_count = self._count_nodes(tree)

            # Check for common issues
            issues = self._check_common_issues(tree)

            result = {
                "valid": True,
                "language": "python",
                "ast_depth": depth,
                "node_count": node_count,
                "issues": issues,
                "message": "Code is syntactically valid",
            }

            logger.debug(f"Python validation passed: depth={depth}, nodes={node_count}")
            return result

        except SyntaxError as e:
            logger.warning(f"Python syntax error: {e}")
            return {
                "valid": False,
                "language": "python",
                "error_type": "SyntaxError",
                "message": str(e),
                "line": e.lineno,
                "offset": e.offset,
                "text": e.text,
            }
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            return {
                "valid": False,
                "language": "python",
                "error_type": type(e).__name__,
                "message": str(e),
            }

    def _calculate_ast_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """
        Calculate maximum depth of AST.

        Args:
            node: AST node
            current_depth: Current depth in tree

        Returns:
            Maximum depth
        """
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            child_depth = self._calculate_ast_depth(child, current_depth + 1)
            max_depth = max(max_depth, child_depth)

        return max_depth

    def _count_nodes(self, node: ast.AST) -> int:
        """
        Count total nodes in AST.

        Args:
            node: AST node

        Returns:
            Total node count
        """
        count = 1
        for child in ast.iter_child_nodes(node):
            count += self._count_nodes(child)
        return count

    def _check_common_issues(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """
        Check for common code issues.

        Args:
            tree: AST tree

        Returns:
            List of issue dicts
        """
        issues = []

        # Check for bare except clauses
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(
                        {
                            "type": "bare_except",
                            "severity": "warning",
                            "message": "Bare except clause found (catches all exceptions)",  # noqa: E501
                            "line": node.lineno,
                        }
                    )

            # Check for unused variables (simple heuristic)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.startswith("_") and target.id != "_":
                            issues.append(
                                {
                                    "type": "unused_variable",
                                    "severity": "info",
                                    "message": f"Variable '{target.id}' appears unused",
                                    "line": node.lineno,
                                }
                            )

        return issues

    def get_ast_info(
        self, code: str, language: str = "python"
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed AST information.

        Args:
            code: Source code
            language: Programming language

        Returns:
            Dict with AST information or None if invalid
        """
        validation = self.validate(code, language)

        if not validation["valid"]:
            return None

        if language.lower() == "python":
            try:
                tree = ast.parse(code)

                # Extract function and class definitions (top-level only)
                functions = []
                classes = []

                # Only iterate top-level nodes, not nested ones
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef):
                        functions.append(
                            {
                                "name": node.name,
                                "line": node.lineno,
                                "args": [arg.arg for arg in node.args.args],
                                "decorators": [
                                    d.id if isinstance(d, ast.Name) else str(d)
                                    for d in node.decorator_list
                                ],
                            }
                        )
                    elif isinstance(node, ast.ClassDef):
                        classes.append(
                            {
                                "name": node.name,
                                "line": node.lineno,
                                "bases": [
                                    b.id if isinstance(b, ast.Name) else str(b)
                                    for b in node.bases
                                ],
                                "methods": [
                                    m.name
                                    for m in node.body
                                    if isinstance(m, ast.FunctionDef)
                                ],
                            }
                        )

                return {
                    "functions": functions,
                    "classes": classes,
                    "ast_depth": validation.get("ast_depth"),
                    "node_count": validation.get("node_count"),
                }
            except Exception as e:
                logger.error(f"Failed to extract AST info: {e}")
                return None

        return None
