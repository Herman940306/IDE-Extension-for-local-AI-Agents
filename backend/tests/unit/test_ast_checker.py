"""
Unit tests for AST Checker
Project Creator: Herman Swanepoel
"""

import pytest
from src.verifier.ast_checker import ASTChecker


class TestASTChecker:
    """Test suite for ASTChecker"""
    
    def test_initialization(self):
        """Test AST checker initialization"""
        checker = ASTChecker()
        assert "python" in checker.supported_languages
    
    def test_valid_python_code(self):
        """Test validation of valid Python code"""
        checker = ASTChecker()
        code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        result = checker.validate(code, "python")
        assert result["valid"] is True
        assert result["language"] == "python"
        assert "ast_depth" in result
        assert "node_count" in result
    
    def test_invalid_python_code(self):
        """Test validation of invalid Python code"""
        checker = ASTChecker()
        code = """
def broken_function(
    print("Missing closing parenthesis"
"""
        result = checker.validate(code, "python")
        assert result["valid"] is False
        assert result["error_type"] == "SyntaxError"
        assert "message" in result
    
    def test_ast_depth_calculation(self):
        """Test AST depth calculation"""
        checker = ASTChecker()
        
        # Simple code (shallow AST)
        simple_code = "x = 1"
        result = checker.validate(simple_code, "python")
        assert result["ast_depth"] < 5
        
        # Complex code (deeper AST)
        complex_code = """
def outer():
    def inner():
        if True:
            for i in range(10):
                while i > 0:
                    return i
"""
        result = checker.validate(complex_code, "python")
        assert result["ast_depth"] > 5
    
    def test_common_issues_detection(self):
        """Test detection of common code issues"""
        checker = ASTChecker()
        
        # Code with bare except
        code_with_issues = """
try:
    risky_operation()
except:
    pass
"""
        result = checker.validate(code_with_issues, "python")
        assert result["valid"] is True
        assert len(result["issues"]) > 0
        assert any(issue["type"] == "bare_except" for issue in result["issues"])
    
    def test_get_ast_info(self):
        """Test AST information extraction"""
        checker = ASTChecker()
        code = """
class MyClass:
    def method1(self):
        pass
    
    def method2(self, arg):
        return arg

def standalone_function(x, y):
    return x + y
"""
        info = checker.get_ast_info(code, "python")
        assert info is not None
        assert len(info["classes"]) == 1
        assert info["classes"][0]["name"] == "MyClass"
        assert len(info["functions"]) == 1
        assert info["functions"][0]["name"] == "standalone_function"
    
    def test_unsupported_language(self):
        """Test handling of unsupported languages"""
        checker = ASTChecker()
        result = checker.validate("console.log('test');", "javascript")
        assert result["valid"] is True  # Assumes valid for unsupported
        assert "not supported" in result["message"].lower()
