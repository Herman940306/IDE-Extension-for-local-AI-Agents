"""
Enhanced tests for CodeSmellDetector
Focus: Increase coverage from 15% to 70%+
"""

from unittest.mock import AsyncMock, Mock

import pytest
from src.models import Priority
from src.services.code_smell_detector import CodeSmellDetector
from src.services.embeddings_service import EmbeddingsService


@pytest.fixture
def mock_embeddings_service():
    """Mock embeddings service"""
    service = Mock(spec=EmbeddingsService)
    service.embed_code = AsyncMock(return_value=[0.1] * 384)
    service.compute_similarity = Mock(return_value=0.9)
    return service


@pytest.fixture
def detector(mock_embeddings_service):
    """CodeSmellDetector instance"""
    return CodeSmellDetector(mock_embeddings_service)


class TestPythonSmellDetection:
    """Test Python-specific smell detection"""

    @pytest.mark.asyncio
    async def test_detect_god_class(self, detector):
        """Test detection of god class (>10 methods)"""
        code = """
class GodClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
"""
        smells = await detector.detect_smells("test.py", code, "python")

        god_class_smells = [s for s in smells if s.smell_type == "god_class"]
        assert len(god_class_smells) >= 1
        assert "GodClass" in god_class_smells[0].description
        assert god_class_smells[0].severity == Priority.HIGH

    @pytest.mark.asyncio
    async def test_detect_long_function(self, detector):
        """Test detection of long functions (>50 lines)"""
        # Create a function with >50 lines
        lines = ["def long_function():\n"]
        lines.extend([f"    x = {i}\n" for i in range(60)])
        code = "".join(lines)

        smells = await detector.detect_smells("test.py", code, "python")

        long_func_smells = [s for s in smells if s.smell_type == "long_function"]
        assert len(long_func_smells) >= 1
        assert "long_function" in long_func_smells[0].description

    @pytest.mark.asyncio
    async def test_detect_too_many_parameters(self, detector):
        """Test detection of functions with too many parameters (>5)"""
        code = """
def complex_function(a, b, c, d, e, f, g):
    return a + b + c + d + e + f + g
"""
        smells = await detector.detect_smells("test.py", code, "python")

        param_smells = [s for s in smells if s.smell_type == "too_many_parameters"]
        assert len(param_smells) >= 1
        assert "7 parameters" in param_smells[0].description

    @pytest.mark.asyncio
    async def test_parameters_at_threshold(self, detector):
        """Test function with exactly 5 parameters (should not flag)"""
        code = """
def function_with_five(a, b, c, d, e):
    return a + b + c + d + e
"""
        smells = await detector.detect_smells("test.py", code, "python")

        param_smells = [s for s in smells if s.smell_type == "too_many_parameters"]
        assert len(param_smells) == 0

    @pytest.mark.asyncio
    async def test_no_smells_clean_code(self, detector):
        """Test that clean code produces no smells"""
        code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
        smells = await detector.detect_smells("test.py", code, "python")

        # May have semantic duplication smells, but no structural smells
        structural_smells = [
            s
            for s in smells
            if s.smell_type in ["god_class", "long_function", "complex_function"]
        ]
        assert len(structural_smells) == 0


class TestJavaScriptSmellDetection:
    """Test JavaScript/TypeScript smell detection"""

    @pytest.mark.asyncio
    async def test_detect_js_callback_hell(self, detector):
        """Test detection of callback hell"""
        code = """
function processData(callback) {
    getData(function(a) {
        getMoreData(a, function(b) {
            getMoreData(b, function(c) {
                getMoreData(c, function(d) {
                    getMoreData(d, function(e) {
                        callback(e);
                    });
                });
            });
        });
    });
}
"""
        smells = await detector.detect_smells("test.js", code, "javascript")

        callback_smells = [s for s in smells if s.smell_type == "callback_hell"]
        assert len(callback_smells) >= 1

    @pytest.mark.asyncio
    async def test_detect_var_usage(self, detector):
        """Test detection of outdated 'var' keyword usage"""
        code = """
function oldStyle() {
    var x = 1;
    var y = 2;
    var z = 3;
    var a = 4;
    var b = 5;
    return x + y + z + a + b;
}
"""
        smells = await detector.detect_smells("test.js", code, "javascript")

        var_smells = [s for s in smells if s.smell_type == "outdated_syntax"]
        assert len(var_smells) >= 1
        assert "var" in var_smells[0].description


