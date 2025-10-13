"""
Context manager for code analysis
Project Creator: Herman Swanepoel
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import re

from git import Repo, InvalidGitRepositoryError
from models import CodeContext, GitCommit

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages code context including file system, Git history, and dependencies
    """

    def __init__(self, workspace_path: str):
        """
        Initialize context manager
        
        Args:
            workspace_path: Path to workspace
        """
        self.workspace_path = Path(workspace_path)
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
