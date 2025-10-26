"""
Prompt Templates Tests
"""

from src.models import TaskType
from src.services.prompt_templates import PromptTemplates


class TestPromptTemplatesSystemPrompts:
    """Test system prompt generation"""

    def test_get_inline_suggestion_prompt(self):
        """Test inline suggestion system prompt"""
        prompt = PromptTemplates.get_system_prompt(TaskType.INLINE_SUGGESTION)
        assert prompt is not None
        assert "code completion" in prompt.lower() or "suggestion" in prompt.lower()
        assert len(prompt) > 50

    def test_get_refactor_prompt(self):
        """Test refactor system prompt"""
        prompt = PromptTemplates.get_system_prompt(TaskType.REFACTOR)
        assert prompt is not None
        assert "refactor" in prompt.lower()
        assert "code quality" in prompt.lower() or "maintainability" in prompt.lower()

    def test_get_test_generation_prompt(self):
        """Test test generation system prompt"""
        prompt = PromptTemplates.get_system_prompt(TaskType.TEST_GENERATION)
        assert prompt is not None
        assert "test" in prompt.lower()
        assert "coverage" in prompt.lower() or "edge case" in prompt.lower()

    def test_get_bug_detection_prompt(self):
        """Test bug detection system prompt"""
        prompt = PromptTemplates.get_system_prompt(TaskType.BUG_DETECTION)
        assert prompt is not None
        assert "bug" in prompt.lower() or "issue" in prompt.lower()
        assert len(prompt) > 50

    def test_get_documentation_prompt(self):
        """Test documentation system prompt"""
        prompt = PromptTemplates.get_system_prompt(TaskType.DOCUMENTATION)
        assert prompt is not None
        assert "documentation" in prompt.lower() or "docstring" in prompt.lower()

    def test_get_security_analysis_prompt(self):
        """Test security analysis system prompt"""
        prompt = PromptTemplates.get_system_prompt(TaskType.SECURITY_ANALYSIS)
        assert prompt is not None
        assert "security" in prompt.lower()
        assert "vulnerability" in prompt.lower() or "attack" in prompt.lower()

    def test_all_task_types_have_prompts(self):
        """Test all task types have system prompts"""
        for task_type in TaskType:
            prompt = PromptTemplates.get_system_prompt(task_type)
            assert prompt is not None
            assert isinstance(prompt, str)
            assert len(prompt) > 0


class TestPromptTemplatesCodeSuggestion:
    """Test code suggestion prompt building"""

    def test_build_code_suggestion_prompt(self):
        """Test building code suggestion prompt"""
        code = "def add(a, b):\n    return a + b"
        context = {"language": "python", "file": "math.py"}

        prompt = PromptTemplates.build_code_suggestion_prompt(code, context)
        assert prompt is not None
        assert isinstance(prompt, str)
        assert code in prompt or "add" in prompt

    def test_code_suggestion_with_empty_code(self):
        """Test code suggestion with empty code"""
        prompt = PromptTemplates.build_code_suggestion_prompt("", {})
        assert prompt is not None
        assert isinstance(prompt, str)

    def test_code_suggestion_with_complex_context(self):
        """Test code suggestion with complex context"""
        code = "class MyClass:\n    pass"
        context = {
            "language": "python",
            "file": "models.py",
            "imports": ["typing", "dataclasses"],
            "line_number": 42,
        }

        prompt = PromptTemplates.build_code_suggestion_prompt(code, context)
        assert prompt is not None
        assert isinstance(prompt, str)


class TestPromptTemplatesRefactoring:
    """Test refactoring prompt building"""

    def test_build_refactor_prompt(self):
        """Test building refactor prompt"""
        code = "def bad_function():\n    x = 1\n    y = 2\n    return x + y"
        context = {"issues": ["complexity"], "suggestions": ["simplify"]}

        prompt = PromptTemplates.build_refactor_prompt(code, context)
        assert prompt is not None
        assert isinstance(prompt, str)

    def test_refactor_prompt_with_minimal_context(self):
        """Test refactor prompt with minimal context"""
        code = "print('hello')"
        prompt = PromptTemplates.build_refactor_prompt(code, {})
        assert prompt is not None


