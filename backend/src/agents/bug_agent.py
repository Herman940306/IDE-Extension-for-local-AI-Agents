"""
Bug Agent with security analysis and vulnerability detection
Project Creator: Herman Swanepoel
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import re

from models import Task, AgentResponse, Suggestion, TaskType
from adapters.base_adapter import AgentAdapter
from services.llm_manager import LLMManager
from services.code_smell_detector import CodeSmellDetector

logger = logging.getLogger(__name__)


class BugAgent(AgentAdapter):
    """
    Specialized agent for bug detection, security analysis, and code quality
    """
    
    def __init__(self, llm_manager: LLMManager):
        """
        Initialize Bug Agent
        
        Args:
            llm_manager: LLM manager instance
        """
        super().__init__(
            name="bug_agent",
            capabilities=["bug_detection", "security_analysis", "code_quality", "linting"]
        )
        self.llm_manager = llm_manager
        self.code_smell_detector = CodeSmellDetector()
        
        # Security patterns
        self.security_patterns = self._initialize_security_patterns()
        
        logger.info("✓ BugAgent initialized")
    
    def _initialize_security_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize security vulnerability patterns"""
        return {
            "python": [
                {
                    "pattern": r"eval\s*\(",
                    "severity": "critical",
                    "message": "Use of eval() is dangerous - arbitrary code execution",
                    "cwe": "CWE-95"
                },
                {
                    "pattern": r"exec\s*\(",
                    "severity": "critical",
                    "message": "Use of exec() is dangerous - arbitrary code execution",
                    "cwe": "CWE-95"
                },
                {
                    "pattern": r"pickle\.loads?\s*\(",
                    "severity": "high",
                    "message": "Pickle deserialization can execute arbitrary code",
                    "cwe": "CWE-502"
                },
                {
                    "pattern": r"os\.system\s*\(",
                    "severity": "high",
                    "message": "os.system() vulnerable to command injection",
                    "cwe": "CWE-78"
                },
                {
                    "pattern": r"subprocess\.(call|run|Popen).*shell\s*=\s*True",
                    "severity": "high",
                    "message": "Shell=True in subprocess is vulnerable to injection",
                    "cwe": "CWE-78"
                },
                {
                    "pattern": r"password\s*=\s*['\"].*['\"]",
                    "severity": "critical",
                    "message": "Hardcoded password detected",
                    "cwe": "CWE-259"
                },
                {
                    "pattern": r"api[_-]?key\s*=\s*['\"].*['\"]",
                    "severity": "critical",
                    "message": "Hardcoded API key detected",
                    "cwe": "CWE-798"
                },
                {
                    "pattern": r"secret\s*=\s*['\"].*['\"]",
                    "severity": "critical",
                    "message": "Hardcoded secret detected",
                    "cwe": "CWE-798"
                }
            ],
            "javascript": [
                {
                    "pattern": r"eval\s*\(",
                    "severity": "critical",
                    "message": "Use of eval() is dangerous - arbitrary code execution",
                    "cwe": "CWE-95"
                },
                {
                    "pattern": r"innerHTML\s*=",
                    "severity": "medium",
                    "message": "innerHTML can lead to XSS vulnerabilities",
                    "cwe": "CWE-79"
                },
                {
                    "pattern": r"document\.write\s*\(",
                    "severity": "medium",
                    "message": "document.write() can lead to XSS vulnerabilities",
                    "cwe": "CWE-79"
                },
                {
                    "pattern": r"dangerouslySetInnerHTML",
                    "severity": "high",
                    "message": "dangerouslySetInnerHTML can lead to XSS",
                    "cwe": "CWE-79"
                },
                {
                    "pattern": r"password\s*[:=]\s*['\"].*['\"]",
                    "severity": "critical",
                    "message": "Hardcoded password detected",
                    "cwe": "CWE-259"
                },
                {
                    "pattern": r"apiKey\s*[:=]\s*['\"].*['\"]",
                    "severity": "critical",
                    "message": "Hardcoded API key detected",
                    "cwe": "CWE-798"
                }
            ],
            "typescript": [
                {
                    "pattern": r"eval\s*\(",
                    "severity": "critical",
                    "message": "Use of eval() is dangerous - arbitrary code execution",
                    "cwe": "CWE-95"
                },
                {
                    "pattern": r"dangerouslySetInnerHTML",
                    "severity": "high",
                    "message": "dangerouslySetInnerHTML can lead to XSS",
                    "cwe": "CWE-79"
                },
                {
                    "pattern": r"password\s*[:=]\s*['\"].*['\"]",
                    "severity": "critical",
                    "message": "Hardcoded password detected",
                    "cwe": "CWE-259"
                },
                {
                    "pattern": r"any\s+as\s+",
                    "severity": "low",
                    "message": "Type assertion bypasses type safety",
                    "cwe": "CWE-704"
                }
            ]
        }
    
    async def execute_task(self, task: Task) -> AgentResponse:
        """
        Execute bug detection and security analysis task
        
        Args:
            task: Task to execute
            
        Returns:
            AgentResponse with bug fixes and security recommendations
        """
        try:
            logger.info(f"BugAgent executing task: {task.id}")
            
            # Get code context
            code = task.code_context.get("code", "") if task.code_context else ""
            language = task.code_context.get("language", "unknown") if task.code_context else "unknown"
            
            if not code:
                return self._create_empty_response(task)
            
            # Perform analysis
            issues = await self._analyze_code(code, language)
            
            # Generate suggestions
            suggestions = await self._generate_suggestions(code, language, issues)
            
            # Create response
            return AgentResponse(
                task_id=task.id,
                agent_name=self.name,
                suggestions=suggestions,
                metadata={
                    "issues_found": len(issues),
                    "critical_issues": sum(1 for i in issues if i["severity"] == "critical"),
                    "high_issues": sum(1 for i in issues if i["severity"] == "high"),
                    "medium_issues": sum(1 for i in issues if i["severity"] == "medium"),
                    "low_issues": sum(1 for i in issues if i["severity"] == "low"),
                    "analysis_type": "security_and_quality"
                }
            )
            
        except Exception as e:
            logger.error(f"BugAgent task execution failed: {e}")
            return self._create_error_response(task, str(e))
    
    async def _analyze_code(self, code: str, language: str) -> List[Dict[str, Any]]:
        """
        Analyze code for bugs and security issues
        
        Args:
            code: Code to analyze
            language: Programming language
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Security pattern matching
        security_issues = self._detect_security_issues(code, language)
        issues.extend(security_issues)
        
        # Code smell detection
        code_smells = await self.code_smell_detector.detect(code, language)
        issues.extend(code_smells)
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        issues.sort(key=lambda x: severity_order.get(x["severity"], 4))
        
        return issues
    
    def _detect_security_issues(self, code: str, language: str) -> List[Dict[str, Any]]:
        """
        Detect security vulnerabilities using pattern matching
        
        Args:
            code: Code to analyze
            language: Programming language
            
        Returns:
            List of security issues
        """
        issues = []
        patterns = self.security_patterns.get(language, [])
        
        for pattern_info in patterns:
            pattern = pattern_info["pattern"]
            matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                # Find line number
                line_num = code[:match.start()].count('\n') + 1
                
                issues.append({
                    "type": "security",
                    "severity": pattern_info["severity"],
                    "message": pattern_info["message"],
                    "cwe": pattern_info.get("cwe", ""),
                    "line": line_num,
                    "code_snippet": match.group(0),
                    "category": "security_vulnerability"
                })
        
        return issues
    
    async def _generate_suggestions(
        self,
        code: str,
        language: str,
        issues: List[Dict[str, Any]]
    ) -> List[Suggestion]:
        """
        Generate fix suggestions for detected issues
        
        Args:
            code: Original code
            language: Programming language
            issues: List of detected issues
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Group issues by severity
        critical_issues = [i for i in issues if i["severity"] == "critical"]
        high_issues = [i for i in issues if i["severity"] == "high"]
        
        # Generate fixes for critical issues first
        for issue in critical_issues[:3]:  # Limit to top 3
            suggestion = await self._generate_fix_for_issue(code, language, issue)
            if suggestion:
                suggestions.append(suggestion)
        
        # Generate fixes for high severity issues
        for issue in high_issues[:2]:  # Limit to top 2
            suggestion = await self._generate_fix_for_issue(code, language, issue)
            if suggestion:
                suggestions.append(suggestion)
        
        # If no critical/high issues, provide general improvements
        if not suggestions and issues:
            suggestion = await self._generate_general_improvements(code, language, issues)
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions
    
    async def _generate_fix_for_issue(
        self,
        code: str,
        language: str,
        issue: Dict[str, Any]
    ) -> Optional[Suggestion]:
        """
        Generate a fix suggestion for a specific issue
        
        Args:
            code: Original code
            language: Programming language
            issue: Issue to fix
            
        Returns:
            Suggestion or None
        """
        try:
            # Create prompt for LLM
            prompt = f"""Fix this {issue['severity']} severity {language} code issue:

Issue: {issue['message']}
{f"CWE: {issue['cwe']}" if issue.get('cwe') else ""}
Line: {issue.get('line', 'unknown')}

Original code:
```{language}
{code}
```

Provide a fixed version of the code that resolves this issue while maintaining functionality.
Only return the fixed code, no explanations."""

            # Get fix from LLM
            fixed_code = await self.llm_manager.generate(prompt)
            
            # Calculate confidence based on severity
            confidence = 0.9 if issue["severity"] == "critical" else 0.8
            
            return Suggestion(
                code=fixed_code.strip(),
                description=f"Fix {issue['severity']} issue: {issue['message']}",
                confidence=confidence,
                reasoning=f"Addresses {issue.get('cwe', 'security issue')} by {issue['message'].lower()}"
            )
            
        except Exception as e:
            logger.error(f"Failed to generate fix for issue: {e}")
            return None
    
    async def _generate_general_improvements(
        self,
        code: str,
        language: str,
        issues: List[Dict[str, Any]]
    ) -> Optional[Suggestion]:
        """
        Generate general code quality improvements
        
        Args:
            code: Original code
            language: Programming language
            issues: List of all issues
            
        Returns:
            Suggestion or None
        """
        try:
            issue_summary = "\n".join([
                f"- {i['severity'].upper()}: {i['message']}"
                for i in issues[:5]
            ])
            
            prompt = f"""Improve this {language} code to address these quality issues:

{issue_summary}

Original code:
```{language}
{code}
```

Provide an improved version that addresses these issues.
Only return the improved code, no explanations."""

            improved_code = await self.llm_manager.generate(prompt)
            
            return Suggestion(
                code=improved_code.strip(),
                description=f"Improve code quality ({len(issues)} issues addressed)",
                confidence=0.7,
                reasoning=f"Addresses {len(issues)} code quality and security issues"
            )
            
        except Exception as e:
            logger.error(f"Failed to generate general improvements: {e}")
            return None
    
    def _create_empty_response(self, task: Task) -> AgentResponse:
        """Create empty response when no code provided"""
        return AgentResponse(
            task_id=task.id,
            agent_name=self.name,
            suggestions=[],
            metadata={"error": "No code provided for analysis"}
        )
    
    def _create_error_response(self, task: Task, error: str) -> AgentResponse:
        """Create error response"""
        return AgentResponse(
            task_id=task.id,
            agent_name=self.name,
            suggestions=[],
            metadata={"error": error}
        )
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return self.capabilities
    
    async def health_check(self) -> bool:
        """Check if agent is healthy"""
        try:
            # Test LLM connection
            await self.llm_manager.generate("test", max_tokens=10)
            return True
        except:
            return False
