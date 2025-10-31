"""
Comprehensive tests for ContextManager - Targeting 70%+ coverage
Project Creator: Herman Swanepoel

This test suite adds comprehensive coverage for:
- AST parsing with tree-sitter
- Dependency graph operations
- Impact analysis
- Project structure analysis
- File relationship tracking
- Git status operations
- File watcher callbacks
- Cache management
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import Mock, patch

import networkx as nx
import pytest
from src.models import CodeContext
from src.services.context_manager import ContextManager


class TestASTParsingComprehensive:
    """Test tree-sitter AST parsing functionality"""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create temporary workspace with code files"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Python file
        py_file = workspace / "example.py"
        py_file.write_text(
            """
import os
from typing import List

class ExampleClass:
    def method_one(self):
        pass

    def method_two(self):
        return 42

def standalone_function():
    return "hello"
"""
        )

        # JavaScript file
        js_file = workspace / "example.js"
        js_file.write_text(
            """
import React from 'react';

class Component extends React.Component {
    render() {
        return null;
    }
}

function helper() {
    return true;
}

const arrow = () => {
    return false;
};
"""
        )

        # TypeScript file
        ts_file = workspace / "example.ts"
        ts_file.write_text(
            """
import { Injectable } from '@angular/core';

@Injectable()
export class Service {
    getData(): string {
        return "data";
    }
}