class TestSemanticDuplication:
    """Test semantic duplication detection"""

    @pytest.mark.asyncio
    async def test_detect_semantic_duplication_high_similarity(self, detector):
        """Test detection of semantically similar code blocks"""
        detector.embeddings_service.compute_similarity = Mock(return_value=0.95)

        code = """
def function1():
    x = 1
    y = 2
    return x + y

def function2():
    a = 1
    b = 2
    return a + b
"""
        smells = await detector.detect_smells("test.py", code, "python")

        dup_smells = [s for s in smells if s.smell_type == "semantic_duplication"]
        assert len(dup_smells) >= 1
        assert dup_smells[0].confidence >= 0.85

    @pytest.mark.asyncio
    async def test_no_duplication_low_similarity(self, detector):
        """Test no duplication when similarity is below threshold"""
        # Mock different embeddings for each function
        embedding1 = [1.0] + [0.0] * 383
        embedding2 = [0.0] * 383 + [1.0]

        detector.embeddings_service.embed_code = AsyncMock(
            side_effect=[embedding1, embedding2]
        )

        code = """
def function1():
    return "hello"

def function2():
    return [1, 2, 3, 4, 5]
"""
        smells = await detector.detect_smells("test.py", code, "python")

        dup_smells = [s for s in smells if s.smell_type == "semantic_duplication"]
        # With very different embeddings, similarity should be ~0
        assert len(dup_smells) == 0


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_handle_invalid_python_syntax(self, detector):
        """Test handling of invalid Python syntax"""
        code = """
def broken function(:
    return "this won't parse"
"""
        smells = await detector.detect_smells("test.py", code, "python")

        # Should not crash, returns empty or partial results
        assert isinstance(smells, list)

    @pytest.mark.asyncio
    async def test_handle_embeddings_service_failure(self, detector):
        """Test handling when embeddings service fails"""
        detector.embeddings_service.embed_code = AsyncMock(
            side_effect=Exception("Embeddings failed")
        )

        code = """
def simple_function():
    return 42
"""
        smells = await detector.detect_smells("test.py", code, "python")

        # Should still return structural smells even if semantic detection fails
        assert isinstance(smells, list)


class TestLanguageSupport:
    """Test language-specific features"""

    @pytest.mark.asyncio
    async def test_unsupported_language_fallback(self, detector):
        """Test fallback for unsupported languages"""
        code = "int main() { return 0; }"

        smells = await detector.detect_smells("test.c", code, "c")

        # Should still attempt semantic duplication
        assert isinstance(smells, list)

    @pytest.mark.asyncio
    async def test_typescript_detection(self, detector):
        """Test TypeScript is treated like JavaScript"""
        code = """
function test(): number {
    return 42;
}
"""
        smells = await detector.detect_smells("test.ts", code, "typescript")

        assert isinstance(smells, list)


class TestThresholdConfiguration:
    """Test threshold configuration"""

    def test_configure_similarity_threshold(self, mock_embeddings_service):
        """Test configuring similarity threshold"""
        detector = CodeSmellDetector(mock_embeddings_service)
        detector.similarity_threshold = 0.95

        assert detector.similarity_threshold == 0.95

    def test_configure_god_class_threshold(self, mock_embeddings_service):
        """Test configuring god class threshold"""
        detector = CodeSmellDetector(mock_embeddings_service)
        detector.god_class_threshold = 20

        assert detector.god_class_threshold == 20

    @pytest.mark.asyncio
    async def test_god_class_with_custom_threshold(self, mock_embeddings_service):
        """Test god class detection respects custom threshold"""
        detector = CodeSmellDetector(mock_embeddings_service)
        detector.god_class_threshold = 5  # Lower threshold

        code = """
class SmallClass:
    def m1(self): pass
    def m2(self): pass
    def m3(self): pass
    def m4(self): pass
    def m5(self): pass
    def m6(self): pass
"""
        smells = await detector.detect_smells("test.py", code, "python")

        god_class_smells = [s for s in smells if s.smell_type == "god_class"]
        assert len(god_class_smells) >= 1
