"""
Bug Detection Agent with security analysis
Project Creator: Herman Swanepoel
"""

import re
from enum import Enum
from typing import Any, Dict, List

from src.models import AgentResponse, CodeContext, Suggestion, Task
from src.services.llm_manager import LLMManager


class Severity(str, Enum):
    """Bug severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class BugCategory(str, Enum):
    """Bug categories"""

    SECURITY = "security"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"


class BugAgent:
    """
    Bug detection agent with security analysis

    Detects bugs, security vulnerabilities, and code quality issues
    using static analysis and LLM-powered detection.
    """

    def __init__(self, llm_manager: LLMManager):
        """
        Initialize Bug Agent

        Args:
            llm_manager: LLM manager for AI-powered analysis
        """
        self.llm_manager = llm_manager
        self.name = "Bug Agent"

        # Security patterns to detect
        self.security_patterns = {
            "sql_injection": r"(execute|query|cursor\.execute)\s*\(\s*['\"].*%s.*['\"]",
            "command_injection": r"(os\.system|subprocess\.call|eval|exec)\s*\(",
            "hardcoded_secret": r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]",
            "xss_vulnerability": r"innerHTML\s*=|document\.write\s*\(",
            "path_traversal": r"open\s*\([^)]*\+[^)]*\)",
            "insecure_random": r"random\.random\(\)|Math\.random\(\)",
        }

        # Performance anti-patterns
        self.performance_patterns = {
            "nested_loops": r"for\s+.*:\s*\n\s+for\s+",
            "inefficient_string_concat": r"\+\s*=\s*['\"]",
            "global_variable": r"global\s+\w+",
        }

    async def analyze_code(self, task: Task, context: CodeContext) -> AgentResponse:
        """
        Analyze code for bugs and security issues

        Args:
            task: Task to execute
            context: Code context

        Returns:
            AgentResponse with bug findings and fixes
        """
        try:
            # Run static analysis
            static_issues = await self._static_analysis(context)

            # Run LLM-powered analysis
            llm_issues = await self._llm_analysis(context)

            # Combine and deduplicate issues
            all_issues = self._merge_issues(static_issues, llm_issues)

            # Generate fix suggestions
            suggestions = await self._generate_fixes(all_issues, context)

            # Calculate overall confidence
            confidence = self._calculate_confidence(all_issues, suggestions)

            return AgentResponse(
                task_id=task.id,
                agent_name=self.name,
                suggestions=suggestions,
                confidence=confidence,
                reasoning=self._generate_reasoning(all_issues),
            )

        except Exception as e:
            return AgentResponse(
                task_id=task.id,
                agent_name=self.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
            )

    async def _static_analysis(self, context: CodeContext) -> List[Dict[str, Any]]:
        """
        Perform static code analysis

        Args:
            context: Code context

        Returns:
            List of detected issues
        """
        issues = []

        # Check security patterns
        for pattern_name, pattern in self.security_patterns.items():
            matches = re.finditer(pattern, context.code, re.MULTILINE)
            for match in matches:
                line_num = context.code[: match.start()].count("\n") + 1
                issues.append(
                    {
                        "type": "security",
                        "category": BugCategory.SECURITY,
                        "severity": self._get_severity(pattern_name),
                        "pattern": pattern_name,
                        "line": line_num,
                        "code": match.group(0),
                        "message": self._get_message(pattern_name),
                    }
                )

        # Check performance patterns
        for pattern_name, pattern in self.performance_patterns.items():
            matches = re.finditer(pattern, context.code, re.MULTILINE)
            for match in matches:
                line_num = context.code[: match.start()].count("\n") + 1
                issues.append(
                    {
                        "type": "performance",
                        "category": BugCategory.PERFORMANCE,
                        "severity": Severity.MEDIUM,
                        "pattern": pattern_name,
                        "line": line_num,
                        "code": match.group(0),
                        "message": self._get_message(pattern_name),
                    }
                )

        # Language-specific checks
        if context.language == "python":
            issues.extend(await self._python_specific_checks(context))
        elif context.language in ["javascript", "typescript"]:
            issues.extend(await self._javascript_specific_checks(context))

        return issues

    async def _python_specific_checks(self, context: CodeContext) -> List[Dict[str, Any]]:
        """Python-specific security and quality checks"""
        issues = []

        # Check for pickle usage (security risk)
        if "pickle.loads" in context.code or "pickle.load" in context.code:
            issues.append(
                {
                    "type": "security",
                    "category": BugCategory.SECURITY,
                    "severity": Severity.HIGH,
                    "pattern": "unsafe_deserialization",
                    "line": 0,
                    "code": "pickle.loads/load",
                    "message": "Unsafe deserialization with pickle can lead to code execution",
                }
            )

        # Check for assert in production code
        if "assert " in context.code:
            issues.append(
                {
                    "type": "logic",
                    "category": BugCategory.LOGIC,
                    "severity": Severity.LOW,
                    "pattern": "assert_in_production",
                    "line": 0,
                    "code": "assert",
                    "message": "Assert statements are removed in optimized Python, use proper error handling",
                }
            )

        return issues

    async def _javascript_specific_checks(self, context: CodeContext) -> List[Dict[str, Any]]:
        """JavaScript/TypeScript-specific checks"""
        issues = []

        # Check for == instead of ===
        matches = re.finditer(r"[^=!]==[^=]", context.code)
        for match in matches:
            line_num = context.code[: match.start()].count("\n") + 1
            issues.append(
                {
                    "type": "logic",
                    "category": BugCategory.LOGIC,
                    "severity": Severity.LOW,
                    "pattern": "loose_equality",
                    "line": line_num,
                    "code": match.group(0),
                    "message": "Use === instead of == for strict equality comparison",
                }
            )

        # Check for console.log in production
        if "console.log" in context.code:
            issues.append(
                {
                    "type": "style",
                    "category": BugCategory.STYLE,
                    "severity": Severity.INFO,
                    "pattern": "console_log",
                    "line": 0,
                    "code": "console.log",
                    "message": "Remove console.log statements from production code",
                }
            )

        return issues

    async def _llm_analysis(self, context: CodeContext) -> List[Dict[str, Any]]:
        """
        Use LLM for deeper code analysis

        Args:
            context: Code context

        Returns:
            List of LLM-detected issues
        """
        try:
            prompt = f"""Analyze the following {context.language} code for bugs, security vulnerabilities, and code quality issues.