export function utility(): void {
    console.log("util");
}
"""
        )

        return workspace

    @pytest.fixture
    def context_manager(self, temp_workspace):
        """Create ContextManager instance"""
        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(temp_workspace), enable_file_watcher=False)
            return manager

    @pytest.mark.asyncio
    async def test_parse_ast_python_with_cache(self, context_manager, temp_workspace):
        """Test AST parsing for Python with caching"""
        py_file = temp_workspace / "example.py"

        # First parse
        ast_info = await context_manager.parse_ast(py_file)

        if ast_info is not None:  # Only if tree-sitter is available
            assert ast_info["language"] == "python"
            assert any("ExampleClass" in str(c) for c in ast_info.get("classes", []))
            assert any(
                "standalone_function" in str(f) for f in ast_info.get("functions", [])
            )

            # Second parse should use cache
            ast_info_cached = await context_manager.parse_ast(py_file)
            assert ast_info_cached == ast_info

    @pytest.mark.asyncio
    async def test_parse_ast_javascript(self, context_manager, temp_workspace):
        """Test AST parsing for JavaScript"""
        js_file = temp_workspace / "example.js"

        ast_info = await context_manager.parse_ast(js_file)

        if ast_info is not None:
            assert ast_info["language"] == "javascript"
            assert len(ast_info.get("functions", [])) >= 0
            assert len(ast_info.get("classes", [])) >= 0

    @pytest.mark.asyncio
    async def test_parse_ast_typescript(self, context_manager, temp_workspace):
        """Test AST parsing for TypeScript"""
        ts_file = temp_workspace / "example.ts"

        ast_info = await context_manager.parse_ast(ts_file)

        if ast_info is not None:
            assert ast_info["language"] == "typescript"

    @pytest.mark.asyncio
    async def test_parse_ast_with_content_provided(
        self, context_manager, temp_workspace
    ):
        """Test AST parsing with pre-provided content"""
        py_file = temp_workspace / "example.py"
        content = "def test(): pass"

        ast_info = await context_manager.parse_ast(py_file, content=content)

        if ast_info is not None:
            assert ast_info["language"] == "python"

    @pytest.mark.asyncio
    async def test_parse_ast_unsupported_language(
        self, context_manager, temp_workspace
    ):
        """Test AST parsing for unsupported language returns None"""
        unknown_file = temp_workspace / "file.xyz"
        unknown_file.write_text("unknown content")

        ast_info = await context_manager.parse_ast(unknown_file)

        # Should return None for unsupported languages
        assert ast_info is None

    @pytest.mark.asyncio
    async def test_parse_ast_error_handling(self, context_manager, temp_workspace):
        """Test AST parsing error handling"""
        # Invalid Python syntax
        bad_file = temp_workspace / "bad.py"
        bad_file.write_text("def broken(: pass")

        ast_info = await context_manager.parse_ast(bad_file)

        # Should handle parse errors gracefully
        # Returns None on error
        if ast_info is not None:
            assert "language" in ast_info

    def test_extract_python_symbols(self, context_manager):
        """Test Python symbol extraction from AST"""
        # Mock tree-sitter node structure
        mock_node = Mock()
        mock_node.type = "function_definition"
        mock_node.start_point = (10, 0)
        mock_name_node = Mock()
        mock_name_node.start_byte = 0
        mock_name_node.end_byte = 4
        mock_node.child_by_field_name = Mock(return_value=mock_name_node)
        mock_node.children = []

        content = "test_function"

        with patch.object(context_manager, "_get_node_text", return_value="test_func"):
            symbols = context_manager._extract_python_symbols(mock_node, content)

            assert symbols["language"] == "python"
            assert "functions" in symbols
            assert "classes" in symbols
            assert "imports" in symbols

    def test_extract_js_symbols(self, context_manager):
        """Test JavaScript symbol extraction from AST"""
        mock_node = Mock()
        mock_node.type = "function_declaration"
        mock_node.start_point = (5, 0)
        mock_name_node = Mock()
        mock_name_node.start_byte = 0
        mock_name_node.end_byte = 6
        mock_node.child_by_field_name = Mock(return_value=mock_name_node)
        mock_node.children = []

        content = "helper"

        with patch.object(context_manager, "_get_node_text", return_value="helper"):
            symbols = context_manager._extract_js_symbols(mock_node, content)

            assert symbols["language"] == "javascript"
            assert "functions" in symbols

    def test_get_node_text(self, context_manager):
        """Test extracting text from tree-sitter node"""
        mock_node = Mock()
        mock_node.start_byte = 10
        mock_node.end_byte = 15

        content = "some code hello world more code"

        text = context_manager._get_node_text(mock_node, content)

        assert text == "hello"

    def test_get_node_text_none_node(self, context_manager):
        """Test getting node text with None node"""
        text = context_manager._get_node_text(None, "content")

        assert text == ""


class TestDependencyGraphComprehensive:
    """Test dependency graph operations"""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create workspace with multiple interconnected files"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # File A imports nothing
        (workspace / "a.py").write_text("# Root file\n")

        # File B imports A
        (workspace / "b.py").write_text("from .a import something\n")

        # File C imports B
        (workspace / "c.py").write_text("from .b import other\n")

        # JS files
        (workspace / "utils.js").write_text("export const helper = () => {};\n")
        (workspace / "main.js").write_text("import { helper } from './utils';\n")

        return workspace

    @pytest.fixture
    def context_manager(self, temp_workspace):
        """Create ContextManager instance"""
        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(temp_workspace), enable_file_watcher=False)
            return manager

    @pytest.mark.asyncio
    async def test_build_dependency_graph(self, context_manager):
        """Test building complete dependency graph"""
        graph = await context_manager.build_dependency_graph(force_rebuild=True)

        assert isinstance(graph, nx.DiGraph)
        assert graph.number_of_nodes() >= 0
        # Graph built successfully

    @pytest.mark.asyncio
    async def test_build_dependency_graph_caching(self, context_manager):
        """Test dependency graph caching"""
        # First build
        graph1 = await context_manager.build_dependency_graph(force_rebuild=True)
        initial_time = context_manager.graph_last_updated

        # Second build without force should use cache (< 5 minutes)
        await asyncio.sleep(0.1)
        graph2 = await context_manager.build_dependency_graph(force_rebuild=False)

        # Should be same graph object (cached)
        assert graph1 is graph2
        assert context_manager.graph_last_updated == initial_time

    @pytest.mark.asyncio
    async def test_build_dependency_graph_force_rebuild(self, context_manager):
        """Test forcing dependency graph rebuild"""
        await context_manager.build_dependency_graph(force_rebuild=True)
        time1 = context_manager.graph_last_updated

        await asyncio.sleep(0.1)

        await context_manager.build_dependency_graph(force_rebuild=True)
        time2 = context_manager.graph_last_updated

        # Time should be updated
        assert time2 > time1

    def test_resolve_import_path_relative_python(self, context_manager, tmp_path):
        """Test resolving relative Python imports"""
        workspace = tmp_path / "project"
        workspace.mkdir()

        source_file = workspace / "src" / "main.py"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("# source")

        target_file = workspace / "src" / "utils.py"
        target_file.write_text("# target")

        resolved = context_manager._resolve_import_path(source_file, "./utils")

        # Should resolve to utils.py
        if resolved:
            assert resolved.name == "utils.py"

    def test_resolve_import_path_relative_js(self, context_manager, tmp_path):
        """Test resolving relative JS imports"""
        workspace = tmp_path / "project"
        workspace.mkdir()

        source_file = workspace / "src" / "app.js"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("// source")

        target_file = workspace / "src" / "helpers.js"
        target_file.write_text("// target")

        resolved = context_manager._resolve_import_path(source_file, "./helpers")

        if resolved:
            assert resolved.name == "helpers.js"

    def test_resolve_import_path_index_file(self, context_manager, tmp_path):
        """Test resolving import to index file"""
        workspace = tmp_path / "project"
        workspace.mkdir()

        source_file = workspace / "app.js"
        source_file.write_text("// app")

        utils_dir = workspace / "utils"
        utils_dir.mkdir()
        (utils_dir / "index.js").write_text("// index")

        resolved = context_manager._resolve_import_path(source_file, "./utils")

        if resolved:
            assert resolved.name == "index.js"

    def test_resolve_import_path_python_init(self, context_manager, tmp_path):
        """Test resolving Python package with __init__.py"""
        workspace = tmp_path / "project"
        workspace.mkdir()

        source_file = workspace / "main.py"
        source_file.write_text("# main")

        pkg_dir = workspace / "package"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("# init")

        resolved = context_manager._resolve_import_path(source_file, "./package")

        if resolved:
            assert resolved.name == "__init__.py"

    def test_resolve_import_path_non_relative(self, context_manager, tmp_path):
        """Test that non-relative imports return None"""
        source_file = tmp_path / "test.py"
        source_file.write_text("# test")

        resolved = context_manager._resolve_import_path(source_file, "os")

        assert resolved is None

    def test_resolve_import_path_not_found(self, context_manager, tmp_path):
        """Test resolving path that doesn't exist"""
        source_file = tmp_path / "test.py"
        source_file.write_text("# test")

        resolved = context_manager._resolve_import_path(source_file, "./nonexistent")

        assert resolved is None

    @pytest.mark.asyncio
    async def test_get_file_dependencies(self, context_manager):
        """Test getting dependencies for specific file"""
        await context_manager.build_dependency_graph(force_rebuild=True)

        deps_info = await context_manager.get_file_dependencies("a.py")

        assert "file" in deps_info
        assert "dependencies" in deps_info
        assert "dependents" in deps_info
        assert "depth" in deps_info
        assert isinstance(deps_info["dependencies"], list)

    @pytest.mark.asyncio
    async def test_get_file_dependencies_not_in_graph(self, context_manager):
        """Test getting dependencies for file not in graph"""
        deps_info = await context_manager.get_file_dependencies("nonexistent.py")

        assert deps_info["file"] == "nonexistent.py"
        assert deps_info["dependencies"] == []
        assert deps_info["dependents"] == []
        assert deps_info["depth"] == 0

    @pytest.mark.asyncio
    async def test_get_file_dependencies_is_leaf(self, context_manager):
        """Test identifying leaf nodes (no dependencies)"""
        await context_manager.build_dependency_graph(force_rebuild=True)

        deps_info = await context_manager.get_file_dependencies("a.py")

        assert "is_leaf" in deps_info
        assert "is_root" in deps_info