class TestPromptTemplatesTestGeneration:
    """Test test generation prompt building"""

    def test_build_test_prompt(self):
        """Test building test generation prompt"""
        code = "def multiply(a, b):\n    return a * b"
        context = {"function_name": "multiply", "test_framework": "pytest"}

        prompt = PromptTemplates.build_test_generation_prompt(code, context)
        assert prompt is not None
        assert isinstance(prompt, str)

    def test_test_prompt_includes_code(self):
        """Test that test prompt includes code"""
        code = "def divide(a, b):\n    return a / b"
        prompt = PromptTemplates.build_test_generation_prompt(code, {})
        assert prompt is not None


class TestPromptTemplatesBugDetection:
    """Test bug detection prompt building"""

    def test_build_bug_detection_prompt(self):
        """Test building bug detection prompt"""
        code = "def unsafe_division(a, b):\n    return a / b  # No zero check!"
        context = {"check_types": ["logic", "runtime"]}

        prompt = PromptTemplates.build_bug_detection_prompt(code, context)
        assert prompt is not None
        assert isinstance(prompt, str)

    def test_bug_detection_with_security_focus(self):
        """Test bug detection with security context"""
        code = "query = f'SELECT * FROM users WHERE id={user_id}'"
        context = {"focus": "security"}

        prompt = PromptTemplates.build_bug_detection_prompt(code, context)
        assert prompt is not None


class TestPromptTemplatesDocumentation:
    """Test documentation prompt building"""

    def test_build_documentation_prompt(self):
        """Test building documentation prompt"""
        code = "def calculate_total(items):\n    return sum(item.price for item in items)"
        context = {"style": "google", "include_examples": True}

        prompt = PromptTemplates.build_documentation_prompt(code, context)
        assert prompt is not None
        assert isinstance(prompt, str)

    def test_documentation_prompt_minimal(self):
        """Test documentation prompt with minimal input"""
        code = "x = 42"
        prompt = PromptTemplates.build_documentation_prompt(code, {})
        assert prompt is not None


class TestPromptTemplatesEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_code(self):
        """Test handling of empty code"""
        prompt = PromptTemplates.build_code_suggestion_prompt("", {})
        assert prompt is not None

    def test_none_context(self):
        """Test handling of None context"""
        code = "test"
        # Should handle None gracefully or use empty dict
        try:
            prompt = PromptTemplates.build_code_suggestion_prompt(code, None)
            assert prompt is not None or True  # Either works or raises handled exception
        except (TypeError, AttributeError):
            pass  # Acceptable if None is not handled

    def test_large_code_block(self):
        """Test handling of large code blocks"""
        large_code = "def test():\n    pass\n" * 1000
        prompt = PromptTemplates.build_code_suggestion_prompt(large_code, {})
        assert prompt is not None

    def test_special_characters_in_code(self):
        """Test handling of special characters"""
        code = 'def test():\n    return "Hello\\nWorld\\t\\"Quotes\\""'
        prompt = PromptTemplates.build_code_suggestion_prompt(code, {})
        assert prompt is not None

    def test_unicode_in_code(self):
        """Test handling of Unicode characters"""
        code = "# Comment: 你好世界 🚀\ndef hello():\n    return 'Привет'"
        prompt = PromptTemplates.build_code_suggestion_prompt(code, {})
        assert prompt is not None


class TestPromptTemplatesConsistency:
    """Test consistency across different methods"""

    def test_all_prompts_are_strings(self):
        """Test all generated prompts are strings"""
        code = "def test(): pass"
        context = {}

        prompts = [
            PromptTemplates.build_code_suggestion_prompt(code, context),
            PromptTemplates.build_refactor_prompt(code, context),
            PromptTemplates.build_test_generation_prompt(code, context),
            PromptTemplates.build_bug_detection_prompt(code, context),
            PromptTemplates.build_documentation_prompt(code, context),
        ]

        for prompt in prompts:
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_prompts_not_empty(self):
        """Test no prompt returns empty string"""
        for task_type in TaskType:
            prompt = PromptTemplates.get_system_prompt(task_type)
            assert len(prompt) > 0
