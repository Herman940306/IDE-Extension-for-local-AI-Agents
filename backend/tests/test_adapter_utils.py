"""
Unit tests for adapter utilities
Project Creator: Herman Swanepoel
"""

import pytest
from src.adapters.adapter_utils import AdapterUtils, AdapterExceptions


class TestAdapterUtils:
    """Test suite for AdapterUtils"""

    def test_extract_code_blocks_single(self):
        """Test extracting a single code block"""
        text = """
Here is some code:
```python
def hello():
    print("world")
```
"""
        blocks = AdapterUtils.extract_code_blocks(text)
        assert len(blocks) == 1
        code, description = blocks[0]
        assert "def hello():" in code
        assert "Here is some code:" in description

    def test_extract_code_blocks_multiple(self):
        """Test extracting multiple code blocks"""
        text = """
First block:
```python
x = 1
```

Second block:
```javascript
const y = 2;
```
"""
        blocks = AdapterUtils.extract_code_blocks(text)
        assert len(blocks) == 2
        assert "x = 1" in blocks[0][0]
        assert "const y = 2" in blocks[1][0]

    def test_extract_code_blocks_no_description(self):
        """Test code block without description"""
        text = "```python\ncode\n```"
        blocks = AdapterUtils.extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0][1] == "Code suggestion"

    def test_calculate_base_confidence_completed(self):
        """Test confidence calculation for completed task"""
        confidence = AdapterUtils.calculate_base_confidence(
            status="completed", has_suggestions=True, success_rate=1.0
        )
        assert confidence == 1.0

    def test_calculate_base_confidence_failed(self):
        """Test confidence calculation for failed task"""
        confidence = AdapterUtils.calculate_base_confidence(
            status="failed", has_suggestions=False, success_rate=0.0
        )
        assert confidence == 0.5

    def test_calculate_base_confidence_partial(self):
        """Test confidence calculation for partial success"""
        confidence = AdapterUtils.calculate_base_confidence(
            status="completed", has_suggestions=True, success_rate=0.5
        )
        assert 0.85 <= confidence <= 0.95

    def test_format_reasoning_steps_basic(self):
        """Test formatting reasoning steps"""
        steps = [
            {"tool": "analyzer", "thought": "Analyzing code", "status": "success"},
            {"tool": "generator", "thought": "Generating fix", "status": "success"},
        ]
        reasoning = AdapterUtils.format_reasoning_steps(steps)
        assert "Executed 2 steps" in reasoning
        assert "analyzer" in reasoning
        assert "Analyzing code" in reasoning

    def test_format_reasoning_steps_max_limit(self):
        """Test reasoning steps respects max limit"""
        steps = [
            {"tool": f"tool{i}", "thought": f"thought{i}", "status": "success"} for i in range(10)
        ]
        reasoning = AdapterUtils.format_reasoning_steps(steps, max_steps=3)
        assert "and 7 more steps" in reasoning

    def test_format_reasoning_steps_empty(self):
        """Test formatting empty steps"""
        reasoning = AdapterUtils.format_reasoning_steps([])
        assert "No execution steps recorded" in reasoning

    def test_truncate_output_short(self):
        """Test truncating short output"""
        output = "Short text"
        result = AdapterUtils.truncate_output(output, 100)
        assert result == "Short text"

    def test_truncate_output_long(self):
        """Test truncating long output"""
        output = "a" * 1000
        result = AdapterUtils.truncate_output(output, 100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_calculate_step_success_rate_all_success(self):
        """Test success rate with all successful steps"""
        steps = [{"status": "success"}, {"status": "completed"}, {"status": "success"}]
        rate = AdapterUtils.calculate_step_success_rate(steps)
        assert rate == 1.0

    def test_calculate_step_success_rate_partial(self):
        """Test success rate with partial success"""
        steps = [{"status": "success"}, {"status": "failed"}, {"status": "success"}]
        rate = AdapterUtils.calculate_step_success_rate(steps)
        assert rate == pytest.approx(0.666, rel=0.01)

    def test_calculate_step_success_rate_empty(self):
        """Test success rate with no steps"""
        rate = AdapterUtils.calculate_step_success_rate([])
        assert rate == 0.0


class TestAdapterExceptions:
    """Test suite for AdapterExceptions"""

    def test_adapter_error(self):
        """Test base AdapterError"""
        with pytest.raises(AdapterExceptions.AdapterError):
            raise AdapterExceptions.AdapterError("Test error")

    def test_initialization_error(self):
        """Test AdapterInitializationError"""
        with pytest.raises(AdapterExceptions.AdapterInitializationError):
            raise AdapterExceptions.AdapterInitializationError("Init failed")

    def test_execution_error(self):
        """Test AdapterExecutionError"""
        with pytest.raises(AdapterExceptions.AdapterExecutionError):
            raise AdapterExceptions.AdapterExecutionError("Execution failed")

    def test_timeout_error(self):
        """Test AdapterTimeoutError"""
        with pytest.raises(AdapterExceptions.AdapterTimeoutError):
            raise AdapterExceptions.AdapterTimeoutError("Timeout")

    def test_connection_error(self):
        """Test AdapterConnectionError"""
        with pytest.raises(AdapterExceptions.AdapterConnectionError):
            raise AdapterExceptions.AdapterConnectionError("Connection failed")

    def test_authentication_error(self):
        """Test AdapterAuthenticationError"""
        with pytest.raises(AdapterExceptions.AdapterAuthenticationError):
            raise AdapterExceptions.AdapterAuthenticationError("Auth failed")

    def test_exception_inheritance(self):
        """Test exception inheritance chain"""
        assert issubclass(
            AdapterExceptions.AdapterInitializationError, AdapterExceptions.AdapterError
        )
        assert issubclass(AdapterExceptions.AdapterExecutionError, AdapterExceptions.AdapterError)
        assert issubclass(AdapterExceptions.AdapterTimeoutError, AdapterExceptions.AdapterError)