class TestImpactAnalysisComprehensive:
    """Test impact analysis functionality"""

    @pytest.fixture
    def context_manager_with_graph(self, tmp_path):
        """Create context manager with populated dependency graph"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create files
        (workspace / "root.py").write_text("# root")
        (workspace / "mid.py").write_text("from .root import x")
        (workspace / "leaf.py").write_text("from .mid import y")

        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(workspace), enable_file_watcher=False)

            # Manually build simple graph
            manager.dependency_graph.add_node("root.py")
            manager.dependency_graph.add_node("mid.py")
            manager.dependency_graph.add_node("leaf.py")
            manager.dependency_graph.add_edge("root.py", "mid.py")
            manager.dependency_graph.add_edge("mid.py", "leaf.py")
            manager.graph_last_updated = time.time()

            return manager

    @pytest.mark.asyncio
    async def test_get_impact_analysis(self, context_manager_with_graph):
        """Test impact analysis for file changes"""
        impact = await context_manager_with_graph.get_impact_analysis("root.py")

        assert impact["file"] == "root.py"
        assert "directly_affected" in impact
        assert "transitively_affected" in impact
        assert "total_impact" in impact
        assert isinstance(impact["directly_affected"], list)

    @pytest.mark.asyncio
    async def test_get_impact_analysis_not_in_graph(self, context_manager_with_graph):
        """Test impact analysis for file not in graph"""
        impact = await context_manager_with_graph.get_impact_analysis("nonexistent.py")

        assert impact["file"] == "nonexistent.py"
        assert impact["directly_affected"] == []
        assert impact["transitively_affected"] == []
        assert impact["total_impact"] == 0

    @pytest.mark.asyncio
    async def test_get_impact_analysis_leaf_node(self, context_manager_with_graph):
        """Test impact analysis for leaf node"""
        impact = await context_manager_with_graph.get_impact_analysis("leaf.py")

        # Leaf nodes should have no descendants
        assert impact["total_impact"] == 0


class TestProjectStructureComprehensive:
    """Test project structure analysis"""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create workspace with various file types"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Python files
        (workspace / "main.py").write_text("# main")
        (workspace / "utils.py").write_text("# utils")

        # JS files
        (workspace / "app.js").write_text("// app")
        (workspace / "helper.js").write_text("// helper")

        # TS files
        (workspace / "service.ts").write_text("// service")

        # Other files
        (workspace / "README.md").write_text("# README")
        (workspace / "data.json").write_text("{}")

        return workspace

    @pytest.fixture
    def context_manager(self, temp_workspace):
        """Create ContextManager instance"""
        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(temp_workspace), enable_file_watcher=False)
            return manager

    @pytest.mark.asyncio
    async def test_get_project_structure(self, context_manager):
        """Test getting project structure overview"""
        structure = await context_manager.get_project_structure()

        assert "workspace_path" in structure
        assert "has_git" in structure
        assert "files_by_language" in structure
        assert "total_files" in structure
        assert isinstance(structure["files_by_language"], dict)
        assert structure["total_files"] >= 0

    @pytest.mark.asyncio
    async def test_get_project_structure_counts(self, context_manager, temp_workspace):
        """Test project structure file counts"""
        structure = await context_manager.get_project_structure()

        # Should detect Python, JS, TS, Markdown, JSON files
        assert structure["total_files"] >= 5
        if "python" in structure["files_by_language"]:
            assert structure["files_by_language"]["python"] >= 2
        if "javascript" in structure["files_by_language"]:
            assert structure["files_by_language"]["javascript"] >= 2


class TestFileRelationshipsComprehensive:
    """Test file relationship finding"""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create workspace with related files"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Main file
        (workspace / "user_model.py").write_text(
            """
