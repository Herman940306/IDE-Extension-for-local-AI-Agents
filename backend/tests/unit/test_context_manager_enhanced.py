"""
Enhanced tests for ContextManager service
Project Creator: Herman Swanepoel
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from src.models import CodeContext
from src.services.context_manager import CodeFileEventHandler, ContextManager, LRUCache


class TestLRUCache:
    """Test LRU cache implementation"""

    def test_cache_basic_operations(self):
        """Test basic get/put operations"""
        cache = LRUCache(maxsize=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_cache_eviction(self):
        """Test LRU eviction when maxsize exceeded"""
        cache = LRUCache(maxsize=2)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_cache_lru_ordering(self):
        """Test that accessing items updates LRU order"""
        cache = LRUCache(maxsize=2)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.get("key1")  # Access key1, making it most recently used
        cache.put("key3", "value3")  # Should evict key2, not key1

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"

    def test_cache_update_existing(self):
        """Test updating existing cache entries"""
        cache = LRUCache(maxsize=2)

        cache.put("key1", "value1")
        cache.put("key1", "new_value1")

        assert cache.get("key1") == "new_value1"

    def test_cache_clear(self):
        """Test cache clearing"""
        cache = LRUCache(maxsize=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestCodeFileEventHandler:
    """Test file system event handler"""

    def test_event_handler_modified(self):
        """Test modified event handling"""
        callback = Mock()
        handler = CodeFileEventHandler(callback)

        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/file.py"

        handler.on_modified(event)

        callback.assert_called_once_with("/path/to/file.py", "modified")

    def test_event_handler_created(self):
        """Test created event handling"""
        callback = Mock()
        handler = CodeFileEventHandler(callback)

        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/file.ts"

        handler.on_created(event)

        callback.assert_called_once_with("/path/to/file.ts", "created")

    def test_event_handler_deleted(self):
        """Test deleted event handling"""
        callback = Mock()
        handler = CodeFileEventHandler(callback)

        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/file.js"

        handler.on_deleted(event)

        callback.assert_called_once_with("/path/to/file.js", "deleted")

    def test_event_handler_ignores_directories(self):
        """Test that directories are ignored"""
        callback = Mock()
        handler = CodeFileEventHandler(callback)

        event = Mock()
        event.is_directory = True
        event.src_path = "/path/to/directory"

        handler.on_modified(event)

        callback.assert_not_called()

    def test_event_handler_ignores_non_code_files(self):
        """Test that non-code files are ignored"""
        callback = Mock()
        handler = CodeFileEventHandler(callback)

        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/file.txt"

        handler.on_modified(event)

        callback.assert_not_called()


class TestContextManager:
    """Test ContextManager service"""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create temporary workspace"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create a test file
        test_file = workspace / "test.py"
        test_file.write_text(
            "import os\nfrom pathlib import Path\n\ndef hello():\n    return 'world'\n"
        )

        return workspace

    @pytest.fixture
    def context_manager(self, temp_workspace):
        """Create ContextManager instance"""
        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(temp_workspace), enable_file_watcher=False)
            return manager

    def test_initialization(self, temp_workspace):
        """Test ContextManager initialization"""
        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(temp_workspace), enable_file_watcher=False)

            assert manager.workspace_path == Path(temp_workspace)
            assert isinstance(manager.ast_cache, LRUCache)
            assert isinstance(manager.context_cache, LRUCache)

    def test_detect_language_python(self, context_manager):
        """Test language detection for Python"""
        language = context_manager._detect_language(Path("test.py"))
        assert language == "python"

    def test_detect_language_javascript(self, context_manager):
        """Test language detection for JavaScript"""
        language = context_manager._detect_language(Path("test.js"))
        assert language == "javascript"

    def test_detect_language_typescript(self, context_manager):
        """Test language detection for TypeScript"""
        language = context_manager._detect_language(Path("test.ts"))
        assert language == "typescript"

    def test_detect_language_unknown(self, context_manager):
        """Test language detection for unknown extensions"""
        language = context_manager._detect_language(Path("test.xyz"))
        assert language == "unknown"

    @pytest.mark.asyncio
    async def test_extract_imports_python(self, context_manager):
        """Test extracting Python imports"""
        code = """
import os
import sys
from pathlib import Path
from typing import List, Dict
"""
        imports = await context_manager._extract_imports(code, "python")

        assert len(imports) >= 2
        assert any("import os" in imp for imp in imports)
        assert any("from pathlib import Path" in imp for imp in imports)

    @pytest.mark.asyncio
    async def test_extract_imports_javascript(self, context_manager):
        """Test extracting JavaScript imports"""
        code = """
import React from 'react';
import { useState } from 'react';
const fs = require('fs');
"""
        imports = await context_manager._extract_imports(code, "javascript")

        assert len(imports) >= 2
        assert any("react" in imp for imp in imports)

    @pytest.mark.asyncio
    async def test_extract_imports_typescript(self, context_manager):
        """Test extracting TypeScript imports"""
        code = """
