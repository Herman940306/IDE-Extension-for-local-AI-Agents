"""
Context manager for code analysis
Project Creator: Herman Swanepoel
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Set, Callable
from pathlib import Path
import re
import time
from collections import OrderedDict

from git import Repo, InvalidGitRepositoryError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
from models import CodeContext, GitCommit

logger = logging.getLogger(__name__)


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
        self.code_extensions = {'.py', '.ts', '.js', '.tsx', '.jsx', '.java', '.go', '.rs', '.cpp', '.c', '.h'}
    
    def on_modified(self, event):
        if not event.is_directory and Path(event.src_path).suffix in self.code_extensions:
            self.callback(event.src_path, 'modified')
    
    def on_created(self, event):
        if not event.is_directory and Path(event.src_path).suffix in self.code_extensions:
            self.callback(event.src_path, 'created')
    
    def on_deleted(self, event):
        if not event.is_directory and Path(event.src_path).suffix in self.code_extensions:
            self.callback(event.src_path, 'deleted')


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
        
        # File watcher
        self.observer: Optional[Observer] = None
        self.file_change_callbacks: List[Callable] = []
        
        if enable_file_watcher:
            self._setup_file_watcher()
        self.repo: Optional[Repo] = None
        self._initialize_git()

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
        selected_text: Optional[str] = None
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
                content,
                cursor_position.get('line', 0) if cursor_position else 0
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
                recent_commits=recent_commits
            )
            
        except Exception as e:
            logger.error(f"Failed to get context for {file_path}: {e}")
            # Return minimal context
            return CodeContext(
                file_path=file_path,
                language=self._detect_language(Path(file_path)),
                cursor_position=cursor_position,
                selected_text=selected_text
            )

    async def _read_file(self, file_path: Path) -> str:
        """Read file content asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: file_path.read_text(encoding='utf-8', errors='ignore')
        )

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension"""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.m': 'objective-c',
            '.sh': 'bash',
            '.sql': 'sql',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.md': 'markdown',
        }
        
        return extension_map.get(file_path.suffix.lower(), 'unknown')

    async def _extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import statements from code"""
        imports = []
        
        try:
            if language == 'python':
                # Python imports
                import_patterns = [
                    r'^import\s+[\w.]+',
                    r'^from\s+[\w.]+\s+import\s+.+',
                ]
            elif language in ['javascript', 'typescript']:
                # JavaScript/TypeScript imports
                import_patterns = [
                    r'^import\s+.+\s+from\s+[\'"].+[\'"]',
                    r'^import\s+[\'"].+[\'"]',
                    r'^const\s+.+\s+=\s+require\([\'"].+[\'"]\)',
                ]
            elif language == 'java':
                # Java imports
                import_patterns = [r'^import\s+[\w.]+;']
            elif language == 'go':
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
            if language == 'python':
                pattern = r'from\s+\.([\w.]+)\s+import|import\s+\.([\w.]+)'
            elif language in ['javascript', 'typescript']:
                pattern = r'from\s+[\'"](\./[\w./]+)[\'"]|require\([\'"](\./[\w./]+)[\'"]\)'
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

    async def _get_recent_commits(self, file_path: str, limit: int = 5) -> List[GitCommit]:
        """Get recent commits for a file"""
        if not self.repo:
            return []

        commits = []
        
        try:
            loop = asyncio.get_event_loop()
            git_commits = await loop.run_in_executor(
                None,
                lambda: list(self.repo.iter_commits(paths=file_path, max_count=limit))
            )

            for commit in git_commits:
                commits.append(GitCommit(
                    hash=commit.hexsha[:8],
                    message=commit.message.strip(),
                    author=commit.author.name,
                    timestamp=float(commit.committed_date)
                ))

        except Exception as e:
            logger.warning(f"Failed to get recent commits: {e}")

        return commits

    def _get_surrounding_code(self, content: str, line: int, context_lines: int = 10) -> str:
        """Get code surrounding a specific line"""
        try:
            lines = content.split('\n')
            start = max(0, line - context_lines)
            end = min(len(lines), line + context_lines + 1)
            return '\n'.join(lines[start:end])
        except Exception as e:
            logger.warning(f"Failed to get surrounding code: {e}")
            return ""

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
            "total_files": 0
        }

        try:
            # Count files by language
            for file_path in self.workspace_path.rglob("*"):
                if file_path.is_file():
                    language = self._detect_language(file_path)
                    if language != 'unknown':
                        structure["files_by_language"][language] = \
                            structure["files_by_language"].get(language, 0) + 1
                        structure["total_files"] += 1

        except Exception as e:
            logger.error(f"Failed to get project structure: {e}")

        return structure

    async def find_related_files(
        self,
        file_path: str,
        max_results: int = 10
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
            dependencies = await self._get_dependencies(full_path)
            
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
                    except:
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
                "modified_files": len([item.a_path for item in self.repo.index.diff(None)]),
            }
        except Exception as e:
            logger.error(f"Failed to get Git status: {e}")
            return {"has_git": True, "error": str(e)}

    def _setup_file_watcher(self) -> None:
        """Setup file system watcher for real-time updates"""
        try:
            self.observer = Observer()
            event_handler = CodeFileEventHandler(self._on_file_change)
            self.observer.schedule(event_handler, str(self.workspace_path), recursive=True)
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
            
            logger.debug(f"File {event_type}: {rel_path}")
            
            # Notify callbacks
            for callback in self.file_change_callbacks:
                try:
                    callback(rel_path, event_type)
                except Exception as e:
                    logger.error(f"File change callback error: {e}")
                    
        except Exception as e:
            logger.warning(f"Error handling file change: {e}")
    
    def register_file_change_callback(self, callback: Callable[[str, str], None]) -> None:
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
            "git_cache_valid": self.git_cache is not None and (time.time() - self.git_cache_time) < self.git_cache_ttl,
            "file_watcher_active": self.observer is not None and self.observer.is_alive() if self.observer else False
        }
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.observer:
            try:
                self.observer.stop()
            except:
                pass