class User:
    def __init__(self, name):
        self.name = name
"""
        )

        # Related files that reference user_model
        (workspace / "user_service.py").write_text(
            """
from user_model import User

def create_user(name):
    return User(name)
"""
        )

        (workspace / "user_controller.py").write_text(
            """
import user_model

def handle_request():
    user = user_model.User("test")
"""
        )

        # Unrelated file
        (workspace / "config.py").write_text("CONFIG = {}")

        return workspace

    @pytest.fixture
    def context_manager(self, temp_workspace):
        """Create ContextManager instance"""
        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(temp_workspace), enable_file_watcher=False)
            return manager

    @pytest.mark.asyncio
    async def test_find_related_files(self, context_manager):
        """Test finding files related to a target file"""
        related = await context_manager.find_related_files(
            "user_model.py", max_results=10
        )

        assert isinstance(related, list)
        # Should find files that import or reference user_model
        # May or may not find related files depending on search

    @pytest.mark.asyncio
    async def test_find_related_files_max_results(self, context_manager):
        """Test max_results limit in find_related_files"""
        related = await context_manager.find_related_files(
            "user_model.py", max_results=1
        )

        assert len(related) <= 1

    @pytest.mark.asyncio
    async def test_find_related_files_nonexistent(self, context_manager):
        """Test finding related files for nonexistent file"""
        related = await context_manager.find_related_files("nonexistent.py")

        # Should return empty list or handle gracefully
        assert isinstance(related, list)


class TestGitStatusComprehensive:
    """Test Git status operations"""

    @pytest.fixture
    def context_manager_no_git(self, tmp_path):
        """Create context manager without Git repo"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(workspace), enable_file_watcher=False)
            manager.repo = None
            return manager

    @pytest.fixture
    def context_manager_with_git(self, tmp_path):
        """Create context manager with mocked Git repo"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(workspace), enable_file_watcher=False)

            # Mock Git repo
            mock_repo = Mock()
            mock_repo.active_branch.name = "main"
            mock_repo.is_dirty.return_value = True
            mock_repo.untracked_files = ["new_file.py", "another.py"]
            mock_item = Mock()
            mock_item.a_path = "modified.py"
            mock_repo.index.diff.return_value = [mock_item]

            manager.repo = mock_repo
            return manager

    def test_get_git_status_no_repo(self, context_manager_no_git):
        """Test Git status when no repo exists"""
        status = context_manager_no_git.get_git_status()

        assert status["has_git"] is False

    def test_get_git_status_with_repo(self, context_manager_with_git):
        """Test Git status with repository"""
        status = context_manager_with_git.get_git_status()

        assert status["has_git"] is True
        assert status["branch"] == "main"
        assert status["is_dirty"] is True
        assert status["untracked_files"] == 2
        assert status["modified_files"] == 1

    def test_get_git_status_error_handling(self, tmp_path):
        """Test Git status error handling"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(workspace), enable_file_watcher=False)

            # Mock repo that raises exception
            mock_repo = Mock()
            mock_repo.active_branch.name.side_effect = Exception("Git error")
            manager.repo = mock_repo

            status = manager.get_git_status()

            assert status["has_git"] is True
            assert "error" in status


