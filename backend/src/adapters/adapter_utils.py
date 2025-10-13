"""
Shared utilities for framework adapters
Project Creator: Herman Swanepoel

This module provides common functionality used across different agent adapters
to reduce code duplication and improve maintainability.
"""

import re
from typing import List, Dict, Any, Tuple


class AdapterUtils:
    """Shared utilities for framework adapters"""

    @staticmethod
    def extract_code_blocks(text: str) -> List[Tuple[str, str]]:
        """
        Extract code blocks with descriptions from text
        
        Args:
            text: Text containing code blocks in markdown format
            
        Returns:
            List of tuples (code, description)
        """
        blocks: List[Tuple[str, str]] = []
        code_matches = re.finditer(r'```[\w]*\n(.*?)```', text, re.DOTALL)
        
        for match in code_matches:
            code = match.group(1).strip()
            
            # Find description before code block (look back up to 200 chars)
            start = max(0, match.start() - 200)
            context = text[start:match.start()]
            desc_match = re.search(r'([^\n]+)\n```', context)
            description = desc_match.group(1).strip() if desc_match else "Code suggestion"
            
            blocks.append((code, description))
        
        return blocks

    @staticmethod
    def calculate_base_confidence(
        status: str,
        has_suggestions: bool,
        success_rate: float = 0.0,
        base: float = 0.5
    ) -> float:
        """
        Calculate confidence score with consistent logic
        
        Args:
            status: Execution status (e.g., "completed", "failed")
            has_suggestions: Whether suggestions were generated
            success_rate: Success rate of steps/actions (0.0 to 1.0)
            base: Base confidence score
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = base
        
        # Increase if execution completed successfully
        if status == "completed":
            confidence += 0.2
        
        # Increase if we have suggestions
        if has_suggestions:
            confidence += 0.2
        
        # Increase based on success rate
        confidence += 0.1 * success_rate
        
        return min(confidence, 1.0)

    @staticmethod
    def format_reasoning_steps(
        steps: List[Dict[str, Any]],
        max_steps: int = 5,
        step_key: str = "thought"
    ) -> str:
        """
        Format execution steps into readable reasoning text
        
        Args:
            steps: List of execution steps
            max_steps: Maximum number of steps to include
            step_key: Key to extract step description from
            
        Returns:
            Formatted reasoning string
        """
        if not steps:
            return "No execution steps recorded"
        
        reasoning = f"Executed {len(steps)} steps:\n\n"
        
        for i, step in enumerate(steps[:max_steps], 1):
            # Extract step information
            tool = step.get("tool") or step.get("name", "unknown")
            thought = step.get(step_key, "")
            status = step.get("status", "unknown")
            
            reasoning += f"{i}. [{status.upper()}] {tool}\n"
            if thought:
                reasoning += f"   {step_key.capitalize()}: {thought}\n"
        
        if len(steps) > max_steps:
            reasoning += f"\n... and {len(steps) - max_steps} more steps\n"
        
        return reasoning

    @staticmethod
    def truncate_output(output: str, max_length: int = 500) -> str:
        """
        Truncate output to maximum length with ellipsis
        
        Args:
            output: Output text to truncate
            max_length: Maximum length
            
        Returns:
            Truncated output
        """
        if len(output) <= max_length:
            return output
        
        return output[:max_length] + "..."

    @staticmethod
    def calculate_step_success_rate(steps: List[Dict[str, Any]]) -> float:
        """
        Calculate success rate from execution steps
        
        Args:
            steps: List of execution steps with status
            
        Returns:
            Success rate between 0.0 and 1.0
        """
        if not steps:
            return 0.0
        
        successful_steps = sum(
            1 for step in steps 
            if step.get("status") in ["success", "completed"]
        )
        
        return successful_steps / len(steps)


class AdapterExceptions:
    """Custom exceptions for adapters"""

    class AdapterError(Exception):
        """Base adapter exception"""
        pass

    class AdapterInitializationError(AdapterError):
        """Failed to initialize adapter"""
        pass

    class AdapterExecutionError(AdapterError):
        """Failed to execute task"""
        pass

    class AdapterTimeoutError(AdapterError):
        """Task execution timed out"""
        pass

    class AdapterConnectionError(AdapterError):
        """Failed to connect to adapter service"""
        pass

    class AdapterAuthenticationError(AdapterError):
        """Authentication failed"""
        pass