import { Component } from '@angular/core';
import * as utils from './utils';
"""
        imports = await context_manager._extract_imports(code, "typescript")

        assert len(imports) >= 1
        assert any("@angular/core" in imp or "utils" in imp for imp in imports)

    @pytest.mark.asyncio
    async def test_extract_imports_unknown_language(self, context_manager):
        """Test import extraction returns empty for unknown languages"""
        code = "some code"
        imports = await context_manager._extract_imports(code, "unknown")

        assert imports == []

    def test_get_surrounding_code(self, context_manager):
        """Test getting surrounding code"""
        code = "\n".join([f"line {i}" for i in range(20)])

        surrounding = context_manager._get_surrounding_code(code, 10, context_lines=2)

        assert "line 8" in surrounding
        assert "line 9" in surrounding
        assert "line 10" in surrounding
        assert "line 11" in surrounding
        assert "line 12" in surrounding

    def test_get_surrounding_code_at_start(self, context_manager):
        """Test surrounding code at file start"""
        code = "\n".join([f"line {i}" for i in range(10)])

        surrounding = context_manager._get_surrounding_code(code, 0, context_lines=5)

        assert "line 0" in surrounding
        assert surrounding.startswith("line 0")

    def test_get_surrounding_code_at_end(self, context_manager):
        """Test surrounding code at file end"""
        code = "\n".join([f"line {i}" for i in range(10)])

        surrounding = context_manager._get_surrounding_code(code, 9, context_lines=5)

        assert "line 9" in surrounding
        assert surrounding.endswith("line 9")

    def test_get_current_branch_no_repo(self, context_manager):
        """Test getting current branch with no Git repo"""
        context_manager.repo = None
        branch = context_manager._get_current_branch()

        assert branch is None

    def test_get_current_branch_with_repo(self, context_manager):
        """Test getting current branch with Git repo"""
        mock_repo = Mock()
        mock_repo.active_branch.name = "main"
        context_manager.repo = mock_repo

        branch = context_manager._get_current_branch()

        assert branch == "main"

    @pytest.mark.asyncio
    async def test_get_recent_commits_no_repo(self, context_manager):
        """Test getting recent commits with no Git repo"""
        context_manager.repo = None
        commits = await context_manager._get_recent_commits("test.py")

        assert commits == []

    @pytest.mark.asyncio
    async def test_get_recent_commits_with_repo(self, context_manager):
        """Test getting recent commits with Git repo"""
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.message = "Test commit"
        mock_commit.author.name = "Test Author"
        mock_commit.committed_date = 1234567890

        mock_repo = Mock()
        mock_repo.iter_commits.return_value = [mock_commit]
        context_manager.repo = mock_repo

        commits = await context_manager._get_recent_commits("test.py", limit=5)

        assert len(commits) == 1
        assert commits[0].hash == "abc12345"
        assert commits[0].message == "Test commit"
        assert commits[0].author == "Test Author"

    @pytest.mark.asyncio
    async def test_get_context(self, context_manager, temp_workspace):
        """Test getting full code context"""
        test_file = temp_workspace / "test.py"

        context = await context_manager.get_context(
            "test.py",
            cursor_position={"line": 2, "character": 0},
            selected_text="def hello():",
        )

        assert isinstance(context, CodeContext)
        assert context.file_path == "test.py"
        assert context.language == "python"
        assert context.cursor_position == {"line": 2, "character": 0}
        assert context.selected_text == "def hello():"
        assert len(context.imports) >= 1

    @pytest.mark.asyncio
    async def test_get_context_with_git(self, context_manager, temp_workspace):
        """Test getting context with Git information"""
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_commit.message = "Test"
        mock_commit.author.name = "Author"
        mock_commit.committed_date = 1234567890

        mock_repo = Mock()
        mock_repo.active_branch.name = "main"
        mock_repo.iter_commits.return_value = [mock_commit]
        context_manager.repo = mock_repo

        context = await context_manager.get_context("test.py")

        assert context.git_branch == "main"
        assert len(context.recent_commits) == 1

    @pytest.mark.asyncio
    async def test_get_context_error_handling(self, context_manager):
        """Test context retrieval with errors returns minimal context"""
        context = await context_manager.get_context(
            "nonexistent.py", cursor_position={"line": 0, "character": 0}
        )

        assert isinstance(context, CodeContext)
        assert context.file_path == "nonexistent.py"
        assert context.language == "python"

    @pytest.mark.asyncio
    async def test_get_dependencies_python(self, context_manager, temp_workspace):
        """Test getting Python dependencies"""
        test_file = temp_workspace / "module.py"
        test_file.write_text("from .utils import helper\nimport .config")

        deps = await context_manager._get_dependencies(test_file)

        assert "utils" in deps or "config" in deps

    @pytest.mark.asyncio
    async def test_get_dependencies_javascript(self, context_manager, temp_workspace):
        """Test getting JavaScript dependencies"""
        test_file = temp_workspace / "module.js"
        test_file.write_text(
            "import utils from './utils';\nconst config = require('./config');"
        )

        deps = await context_manager._get_dependencies(test_file)

        assert "./utils" in deps or "./config" in deps

    @pytest.mark.asyncio
    async def test_read_file(self, context_manager, temp_workspace):
        """Test file reading"""
        test_file = temp_workspace / "test.py"
        content = await context_manager._read_file(test_file)

        assert "import os" in content
        assert "def hello():" in content