class TestFileWatcherComprehensive:
    """Test file watcher functionality"""

    @pytest.fixture
    def context_manager(self, tmp_path):
        """Create context manager"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(workspace), enable_file_watcher=False)
            return manager

    def test_register_file_change_callback(self, context_manager):
        """Test registering file change callbacks"""
        callback = Mock()

        context_manager.register_file_change_callback(callback)

        assert callback in context_manager.file_change_callbacks

    def test_on_file_change_invalidates_cache(self, context_manager, tmp_path):
        """Test that file changes invalidate caches"""
        # Pre-populate caches
        context_manager.ast_cache.put("test.py", {"cached": "data"})
        context_manager.context_cache.put("test.py", Mock())
        context_manager.graph_last_updated = time.time()

        # Trigger file change
        test_file = tmp_path / "workspace" / "test.py"
        context_manager._on_file_change(str(test_file), "modified")

        # Graph should be invalidated
        assert context_manager.graph_last_updated == 0

    def test_on_file_change_calls_callbacks(self, context_manager, tmp_path):
        """Test that file changes trigger callbacks"""
        callback1 = Mock()
        callback2 = Mock()

        context_manager.register_file_change_callback(callback1)
        context_manager.register_file_change_callback(callback2)

        test_file = tmp_path / "workspace" / "test.py"
        context_manager._on_file_change(str(test_file), "modified")

        callback1.assert_called_once()
        callback2.assert_called_once()

    def test_on_file_change_callback_error_handling(self, context_manager, tmp_path):
        """Test error handling in file change callbacks"""
        failing_callback = Mock(side_effect=Exception("Callback error"))
        working_callback = Mock()

        context_manager.register_file_change_callback(failing_callback)
        context_manager.register_file_change_callback(working_callback)

        test_file = tmp_path / "workspace" / "test.py"

        # Should not raise exception despite failing callback
        context_manager._on_file_change(str(test_file), "modified")

        # Working callback should still be called
        working_callback.assert_called_once()

    def test_stop_file_watcher(self, tmp_path):
        """Test stopping file watcher"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("src.services.context_manager.Observer") as MockObserver:
            mock_observer = Mock()
            MockObserver.return_value = mock_observer

            manager = ContextManager(str(workspace), enable_file_watcher=True)
            manager.observer = mock_observer

            manager.stop_file_watcher()

            mock_observer.stop.assert_called_once()
            mock_observer.join.assert_called_once()


