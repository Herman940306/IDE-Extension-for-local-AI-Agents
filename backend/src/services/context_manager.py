"""
Context manager for code analysis
Project Creator: Herman Swanepoel
"""

import asyncio
import logging
import re
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import networkx as nx
from git import InvalidGitRepositoryError, Repo
from src.models import CodeContext, GitCommit
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

try:
    import tree_sitter_javascript as tsjavascript
    import tree_sitter_python as tspython
    import tree_sitter_typescript as tstypescript
    from tree_sitter import Language, Parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.warning("tree-sitter not available - AST parsing disabled")


class CodeFileEventHandler(FileSystemEventHandler):
    """File system event handler for code changes"""

    def __init__(self, callback: Callable[[str, str], None]):
        """
        Initialize event handler

        Args:
            callback: Function to call on file changes (file_path, event_type)
        """
        super().__init__()
        self.callback = callback
        self.code_extensions = {
            ".py",
            ".ts",
            ".js",
            ".tsx",
            ".jsx",
            ".java",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".h",
        }

    def on_modified(self, event):
        if (
            not event.is_directory
            and Path(event.src_path).suffix in self.code_extensions
        ):
            self.callback(event.src_path, "modified")

    def on_created(self, event):
        if (
            not event.is_directory
            and Path(event.src_path).suffix in self.code_extensions
        ):
            self.callback(event.src_path, "created")

    def on_deleted(self, event):
        if (
            not event.is_directory
            and Path(event.src_path).suffix in self.code_extensions
        ):
            self.callback(event.src_path, "deleted")


class LRUCache:
    """Simple LRU cache for AST parsing results"""

    def __init__(self, maxsize: int = 100):
        self.cache: OrderedDict = OrderedDict()
        self.maxsize = maxsize

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.maxsize:
            # Remove least recently used
            self.cache.popitem(last=False)

    def clear(self) -> None:
        self.cache.clear()