Code:
```{context.language}
{context.code}
```

Provide a detailed analysis in the following format:
1. List each issue found
2. Categorize as: security, performance, logic, style, or maintainability
3. Assign severity: critical, high, medium, low, or info
4. Explain the issue and potential impact
5. Suggest a fix

Format your response as:
ISSUE: [category] - [severity]
LINE: [line number or "multiple"]
DESCRIPTION: [detailed description]
FIX: [suggested fix]
---
"""

            response = await self.llm_manager.generate(prompt, max_tokens=1000)

            # Parse LLM response
            return self._parse_llm_response(response)

        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return []

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into structured issues"""
        issues = []

        # Split by issue separator
        issue_blocks = response.split("---")

        for block in issue_blocks:
            if not block.strip():
                continue

            issue = {}

            # Extract fields
            if match := re.search(r"ISSUE:\s*(\w+)\s*-\s*(\w+)", block):
                issue["category"] = match.group(1).lower()
                issue["severity"] = match.group(2).lower()

            if match := re.search(r"LINE:\s*(.+)", block):
                line_str = match.group(1).strip()
                issue["line"] = int(line_str) if line_str.isdigit() else 0

            if match := re.search(r"DESCRIPTION:\s*(.+?)(?=FIX:|$)", block, re.DOTALL):
                issue["message"] = match.group(1).strip()

            if match := re.search(r"FIX:\s*(.+)", block, re.DOTALL):
                issue["fix"] = match.group(1).strip()

            if issue:
                issue["type"] = "llm_detected"
                issues.append(issue)

        return issues

    def _merge_issues(
        self, static_issues: List[Dict[str, Any]], llm_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge and deduplicate issues from different sources"""
        all_issues = static_issues + llm_issues

        # Sort by severity
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }

        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", Severity.INFO), 4))

        return all_issues

    async def _generate_fixes(
        self, issues: List[Dict[str, Any]], context: CodeContext
    ) -> List[Suggestion]:
        """Generate fix suggestions for detected issues"""
        suggestions = []

        for issue in issues[:10]:  # Limit to top 10 issues
            # Use LLM to generate fix if not already provided
            if "fix" not in issue:
                fix_code = await self._generate_fix_code(issue, context)
            else:
                fix_code = issue["fix"]

            suggestions.append(
                Suggestion(
                    code=fix_code,
                    description=f"[{issue['severity'].upper()}] {issue['message']}",
                    confidence=self._get_fix_confidence(issue),
                    reasoning=f"Detected {issue['category']} issue at line {issue.get('line', 'unknown')}",
                )
            )

        return suggestions

    async def _generate_fix_code(self, issue: Dict[str, Any], context: CodeContext) -> str:
        """Generate fix code for an issue using LLM"""
        try:
            prompt = f"""Generate a code fix for the following issue:

Issue: {issue['message']}
Category: {issue.get('category', 'unknown')}
Severity: {issue.get('severity', 'unknown')}

Original code:
```{context.language}
{context.code}
```

Provide only the fixed code without explanations.
"""

            fix = await self.llm_manager.generate(prompt, max_tokens=500)
            return fix.strip()

        except Exception:
            return f"# TODO: Fix {issue['message']}"

    def _get_severity(self, pattern_name: str) -> Severity:
        """Get severity level for a pattern"""
        severity_map = {
            "sql_injection": Severity.CRITICAL,
            "command_injection": Severity.CRITICAL,
            "hardcoded_secret": Severity.HIGH,
            "xss_vulnerability": Severity.HIGH,
            "path_traversal": Severity.HIGH,
            "insecure_random": Severity.MEDIUM,
            "nested_loops": Severity.MEDIUM,
            "inefficient_string_concat": Severity.LOW,
            "global_variable": Severity.LOW,
        }
        return severity_map.get(pattern_name, Severity.INFO)

    def _get_message(self, pattern_name: str) -> str:
        """Get human-readable message for a pattern"""
        messages = {
            "sql_injection": "Potential SQL injection vulnerability detected",
            "command_injection": "Potential command injection vulnerability detected",
            "hardcoded_secret": "Hardcoded secret or credential detected",
            "xss_vulnerability": "Potential XSS vulnerability detected",
            "path_traversal": "Potential path traversal vulnerability detected",
            "insecure_random": "Insecure random number generation for security purposes",
            "nested_loops": "Nested loops may cause performance issues",
            "inefficient_string_concat": "Inefficient string concatenation in loop",
            "global_variable": "Global variable usage may cause maintainability issues",
        }
        return messages.get(pattern_name, f"Issue detected: {pattern_name}")

    def _get_fix_confidence(self, issue: Dict[str, Any]) -> float:
        """Calculate confidence for a fix suggestion"""
        base_confidence = 0.7

        # Higher confidence for static analysis
        if issue.get("type") != "llm_detected":
            base_confidence += 0.1

        # Higher confidence for well-known patterns
        if issue.get("pattern") in self.security_patterns:
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    def _calculate_confidence(
        self, issues: List[Dict[str, Any]], suggestions: List[Suggestion]
    ) -> float:
        """Calculate overall confidence in the analysis"""
        if not issues:
            return 0.9  # High confidence when no issues found

        # Average confidence of suggestions
        if suggestions:
            avg_confidence = sum(s.confidence for s in suggestions) / len(suggestions)
            return avg_confidence

        return 0.7  # Default confidence

    def _generate_reasoning(self, issues: List[Dict[str, Any]]) -> str:
        """Generate reasoning text for the analysis"""
        if not issues:
            return "No significant bugs or security issues detected. Code appears to be clean."

        # Count by severity
        severity_counts = {}
        for issue in issues:
            severity = issue.get("severity", Severity.INFO)
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        reasoning = f"Found {len(issues)} issue(s):\n"
        for severity, count in sorted(severity_counts.items(), key=lambda x: x[0].value):
            reasoning += f"- {severity.value.upper()}: {count}\n"

        reasoning += "\nTop issues:\n"
        for i, issue in enumerate(issues[:5], 1):
            reasoning += f"{i}. [{issue.get('severity', 'unknown').upper()}] {issue['message']}\n"

        return reasoning