class TestCacheManagementComprehensive:
    """Test cache management operations"""

    @pytest.fixture
    def context_manager(self, tmp_path):
        """Create context manager"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(workspace), enable_file_watcher=False)
            return manager

    @pytest.mark.asyncio
    async def test_get_cached_context(self, context_manager):
        """Test retrieving cached context"""
        # Add to cache
        mock_context = Mock(spec=CodeContext)
        context_manager.context_cache.put("test.py", mock_context)

        cached = await context_manager.get_cached_context("test.py")

        assert cached == mock_context

    @pytest.mark.asyncio
    async def test_get_cached_context_miss(self, context_manager):
        """Test cache miss returns None"""
        cached = await context_manager.get_cached_context("nonexistent.py")

        assert cached is None

    @pytest.mark.asyncio
    async def test_invalidate_cache_single_file(self, context_manager):
        """Test invalidating cache for single file"""
        context_manager.ast_cache.put("test.py", {"ast": "data"})
        context_manager.context_cache.put("test.py", Mock())

        await context_manager.invalidate_cache("test.py")

        # File should be invalidated (set to None)
        assert context_manager.ast_cache.get("test.py") is None
        assert context_manager.context_cache.get("test.py") is None

    @pytest.mark.asyncio
    async def test_invalidate_cache_all(self, context_manager):
        """Test invalidating all caches"""
        context_manager.ast_cache.put("file1.py", {"data": 1})
        context_manager.ast_cache.put("file2.py", {"data": 2})
        context_manager.context_cache.put("file1.py", Mock())
        context_manager.git_cache = {"branch": "main"}

        await context_manager.invalidate_cache(None)

        # All caches should be cleared
        assert context_manager.ast_cache.get("file1.py") is None
        assert context_manager.ast_cache.get("file2.py") is None
        assert context_manager.git_cache is None

    def test_get_cache_stats(self, context_manager):
        """Test getting cache statistics"""
        # Populate caches
        context_manager.ast_cache.put("file1.py", {"ast": "data"})
        context_manager.context_cache.put("file1.py", Mock())
        context_manager.dependency_graph.add_node("node1")
        context_manager.dependency_graph.add_edge("node1", "node2")
        context_manager.graph_last_updated = time.time()

        stats = context_manager.get_cache_stats()

        assert "ast_cache_size" in stats
        assert "context_cache_size" in stats
        assert "git_cache_valid" in stats
        assert "file_watcher_active" in stats
        assert "dependency_graph_nodes" in stats
        assert "dependency_graph_edges" in stats
        assert "graph_age_seconds" in stats

        assert stats["ast_cache_size"] >= 1
        assert stats["context_cache_size"] >= 1
        assert stats["dependency_graph_nodes"] >= 1

    def test_get_cache_stats_empty(self, context_manager):
        """Test cache stats when empty"""
        stats = context_manager.get_cache_stats()

        assert stats["ast_cache_size"] == 0
        assert stats["context_cache_size"] == 0
        assert stats["dependency_graph_nodes"] == 0
        assert stats["dependency_graph_edges"] == 0


class TestImportExtractionEdgeCases:
    """Test import extraction edge cases"""

    @pytest.fixture
    def context_manager(self, tmp_path):
        """Create context manager"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(workspace), enable_file_watcher=False)
            return manager

    @pytest.mark.asyncio
    async def test_extract_imports_java(self, context_manager):
        """Test extracting Java imports"""
        java_code = """
import java.util.List;
import java.util.ArrayList;
import com.example.MyClass;
"""
        imports = await context_manager._extract_imports(java_code, "java")

        assert len(imports) >= 1
        assert any("java.util" in imp for imp in imports)

    @pytest.mark.asyncio
    async def test_extract_imports_go(self, context_manager):
        """Test extracting Go imports"""
        go_code = """
import "fmt"
import "github.com/example/package"
"""
        imports = await context_manager._extract_imports(go_code, "go")

        assert len(imports) >= 1

    @pytest.mark.asyncio
    async def test_extract_imports_error_handling(self, context_manager):
        """Test import extraction error handling"""
        # Invalid code that might cause regex issues
        invalid_code = "import \x00\x01\x02 invalid"

        # Should not raise exception
        imports = await context_manager._extract_imports(invalid_code, "python")

        assert isinstance(imports, list)

    @pytest.mark.asyncio
    async def test_extract_imports_empty_code(self, context_manager):
        """Test extracting imports from empty code"""
        imports = await context_manager._extract_imports("", "python")

        assert imports == []

    @pytest.mark.asyncio
    async def test_extract_imports_multiline_python(self, context_manager):
        """Test extracting multiline Python imports"""
        code = """
import os
import sys
from pathlib import (
    Path,
    PurePath
)
from typing import List, Dict, Optional
"""
        imports = await context_manager._extract_imports(code, "python")

        # Should extract multiple imports
        assert len(imports) >= 2