class ContextManager:
    """
    Manages code context including file system, Git history, and dependencies
    Enhanced with file watching and caching for real-time updates
    """

    def __init__(self, workspace_path: str, enable_file_watcher: bool = True):
        """
        Initialize context manager

        Args:
            workspace_path: Path to workspace
            enable_file_watcher: Enable real-time file watching
        """
        self.workspace_path = Path(workspace_path)
        self.enable_file_watcher = enable_file_watcher

        # Caching for performance
        self.ast_cache = LRUCache(maxsize=200)
        self.context_cache = LRUCache(maxsize=100)
        self.git_cache: Optional[Dict[str, Any]] = None
        self.git_cache_time: float = 0
        self.git_cache_ttl: float = 60.0  # 60 seconds

        # Dependency graph
        self.dependency_graph: nx.DiGraph = nx.DiGraph()
        self.graph_last_updated: float = 0

        # Tree-sitter parsers
        self.parsers: Dict[str, Parser] = {}
        if TREE_SITTER_AVAILABLE:
            self._initialize_parsers()

        # File watcher
        self.observer: Optional[Observer] = None
        self.file_change_callbacks: List[Callable] = []

        if enable_file_watcher:
            self._setup_file_watcher()
        self.repo: Optional[Repo] = None
        self._initialize_git()

    def _initialize_parsers(self) -> None:
        """Initialize tree-sitter parsers for supported languages"""
        try:
            # Python parser
            PY_LANGUAGE = Language(tspython.language(), "python")
            py_parser = Parser()
            py_parser.set_language(PY_LANGUAGE)
            self.parsers["python"] = py_parser

            # JavaScript parser
            JS_LANGUAGE = Language(tsjavascript.language(), "javascript")
            js_parser = Parser()
            js_parser.set_language(JS_LANGUAGE)
            self.parsers["javascript"] = js_parser

            # TypeScript parser
            TS_LANGUAGE = Language(tstypescript.language_typescript(), "typescript")
            ts_parser = Parser()
            ts_parser.set_language(TS_LANGUAGE)
            self.parsers["typescript"] = ts_parser

            # TSX parser
            TSX_LANGUAGE = Language(tstypescript.language_tsx(), "tsx")
            tsx_parser = Parser()
            tsx_parser.set_language(TSX_LANGUAGE)
            self.parsers["tsx"] = tsx_parser

            logger.info("✓ Tree-sitter parsers initialized")
        except Exception as e:
            logger.error(f"Failed to initialize tree-sitter parsers: {e}")
            self.parsers = {}

    def _initialize_git(self) -> None:
        """Initialize Git repository if available"""
        try:
            self.repo = Repo(self.workspace_path, search_parent_directories=True)
            logger.info(f"✓ Git repository found: {self.repo.working_dir}")
        except InvalidGitRepositoryError:
            logger.warning("No Git repository found in workspace")
            self.repo = None

    async def get_context(
        self,
        file_path: str,
        cursor_position: Optional[Dict[str, int]] = None,
        selected_text: Optional[str] = None,
    ) -> CodeContext:
        """
        Get comprehensive context for a file

        Args:
            file_path: Path to file
            cursor_position: Cursor position (line, character)
            selected_text: Selected text

        Returns:
            CodeContext with all available information
        """
        try:
            full_path = self.workspace_path / file_path

            # Read file content
            content = await self._read_file(full_path)

            # Detect language
            language = self._detect_language(full_path)

            # Extract imports
            imports = await self._extract_imports(content, language)

            # Get dependencies
            dependencies = await self._get_dependencies(full_path)

            # Get Git context
            git_branch = None
            recent_commits = []
            if self.repo:
                git_branch = self._get_current_branch()
                recent_commits = await self._get_recent_commits(file_path, limit=5)

            # Get surrounding code
            surrounding_code = self._get_surrounding_code(
                content, cursor_position.get("line", 0) if cursor_position else 0
            )

            return CodeContext(
                file_path=file_path,
                language=language,
                cursor_position=cursor_position,
                selected_text=selected_text,
                surrounding_code=surrounding_code,
                imports=imports,
                dependencies=dependencies,
                git_branch=git_branch,
                recent_commits=recent_commits,
            )

        except Exception as e:
            logger.error(f"Failed to get context for {file_path}: {e}")
            # Return minimal context
            return CodeContext(
                file_path=file_path,
                language=self._detect_language(Path(file_path)),
                cursor_position=cursor_position,
                selected_text=selected_text,
            )

    async def _read_file(self, file_path: Path) -> str:
        """Read file content asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: file_path.read_text(encoding="utf-8", errors="ignore")
        )

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension"""
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".r": "r",
            ".m": "objective-c",
            ".sh": "bash",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".md": "markdown",
        }

        return extension_map.get(file_path.suffix.lower(), "unknown")

    async def _extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import statements from code"""
        imports = []

        try:
            if language == "python":
                # Python imports
                import_patterns = [
                    r"^import\s+[\w.]+",
                    r"^from\s+[\w.]+\s+import\s+.+",
                ]
            elif language in ["javascript", "typescript"]:
                # JavaScript/TypeScript imports
                import_patterns = [
                    r'^import\s+.+\s+from\s+[\'"].+[\'"]',
                    r'^import\s+[\'"].+[\'"]',
                    r'^const\s+.+\s+=\s+require\([\'"].+[\'"]\)',
                ]
            elif language == "java":
                # Java imports
                import_patterns = [r"^import\s+[\w.]+;"]
            elif language == "go":
                # Go imports
                import_patterns = [r'^import\s+[\'"].+[\'"]']
            else:
                return imports

            for pattern in import_patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                imports.extend([match.group(0) for match in matches])

        except Exception as e:
            logger.warning(f"Failed to extract imports: {e}")

        return imports

    async def _get_dependencies(self, file_path: Path) -> List[str]:
        """Get file dependencies (files that this file imports)"""
        dependencies = []

        try:
            content = await self._read_file(file_path)
            language = self._detect_language(file_path)

            # Extract relative imports
            if language == "python":
                pattern = r"from\s+\.([\w.]+)\s+import|import\s+\.([\w.]+)"
            elif language in ["javascript", "typescript"]:
                pattern = (
                    r'from\s+[\'"](\./[\w./]+)[\'"]|require\([\'"](\./[\w./]+)[\'"]\)'
                )
            else:
                return dependencies

            matches = re.finditer(pattern, content)
            for match in matches:
                dep = match.group(1) or match.group(2)
                if dep:
                    dependencies.append(dep)

        except Exception as e:
            logger.warning(f"Failed to get dependencies: {e}")

        return dependencies

    def _get_current_branch(self) -> Optional[str]:
        """Get current Git branch"""
        if not self.repo:
            return None

        try:
            return self.repo.active_branch.name
        except Exception as e:
            logger.warning(f"Failed to get current branch: {e}")
            return None

    async def _get_recent_commits(
        self, file_path: str, limit: int = 5
    ) -> List[GitCommit]:
        """Get recent commits for a file"""
        if not self.repo:
            return []

        commits = []

        try:
            loop = asyncio.get_event_loop()
            git_commits = await loop.run_in_executor(
                None,
                lambda: list(self.repo.iter_commits(paths=file_path, max_count=limit)),
            )

            for commit in git_commits:
                commits.append(
                    GitCommit(
                        hash=commit.hexsha[:8],
                        message=commit.message.strip(),
                        author=commit.author.name,
                        timestamp=float(commit.committed_date),
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to get recent commits: {e}")

        return commits

    def _get_surrounding_code(
        self, content: str, line: int, context_lines: int = 10
    ) -> str:
        """Get code surrounding a specific line"""
        try:
            lines = content.split("\n")
            start = max(0, line - context_lines)
            end = min(len(lines), line + context_lines + 1)
            return "\n".join(lines[start:end])
        except Exception as e:
            logger.warning(f"Failed to get surrounding code: {e}")
            return ""

    async def parse_ast(
        self, file_path: Path, content: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Parse file using tree-sitter AST

        Args:
            file_path: Path to file
            content: File content (optional, will read if not provided)

        Returns:
            Dictionary with AST information (functions, classes, imports, etc.)
        """
        if not TREE_SITTER_AVAILABLE:
            return None

        # Check cache
        cache_key = str(file_path)
        cached = self.ast_cache.get(cache_key)
        if cached:
            return cached

        try:
            language = self._detect_language(file_path)
            parser = self.parsers.get(language)

            if not parser:
                return None

            # Read content if not provided
            if content is None:
                content = await self._read_file(file_path)

            # Parse
            tree = parser.parse(bytes(content, "utf8"))
            root_node = tree.root_node

            # Extract symbols
            ast_info = {
                "functions": [],
                "classes": [],
                "imports": [],
                "variables": [],
                "language": language,
            }

            # Language-specific extraction
            if language == "python":
                ast_info = self._extract_python_symbols(root_node, content)
            elif language in ["javascript", "typescript", "tsx"]:
                ast_info = self._extract_js_symbols(root_node, content)

            # Cache result
            self.ast_cache.put(cache_key, ast_info)

            return ast_info

        except Exception as e:
            logger.error(f"Failed to parse AST for {file_path}: {e}")
            return None

    def _extract_python_symbols(self, root_node, content: str) -> Dict[str, Any]:
        """Extract symbols from Python AST"""
        symbols = {
            "functions": [],
            "classes": [],
            "imports": [],
            "variables": [],
            "language": "python",
        }

        def traverse(node):
            if node.type == "function_definition":
                func_name = self._get_node_text(
                    node.child_by_field_name("name"), content
                )
                symbols["functions"].append(
                    {"name": func_name, "line": node.start_point[0], "type": "function"}
                )

            elif node.type == "class_definition":
                class_name = self._get_node_text(
                    node.child_by_field_name("name"), content
                )
                symbols["classes"].append(
                    {"name": class_name, "line": node.start_point[0], "type": "class"}
                )

            elif node.type in ["import_statement", "import_from_statement"]:
                import_text = self._get_node_text(node, content)
                symbols["imports"].append(import_text)

            # Recurse
            for child in node.children:
                traverse(child)

        traverse(root_node)
        return symbols

    def _extract_js_symbols(self, root_node, content: str) -> Dict[str, Any]:
        """Extract symbols from JavaScript/TypeScript AST"""
        symbols = {
            "functions": [],
            "classes": [],
            "imports": [],
            "variables": [],
            "language": "javascript",
        }

        def traverse(node):
            if node.type in ["function_declaration", "function", "arrow_function"]:
                func_name = "anonymous"
                name_node = node.child_by_field_name("name")
                if name_node:
                    func_name = self._get_node_text(name_node, content)
                symbols["functions"].append(
                    {"name": func_name, "line": node.start_point[0], "type": "function"}
                )

            elif node.type == "class_declaration":
                class_name = self._get_node_text(
                    node.child_by_field_name("name"), content
                )
                symbols["classes"].append(
                    {"name": class_name, "line": node.start_point[0], "type": "class"}
                )

            elif node.type == "import_statement":
                import_text = self._get_node_text(node, content)
                symbols["imports"].append(import_text)

            # Recurse
            for child in node.children:
                traverse(child)

        traverse(root_node)
        return symbols

    def _get_node_text(self, node, content: str) -> str:
        """Get text content of a tree-sitter node"""
        if node is None:
            return ""
        return content[node.start_byte : node.end_byte]

    async def build_dependency_graph(self, force_rebuild: bool = False) -> nx.DiGraph:
        """
        Build dependency graph for the entire codebase

        Args:
            force_rebuild: Force rebuild even if cache is valid

        Returns:
            NetworkX directed graph of file dependencies
        """
        # Check if rebuild needed
        if (
            not force_rebuild and time.time() - self.graph_last_updated < 300
        ):  # 5 minutes
            return self.dependency_graph

        logger.info("Building dependency graph...")
        self.dependency_graph = nx.DiGraph()

        try:
            # Find all code files
            code_files = []
            for ext in [".py", ".js", ".ts", ".tsx", ".jsx"]:
                code_files.extend(self.workspace_path.rglob(f"*{ext}"))

            # Build graph
            for file_path in code_files:
                try:
                    rel_path = str(file_path.relative_to(self.workspace_path))

                    # Add node
                    self.dependency_graph.add_node(rel_path, path=str(file_path))

                    # Get dependencies
                    dependencies = await self._get_dependencies(file_path)

                    # Add edges
                    for dep in dependencies:
                        # Resolve dependency path
                        dep_path = self._resolve_import_path(file_path, dep)
                        if dep_path:
                            dep_rel = str(dep_path.relative_to(self.workspace_path))
                            self.dependency_graph.add_edge(rel_path, dep_rel)

                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")
                    continue

            self.graph_last_updated = time.time()
            logger.info(
                f"✓ Dependency graph built: {self.dependency_graph.number_of_nodes()} nodes, {self.dependency_graph.number_of_edges()} edges"  # noqa: E501
            )

        except Exception as e:
            logger.error(f"Failed to build dependency graph: {e}")

        return self.dependency_graph

    def _resolve_import_path(
        self, source_file: Path, import_path: str
    ) -> Optional[Path]:
        """
        Resolve relative import to absolute file path

        Args:
            source_file: Source file doing the import
            import_path: Import path (e.g., './utils', '../models/user')

        Returns:
            Resolved file path or None
        """
        try:
            # Handle relative imports
            if import_path.startswith("."):
                base_dir = source_file.parent
                resolved = (base_dir / import_path).resolve()

                # Try with common extensions
                for ext in ["", ".py", ".js", ".ts", ".tsx", ".jsx"]:
                    candidate = resolved.with_suffix(ext)
                    if candidate.exists() and candidate.is_file():
                        return candidate

                # Try as directory with index file
                for index_file in ["__init__.py", "index.js", "index.ts"]:
                    candidate = resolved / index_file
                    if candidate.exists():
                        return candidate

            return None

        except Exception as e:
            logger.debug(f"Failed to resolve import {import_path}: {e}")
            return None

    async def get_file_dependencies(self, file_path: str) -> Dict[str, Any]:
        """
        Get dependencies for a specific file

        Args:
            file_path: Relative path to file

        Returns:
            Dictionary with dependency information
        """
        # Ensure graph is built
        await self.build_dependency_graph()

        if file_path not in self.dependency_graph:
            return {"file": file_path, "dependencies": [], "dependents": [], "depth": 0}

        # Get direct dependencies (files this file imports)
        dependencies = list(self.dependency_graph.successors(file_path))

        # Get dependents (files that import this file)
        dependents = list(self.dependency_graph.predecessors(file_path))

        # Calculate dependency depth
        try:
            # Find all paths from root nodes
            root_nodes = [
                n
                for n in self.dependency_graph.nodes()
                if self.dependency_graph.in_degree(n) == 0
            ]
            depths = []
            for root in root_nodes:
                if nx.has_path(self.dependency_graph, root, file_path):
                    depth = nx.shortest_path_length(
                        self.dependency_graph, root, file_path
                    )
                    depths.append(depth)
            depth = max(depths) if depths else 0
        except Exception as e:
            logger.debug(f"Could not calculate depth for {file_path}: {e}")
            depth = 0

        return {
            "file": file_path,
            "dependencies": dependencies,
            "dependents": dependents,
            "depth": depth,
            "is_leaf": len(dependencies) == 0,
            "is_root": len(dependents) == 0,
        }

    async def get_impact_analysis(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze impact of changes to a file

        Args:
            file_path: Relative path to file

        Returns:
            Dictionary with impact analysis
        """
        # Ensure graph is built
        await self.build_dependency_graph()

        if file_path not in self.dependency_graph:
            return {
                "file": file_path,
                "directly_affected": [],
                "transitively_affected": [],
                "total_impact": 0,
            }

        # Get all descendants (files affected by changes)
        try:
            descendants = nx.descendants(self.dependency_graph, file_path)
            directly_affected = list(self.dependency_graph.predecessors(file_path))
            transitively_affected = list(descendants - set(directly_affected))

            return {
                "file": file_path,
                "directly_affected": directly_affected,
                "transitively_affected": transitively_affected,
                "total_impact": len(descendants),
            }
        except Exception as e:
            logger.error(f"Failed to analyze impact: {e}")
            return {
                "file": file_path,
                "directly_affected": [],
                "transitively_affected": [],
                "total_impact": 0,
            }

    async def get_project_structure(self) -> Dict[str, Any]:
        """
        Get project structure overview

        Returns:
            Dictionary with project structure information
        """
        structure = {
            "workspace_path": str(self.workspace_path),
            "has_git": self.repo is not None,
            "files_by_language": {},
            "total_files": 0,
        }

        try:
            # Count files by language
            for file_path in self.workspace_path.rglob("*"):
                if file_path.is_file():
                    language = self._detect_language(file_path)
                    if language != "unknown":
                        structure["files_by_language"][language] = (
                            structure["files_by_language"].get(language, 0) + 1
                        )
                        structure["total_files"] += 1

        except Exception as e:
            logger.error(f"Failed to get project structure: {e}")

        return structure

    async def find_related_files(
        self, file_path: str, max_results: int = 10
    ) -> List[str]:
        """
        Find files related to the given file

        Args:
            file_path: Path to file
            max_results: Maximum number of results

        Returns:
            List of related file paths
        """
        related = set()

        try:
            full_path = self.workspace_path / file_path

            # Get dependencies
            await self._get_dependencies(full_path)

            # Find files that import this file
            file_name = full_path.stem
            for candidate in self.workspace_path.rglob("*"):
                if candidate.is_file() and candidate != full_path:
                    try:
                        content = await self._read_file(candidate)
                        if file_name in content:
                            related.add(str(candidate.relative_to(self.workspace_path)))
                            if len(related) >= max_results:
                                break
                    except Exception as e:
                        logger.debug(f"Error reading file {candidate}: {e}")
                        continue

        except Exception as e:
            logger.warning(f"Failed to find related files: {e}")

        return list(related)[:max_results]

    def get_git_status(self) -> Dict[str, Any]:
        """
        Get Git repository status

        Returns:
            Dictionary with Git status information
        """
        if not self.repo:
            return {"has_git": False}

        try:
            return {
                "has_git": True,
                "branch": self._get_current_branch(),
                "is_dirty": self.repo.is_dirty(),
                "untracked_files": len(self.repo.untracked_files),
                "modified_files": len(
                    [item.a_path for item in self.repo.index.diff(None)]
                ),
            }
        except Exception as e:
            logger.error(f"Failed to get Git status: {e}")
            return {"has_git": True, "error": str(e)}

    def _setup_file_watcher(self) -> None:
        """Setup file system watcher for real-time updates"""
        try:
            self.observer = Observer()
            event_handler = CodeFileEventHandler(self._on_file_change)
            self.observer.schedule(
                event_handler, str(self.workspace_path), recursive=True
            )
            self.observer.start()
            logger.info("✓ File watcher started")
        except Exception as e:
            logger.error(f"Failed to setup file watcher: {e}")
            self.observer = None

    def _on_file_change(self, file_path: str, event_type: str) -> None:
        """Handle file change events"""
        try:
            # Invalidate caches for changed file
            rel_path = str(Path(file_path).relative_to(self.workspace_path))
            self.ast_cache.put(rel_path, None)  # Invalidate
            self.context_cache.put(rel_path, None)  # Invalidate

            # Invalidate dependency graph (will be rebuilt on next access)
            self.graph_last_updated = 0

            logger.debug(f"File {event_type}: {rel_path}")

            # Notify callbacks
            for callback in self.file_change_callbacks:
                try:
                    callback(rel_path, event_type)
                except Exception as e:
                    logger.error(f"File change callback error: {e}")

        except Exception as e:
            logger.warning(f"Error handling file change: {e}")

    def register_file_change_callback(
        self, callback: Callable[[str, str], None]
    ) -> None:
        """
        Register callback for file changes

        Args:
            callback: Function to call on file changes (file_path, event_type)
        """
        self.file_change_callbacks.append(callback)

    def stop_file_watcher(self) -> None:
        """Stop file system watcher"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("File watcher stopped")

    async def get_cached_context(self, file_path: str) -> Optional[CodeContext]:
        """
        Get cached context if available

        Args:
            file_path: Path to file

        Returns:
            Cached CodeContext or None
        """
        return self.context_cache.get(file_path)

    async def invalidate_cache(self, file_path: Optional[str] = None) -> None:
        """
        Invalidate cache for file or all files

        Args:
            file_path: Path to file, or None to clear all
        """
        if file_path:
            self.ast_cache.put(file_path, None)
            self.context_cache.put(file_path, None)
        else:
            self.ast_cache.clear()
            self.context_cache.clear()
            self.git_cache = None

        logger.debug(f"Cache invalidated: {file_path or 'all'}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "ast_cache_size": len(self.ast_cache.cache),
            "context_cache_size": len(self.context_cache.cache),
            "git_cache_valid": self.git_cache is not None
            and (time.time() - self.git_cache_time) < self.git_cache_ttl,
            "file_watcher_active": (
                self.observer is not None and self.observer.is_alive()
                if self.observer
                else False
            ),
            "dependency_graph_nodes": self.dependency_graph.number_of_nodes(),
            "dependency_graph_edges": self.dependency_graph.number_of_edges(),
            "graph_age_seconds": (
                time.time() - self.graph_last_updated
                if self.graph_last_updated > 0
                else None
            ),
        }

    def __del__(self):
        """Cleanup on deletion"""
        if self.observer:
            try:
                self.observer.stop()
            except Exception as e:
                logger.warning(f"Error stopping file observer: {e}")