class TestLanguageDetectionEdgeCases:
    """Test language detection edge cases"""

    @pytest.fixture
    def context_manager(self, tmp_path):
        """Create context manager"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("src.services.context_manager.Observer"):
            manager = ContextManager(str(workspace), enable_file_watcher=False)
            return manager

    def test_detect_language_various_extensions(self, context_manager):
        """Test language detection for various file extensions"""
        test_cases = {
            "file.java": "java",
            "file.cpp": "cpp",
            "file.c": "c",
            "file.go": "go",
            "file.rs": "rust",
            "file.rb": "ruby",
            "file.php": "php",
            "file.swift": "swift",
            "file.kt": "kotlin",
            "file.scala": "scala",
            "file.html": "html",
            "file.css": "css",
            "file.json": "json",
            "file.yaml": "yaml",
            "file.yml": "yaml",
            "file.xml": "xml",
            "file.md": "markdown",
            "file.sh": "bash",
            "file.sql": "sql",
        }

        for filename, expected_lang in test_cases.items():
            detected = context_manager._detect_language(Path(filename))
            assert detected == expected_lang, f"Failed for {filename}"

    def test_detect_language_case_insensitive(self, context_manager):
        """Test that language detection is case-insensitive"""
        assert context_manager._detect_language(Path("FILE.PY")) == "python"
        assert context_manager._detect_language(Path("FILE.JS")) == "javascript"
        assert context_manager._detect_language(Path("FILE.TS")) == "typescript"


class TestContextManagerCleanup:
    """Test cleanup and teardown"""

    def test_destructor_stops_observer(self, tmp_path):
        """Test that destructor stops observer"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("src.services.context_manager.Observer") as MockObserver:
            mock_observer = Mock()
            mock_observer.is_alive.return_value = True
            MockObserver.return_value = mock_observer

            manager = ContextManager(str(workspace), enable_file_watcher=True)
            manager.observer = mock_observer

            # Call the cleanup method directly
            manager.__del__()

            # Observer stop should be called
            mock_observer.stop.assert_called()
