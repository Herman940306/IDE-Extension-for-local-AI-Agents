"""MCP server entry point tailored for the IDE Agents integration system.

This module exposes MCP tools that bridge local developer workflows with the
IDE Agents backend. It focuses on fast, deterministic interactions that can be
extended through optional ULTRA intelligence pipelines when available.

Design goals:
    * Centralize configuration through environment variables.
    * Keep the synchronous MCP contract predictable while delegating long
      running work to backend services.
    * Fail softly when optional ML dependencies are missing so that base IDE
      automation keeps working.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

import httpx

try:
    from mcp.server.fastmcp import FastMCP as FastMCPServer

    _FAST_MCP = True
except Exception:  # pragma: no cover - fallback for test environment

    class FastMCPServer:  # type: ignore[misc]
        def __init__(self, name: str) -> None:  # noqa: D401
            self.name = name

        def register_tool(self, name: str, handler: Any) -> None:  # noqa: D401
            return

        async def run(self, **_: Any) -> None:  # noqa: D401
            return


from mcp_server import approval as approval_mod
from mcp_server import telemetry
from mcp_server.tool_adapters import (
    catalog_adapter,
    catalog_args_schema,
    command_args_schema,
    run_command_adapter,
)


# Phase 0: Server instructions/versioning
MCP_SERVER_INSTRUCTIONS_VERSION = "v0.1"
SERVER_INSTRUCTIONS = {
    "version": MCP_SERVER_INSTRUCTIONS_VERSION,
    "summary": (
        "Consolidated tools via method pattern; resources/prompts registered; "
        "approval gating and rate limiting enabled; telemetry spans emitted to logs/."
    ),
    "tools": {
        "ide_agents_command": {
            "schema": "command { method: run|dry_run|explain, command, cwd?, timeout?, payload? }",
        },
        "ide_agents_catalog": {
            "schema": "catalog { method: list_entities|get_doc, query? }",
        },
        "ide_agents_resource": {
            "schema": "resource { method: list|get, name? }",
        },
        "ide_agents_prompt": {
            "schema": "prompt { method: list|get, name? }",
        },
        "ide_agents_health": {
            "schema": "health {}",
        },
        "ide_agents_github_repos": {
            "schema": (
                "github_repos { visibility?: public|private, limit?: number, "
                "include?: string[], exclude?: string[], top?: number }"
            ),
        },
        "ide_agents_github_rank_repos": {
            "schema": (
                "github_rank_repos { query: string, visibility?: public|private, "
                "limit?: number, include?: string[], exclude?: string[], top?: number }"
            ),
        },
        "ide_agents_github_rank_all": {
            "schema": (
                "github_rank_all { query: string, visibility?: public|private, "
                "limit?: number, state?: open|closed, include?: string[], exclude?: string[], "
                "top?: number, items_per_repo?: number, page?: number }"
            ),
        },
    },
    "resources": ["repo.graph", "kb.snippet", "build.logs"],
    "prompts": ["/diff_review", "/test_failures", "/hotfix_plan"],
    # Extended prompts registered dynamically include ranking examples
}

logger = logging.getLogger("ide_agents.mcp")


@dataclass(slots=True)
class AgentsMCPConfig:
    """Runtime configuration for the IDE Agents MCP bridge."""

    backend_base_url: str = "http://127.0.0.1:8001"
    request_timeout: float = 30.0
    ultra_enabled: bool = False
    ultra_mock_enabled: bool = False
    ultra_config_path: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AgentsMCPConfig":
        """Initialize configuration from environment variables."""
        default_url = "http://127.0.0.1:8001"
        base_url = os.getenv("IDE_AGENTS_BACKEND_URL", default_url)
        timeout_env = os.getenv("IDE_AGENTS_REQUEST_TIMEOUT")
        ultra_enabled_env = os.getenv("IDE_AGENTS_ULTRA_ENABLED")
        ultra_mock_env = os.getenv("IDE_AGENTS_ULTRA_MOCK")
        ultra_config_path = os.getenv("IDE_AGENTS_ULTRA_CONFIG")

        timeout = cls.request_timeout
        if timeout_env:
            try:
                timeout = float(timeout_env)
            except ValueError:
                logger.warning(
                    "Invalid IDE_AGENTS_REQUEST_TIMEOUT value %s; using default",
                    timeout_env,
                )

        ultra_enabled = False
        if ultra_enabled_env:
            ultra_enabled = ultra_enabled_env.lower() in {"1", "true", "yes"}
        ultra_mock_enabled = False
        if ultra_mock_env:
            ultra_mock_enabled = ultra_mock_env.lower() in {"1", "true", "yes"}

        return cls(
            backend_base_url=base_url,
            request_timeout=timeout,
            ultra_enabled=ultra_enabled,
            ultra_mock_enabled=ultra_mock_enabled,
            ultra_config_path=ultra_config_path,
        )


class AgentsBackendClient:
    """Thin async HTTP client for the IDE Agents backend."""

    def __init__(self, config: AgentsMCPConfig) -> None:
        timeout = httpx.Timeout(config.request_timeout)
        self._client = httpx.AsyncClient(
            base_url=config.backend_base_url, timeout=timeout
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def run_command(
        self, command: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        response = await self._client.post(
            "/command", json={"command": command, "payload": payload or {}}
        )
        response.raise_for_status()
        return response.json()

    async def list_entities(self) -> List[Dict[str, Any]]:
        response = await self._client.get("/entities/mappings")
        response.raise_for_status()
        return response.json()

    async def fetch_documentation(self, topic: str) -> Dict[str, Any]:
        response = await self._client.get("/documentation", params={"topic": topic})
        response.raise_for_status()
        return response.json()

    async def ultra_rank(self, query: str, candidates: Iterable[str]) -> Dict[str, Any]:
        response = await self._client.post(
            "/ai/intelligence/rank",
            json={"query": query, "candidates": list(candidates)},
        )
        response.raise_for_status()
        return response.json()

    async def ultra_calibrate(self, scores: Iterable[float]) -> Dict[str, Any]:
        response = await self._client.post(
            "/ai/intelligence/calibrate",
            json={"scores": list(scores)},
        )
        response.raise_for_status()
        return response.json()


ToolHandler = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


class AgentsMCPServer:
    """FastMCP server wiring the IDE Agents backend into the MCP protocol."""

    def __init__(self, config: AgentsMCPConfig | None = None) -> None:
        self.config = config or AgentsMCPConfig.from_env()
        self.backend = AgentsBackendClient(self.config)
        self.server = FastMCPServer("ide-agents-mcp")
        self.tool_handlers: Dict[str, ToolHandler] = {}
        self._resources_dir = Path(__file__).parent / "resources"
        self._prompts_dir = Path(__file__).parent / "prompts"
        self._register_tools()

    def _register_tools(self) -> None:
        """Register tool handlers exposed via MCP."""

        self.tool_handlers = {
            "ide_agents_run_command": self._handle_run_command,
            "ide_agents_list_entities": self._handle_list_entities,
            "ide_agents_fetch_doc": self._handle_fetch_doc,
            # Consolidated tools (Phase 0)
            "ide_agents_command": self._handle_command_consolidated,
            "ide_agents_catalog": self._handle_catalog_consolidated,
            # Resources & prompts access (Phase 0)
            "ide_agents_resource": self._handle_resource,
            "ide_agents_prompt": self._handle_prompt,
            # Server instructions access (Phase 0)
            "ide_agents_server_instructions": self._handle_server_instructions,
            # Health/diagnostics
            "ide_agents_health": self._handle_health,
            # GitHub bridge
            "ide_agents_github_repos": self._handle_github_repos,
            "ide_agents_github_rank_repos": self._handle_github_rank_repos,
            "ide_agents_github_rank_all": self._handle_github_rank_all,
        }

        if self.config.ultra_enabled:
            self.tool_handlers.update(
                {
                    "ide_agents_ultra_rank": self._handle_ultra_rank,
                    "ide_agents_ultra_calibrate": self._handle_ultra_calibrate,
                }
            )

        # Register tools using FastMCP dynamic API when available, otherwise legacy API.
        srv_any: Any = self.server  # type: ignore[assignment]
        if hasattr(srv_any, "tool") or hasattr(srv_any, "add_tool"):
            for tool_name in list(self.tool_handlers.keys()):

                def _make_wrapper(name: str):
                    async def _wrapper(**kwargs: Any) -> Dict[str, Any]:
                        return await self._dispatch_tool_call(name, dict(kwargs))

                    return _wrapper

                wrapper_fn = _make_wrapper(tool_name)
                desc = self._describe_tool(tool_name)
                tool_deco = getattr(srv_any, "tool", None)
                add_tool_fn = getattr(srv_any, "add_tool", None)
                if callable(tool_deco):
                    decorated = tool_deco(
                        name=tool_name, title=tool_name, description=desc
                    )
                    if callable(decorated):
                        decorated(wrapper_fn)
                elif callable(add_tool_fn):
                    add_tool_fn(
                        wrapper_fn,
                        name=tool_name,
                        title=tool_name,
                        description=desc,
                    )
        else:
            for tool_name, handler in self.tool_handlers.items():

                async def wrapper(
                    arguments: Dict[str, Any], _h: ToolHandler = handler
                ) -> Dict[str, Any]:
                    return await _h(arguments)

                self.server.register_tool(tool_name, wrapper)

    async def _dispatch_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Simple rate limit per tool+method (allow list->get sequences)
        rl_key = (
            f"{name}:{arguments.get('method', '')}"
            if isinstance(arguments, dict)
            else name
        )
        if not approval_mod.rate_limiter.allow(rl_key):
            raise ValueError("rate_limited: please retry shortly")

        handler = self.tool_handlers.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool requested: {name}")

        # Telemetry span wrap
        start = asyncio.get_event_loop().time()
        method = arguments.get("method") if isinstance(arguments, dict) else None
        try:
            result = await handler(arguments)
            telemetry.emit_span(name, start_time=start, method=method, success=True)
            return result
        except Exception as exc:  # noqa: BLE001
            telemetry.emit_span(
                name,
                start_time=start,
                method=method,
                success=False,
                error_code=exc.__class__.__name__,
            )
            raise

    async def _handle_run_command(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        command = arguments.get("command")
        payload = arguments.get("payload")
        if not command:
            raise ValueError("Missing required argument: command")
        return await self.backend.run_command(command, payload)

    async def _handle_command_consolidated(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Approval gating for potentially mutating operations
        method = arguments.get("method")
        cmd = arguments.get("command", "")
        if method == "run":
            action_id = f"cmd:{cmd}"
            if not approval_mod.approval_queue.is_approved(
                "ide_agents_command", action_id
            ):
                approval_mod.approval_queue.request("ide_agents_command", action_id)
                payload = {
                    "approval_required": True,
                    "action_id": action_id,
                    "tool": "ide_agents_command",
                }
                raise ValueError(json.dumps(payload))
        return await run_command_adapter(self, arguments)

    async def _handle_list_entities(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        result = await self.backend.list_entities()
        return {"entities": result}

    async def _handle_fetch_doc(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        topic = arguments.get("topic")
        if not topic:
            raise ValueError("Missing required argument: topic")
        result = await self.backend.fetch_documentation(topic)
        return {"documentation": result}

    async def _handle_catalog_consolidated(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await catalog_adapter(self, arguments)

    async def _handle_resource(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        method = arguments.get("method", "list")
        if method == "list":
            items = [
                {
                    "name": "repo.graph",
                    "path": str(self._resources_dir / "repo.graph.json"),
                },
                {"name": "kb.snippet", "path": str(self._resources_dir / "kb.snippet")},
                {"name": "build.logs", "path": str(self._resources_dir / "build.logs")},
            ]
            return {"resources": items}
        if method == "get":
            name = arguments.get("name")
            if not name:
                raise ValueError("Missing required argument: name")
            if name == "repo.graph":
                p = self._resources_dir / "repo.graph.json"
                return {
                    "name": name,
                    "content": json.loads(p.read_text(encoding="utf-8")),
                }
            if name == "kb.snippet":
                p = self._resources_dir / "kb.snippet" / "README.md"
                return {"name": name, "content": p.read_text(encoding="utf-8")}
            if name == "build.logs":
                p = self._resources_dir / "build.logs"
                return {"name": name, "content": p.read_text(encoding="utf-8")}
            raise ValueError(f"Unknown resource: {name}")
        raise ValueError(f"Unsupported method for resource: {method}")

    async def _handle_prompt(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        method = arguments.get("method", "list")
        if method == "list":
            return {
                "prompts": [
                    "/diff_review",
                    "/test_failures",
                    "/hotfix_plan",
                    "/rank_github_repos",
                    "/rank_github_all",
                ]
            }
        if method == "get":
            name = arguments.get("name")
            if name not in {
                "/diff_review",
                "/test_failures",
                "/hotfix_plan",
                "/rank_github_repos",
                "/rank_github_all",
            }:
                raise ValueError("Unknown prompt name")
            file_map = {
                "/diff_review": self._prompts_dir / "diff_review.md",
                "/test_failures": self._prompts_dir / "test_failures.md",
                "/hotfix_plan": self._prompts_dir / "hotfix_plan.md",
                "/rank_github_repos": self._prompts_dir / "rank_github_repos.md",
                "/rank_github_all": self._prompts_dir / "rank_github_all.md",
            }
            p = file_map[name]
            return {"name": name, "content": p.read_text(encoding="utf-8")}
        raise ValueError(f"Unsupported method for prompt: {method}")

    async def _handle_server_instructions(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        return SERVER_INSTRUCTIONS

    async def _handle_health(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ok": True,
            "version": MCP_SERVER_INSTRUCTIONS_VERSION,
            "ultra_enabled": self.config.ultra_enabled,
        }

    async def _handle_ultra_rank(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        candidates = arguments.get("candidates")
        if not query or not candidates:
            raise ValueError("Both query and candidates are required for ULTRA ranking")
        result = await self.backend.ultra_rank(query, candidates)
        return {"ranking": result}

    async def _handle_ultra_calibrate(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        scores = arguments.get("scores")
        if scores is None:
            raise ValueError("Scores are required for ULTRA calibration")
        result = await self.backend.ultra_calibrate(scores)
        return {"calibration": result}

    async def _handle_github_repos(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            raise ValueError(
                "Missing GitHub token in env: set GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN"
            )
        visibility = arguments.get("visibility")
        if visibility not in (None, "public", "private"):
            raise ValueError("visibility must be one of: public, private")
        limit = arguments.get("limit", 25)
        try:
            limit = int(limit)
        except Exception:
            raise ValueError("limit must be a number")
        if limit <= 0:
            limit = 1
        if limit > 100:
            limit = 100
        include: List[str] = arguments.get("include") or []
        exclude: List[str] = arguments.get("exclude") or []
        top = arguments.get("top")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        params: Dict[str, Any] = {"per_page": 100}
        if visibility:
            params["visibility"] = visibility
        async with httpx.AsyncClient(base_url="https://api.github.com") as client:
            resp = await client.get("/user/repos", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
        items = []
        for repo in data:
            items.append(
                {
                    "name": repo.get("name"),
                    "full_name": repo.get("full_name"),
                    "private": bool(repo.get("private")),
                    "html_url": repo.get("html_url"),
                    "description": repo.get("description"),
                    "stargazers_count": repo.get("stargazers_count", 0),
                    "watchers_count": repo.get("watchers_count", 0),
                    "forks_count": repo.get("forks_count", 0),
                    "updated_at": repo.get("updated_at"),
                }
            )
        # Apply include/exclude filters
        if include:
            items = [i for i in items if i.get("name") in include or i.get("full_name") in include]
        if exclude:
            items = [
                i
                for i in items
                if i.get("name") not in exclude and i.get("full_name") not in exclude
            ]
        sliced = items[:limit]
        if top is not None:
            try:
                top_int = int(top)
            except Exception:
                top_int = None
            if top_int and top_int > 0:
                sliced = sliced[:top_int]
        return {"repos": sliced}

    async def _handle_github_rank_repos(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        start_ts = asyncio.get_event_loop().time()
        query = arguments.get("query")
        if not query:
            raise ValueError("Missing required argument: query")
        # Reuse fetch logic
        repos_result = await self._handle_github_repos(arguments)
        repos: List[Dict[str, Any]] = repos_result.get("repos", [])
        if not repos:
            return {"ranking": []}

        # ULTRA path: rank by semantic relevance using name + description
        if self.config.ultra_enabled:
            candidates: List[str] = []
            for r in repos:
                desc = r.get("description") or ""
                candidates.append(f"{r.get('full_name')}: {desc}")
            # Mock path
            if getattr(self.config, "ultra_mock_enabled", False):
                def mock_score(q: str, text: str) -> float:
                    q_words = {w for w in q.lower().split() if w}
                    t_words = {w for w in text.lower().split() if w}
                    inter = len(q_words & t_words)
                    return float(inter) / float(len(q_words) or 1)

                results = [
                    {"repo": repos[i], "score": mock_score(query, c)}
                    for i, c in enumerate(candidates)
                ]
                results.sort(key=lambda x: x["score"], reverse=True)
                telemetry.emit_span(
                    "ide_agents_github_rank_repos",
                    start_ts,
                    extra={
                        "mode": "ultra_mock",
                        "candidates": len(candidates),
                        "repos": len(repos),
                    },
                )
                return {"ranking": results}
            try:
                ranked = await self.backend.ultra_rank(query, candidates)
                # Expect a list of {index|candidate|score}. Normalize to include repo metadata.
                items_by_candidate = {c: repos[i] for i, c in enumerate(candidates)}
                collected: List[Dict[str, Any]] = []
                for entry in ranked.get(
                    "ranking", ranked if isinstance(ranked, list) else []
                ):
                    candidate = (
                        entry.get("candidate") if isinstance(entry, dict) else None
                    )
                    score = entry.get("score") if isinstance(entry, dict) else None
                    if candidate in items_by_candidate:
                        item = items_by_candidate[candidate]
                        collected.append({"repo": item, "score": score})
                if collected:
                    telemetry.emit_span(
                        "ide_agents_github_rank_repos",
                        start_ts,
                        extra={
                            "mode": "ultra_backend",
                            "candidates": len(candidates),
                            "repos": len(repos),
                        },
                    )
                    return {"ranking": collected}
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "ULTRA ranking failed, using heuristic fallback: %s", exc
                )

        # Heuristic fallback: stars, recent update, description match
        def heuristic_score(r: Dict[str, Any]) -> float:
            stars = int(r.get("stargazers_count", 0) or 0)
            forks = int(r.get("forks_count", 0) or 0)
            desc = (r.get("description") or "").lower()
            q = str(query).lower()
            match = (
                1.0
                if q and (q in desc or q in str(r.get("full_name", "")).lower())
                else 0.0
            )
            # simple combo: stars weight 1.0, forks 0.3, match 5.0
            return stars * 1.0 + forks * 0.3 + match * 5.0

        ranked_repos = sorted(repos, key=heuristic_score, reverse=True)
        top = arguments.get("top")
        if top is not None:
            try:
                top_int = int(top)
                if top_int > 0:
                    ranked_repos = ranked_repos[:top_int]
            except Exception:
                pass
        telemetry.emit_span(
            "ide_agents_github_rank_repos",
            start_ts,
            extra={
                "mode": "heuristic",
                "repos": len(repos),
            },
        )
        return {"ranking": [{"repo": r, "score": heuristic_score(r)} for r in ranked_repos]}

    async def _handle_github_rank_all(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        start_ts = asyncio.get_event_loop().time()
        query = arguments.get("query")
        if not query:
            raise ValueError("Missing required argument: query")

        # Get base repos (respect visibility/limit/include/exclude/top on repos first)
        repos_result = await self._handle_github_repos(arguments)
        repos: List[Dict[str, Any]] = repos_result.get("repos", [])

        token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            raise ValueError(
                "Missing GitHub token in env: set GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN"
            )
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        # Collect issues/PRs across a subset of repos to avoid rate explosion
        state_filter = arguments.get("state")
        if state_filter not in (None, "open", "closed"):
            raise ValueError("state must be one of: open, closed")
        items_per_repo = arguments.get("items_per_repo", 30)
        page = arguments.get("page", 1)
        try:
            items_per_repo = int(items_per_repo)
        except Exception:
            items_per_repo = 30
        items_per_repo = max(1, min(items_per_repo, 50))
        try:
            page = int(page)
        except Exception:
            page = 1
        page = max(1, page)
        max_repos = min(len(repos), 5)
        max_items_total = 50
        agg_items: List[Dict[str, Any]] = []

        async def fetch_repo_issues(r: Dict[str, Any]) -> List[Dict[str, Any]]:
            full = r.get("full_name")
            if not full:
                return []
            params = {"state": state_filter or "open", "per_page": items_per_repo, "page": page}
            try:
                async with httpx.AsyncClient(base_url="https://api.github.com") as client:
                    resp = await client.get(
                        f"/repos/{full}/issues", headers=headers, params=params
                    )
                    resp.raise_for_status()
                    rows = resp.json()
            except Exception:
                return []
            converted: List[Dict[str, Any]] = []
            for it in rows:
                is_pr = "pull_request" in it
                kind = "pr" if is_pr else "issue"
                converted.append(
                    {
                        "type": kind,
                        "repo": r,
                        kind: {
                            "number": it.get("number"),
                            "title": it.get("title"),
                            "body": it.get("body"),
                            "html_url": it.get("html_url"),
                            "comments": it.get("comments", 0),
                            "state": it.get("state"),
                            "updated_at": it.get("updated_at"),
                        },
                    }
                )
            return converted

        # Parallel fetch
        tasks = [fetch_repo_issues(r) for r in repos[:max_repos]]
        results = await asyncio.gather(*tasks)
        for batch in results:
            for it in batch:
                agg_items.append(it)
                if len(agg_items) >= max_items_total:
                    break
            if len(agg_items) >= max_items_total:
                break

        # Build candidates for ULTRA if enabled
        if self.config.ultra_enabled:
            candidates: List[str] = []
            candidate_map: Dict[str, Dict[str, Any]] = {}
            for r in repos:
                text = f"repo {r.get('full_name')}: {r.get('description') or ''}"
                candidates.append(text)
                candidate_map[text] = {"type": "repo", "repo": r}
            for item in agg_items:
                r = item["repo"]
                if item["type"] == "issue":
                    iss = item["issue"]
                    text = (
                        f"issue {r.get('full_name')} #{iss.get('number')}: "
                        f"{iss.get('title') or ''} {iss.get('body') or ''}"
                    )
                else:
                    pr = item["pr"]
                    text = (
                        f"pr {r.get('full_name')} #{pr.get('number')}: "
                        f"{pr.get('title') or ''} {pr.get('body') or ''}"
                    )
                candidates.append(text)
                candidate_map[text] = item
            if getattr(self.config, "ultra_mock_enabled", False):
                def mock_score(q: str, text: str) -> float:
                    q_words = {w for w in q.lower().split() if w}
                    t_words = {w for w in text.lower().split() if w}
                    inter = len(q_words & t_words)
                    return float(inter) / float(len(q_words) or 1)

                scored: List[Dict[str, Any]] = []
                for cand in candidates:
                    item = candidate_map[cand]
                    sc = mock_score(query, cand)
                    out = {"type": item["type"], "score": sc, "norm_score": sc * 10.0}
                    if item["type"] == "repo":
                        out["repo"] = item["repo"]
                    elif item["type"] == "issue":
                        out["repo"] = item["repo"]
                        out["issue"] = item["issue"]
                    else:
                        out["repo"] = item["repo"]
                        out["pr"] = item["pr"]
                    scored.append(out)
                scored.sort(key=lambda x: x["norm_score"], reverse=True)
                telemetry.emit_span(
                    "ide_agents_github_rank_all",
                    start_ts,
                    extra={
                        "mode": "ultra_mock",
                        "candidates": len(candidates),
                        "repos": len(repos),
                        "items": len(agg_items),
                    },
                )
                top = arguments.get("top")
                if top is not None:
                    try:
                        top_int = int(top)
                        if top_int > 0:
                            scored = scored[:top_int]
                    except Exception:
                        pass
                return {"ranking": scored}
            try:
                ranked = await self.backend.ultra_rank(query, candidates)
                raw_entries = ranked.get(
                    "ranking", ranked if isinstance(ranked, list) else []
                )
                scores: List[float] = []
                for entry in raw_entries:
                    cand = entry.get("candidate") if isinstance(entry, dict) else None
                    score = entry.get("score") if isinstance(entry, dict) else None
                    if cand in candidate_map and isinstance(score, (int, float)):
                        scores.append(float(score))
                # Normalize scores 0..10
                norm_results: List[Dict[str, Any]] = []
                smin = min(scores) if scores else 0.0
                smax = max(scores) if scores else 1.0
                denom = (smax - smin) or 1.0
                for entry in raw_entries:
                    cand = entry.get("candidate") if isinstance(entry, dict) else None
                    score = (
                        float(entry.get("score"))
                        if isinstance(entry, dict)
                        and isinstance(entry.get("score"), (int, float))
                        else None
                    )
                    if cand in candidate_map and score is not None:
                        item = candidate_map[cand]
                        norm = (score - smin) / denom * 10.0
                        out = {"type": item["type"], "score": score, "norm_score": norm}
                        if item["type"] == "repo":
                            out["repo"] = item["repo"]
                        elif item["type"] == "issue":
                            out["repo"] = item["repo"]
                            out["issue"] = item["issue"]
                        else:
                            out["repo"] = item["repo"]
                            out["pr"] = item["pr"]
                        norm_results.append(out)
                if norm_results:
                    telemetry.emit_span(
                        "ide_agents_github_rank_all",
                        start_ts,
                        extra={
                            "mode": "ultra_backend",
                            "candidates": len(candidates),
                            "repos": len(repos),
                            "items": len(agg_items),
                        },
                    )
                    return {"ranking": norm_results}
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "ULTRA ranking failed in rank_all, using heuristic fallback: %s",
                    exc,
                )

        # Heuristic fallback: score repos + issues + PRs, normalize 0..10
        def parse_dt(s: Optional[str]) -> Optional[datetime]:
            try:
                return datetime.strptime(str(s), "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
            except Exception:
                return None

        def repo_score(r: Dict[str, Any]) -> float:
            stars = int(r.get("stargazers_count", 0) or 0)
            forks = int(r.get("forks_count", 0) or 0)
            desc = (r.get("description") or "").lower()
            q = str(query).lower()
            match = (
                1.0
                if q and (q in desc or q in str(r.get("full_name", "")).lower())
                else 0.0
            )
            return stars * 1.0 + forks * 0.3 + match * 5.0

        def issue_like_score(it: Dict[str, Any], is_pr: bool) -> float:
            q = str(query).lower()
            title = (it.get("title") or "").lower()
            body = (it.get("body") or "").lower()
            comments = int(it.get("comments", 0) or 0)
            updated = parse_dt(it.get("updated_at"))
            recency = 0.0
            if updated is not None:
                age_days = (
                    datetime.now(timezone.utc) - updated
                ).total_seconds() / 86400.0
                recency = max(
                    0.0, (30.0 - age_days) / 30.0
                )  # 0..1 if within last 30 days
            match = 1.0 if (q in title or q in body) else 0.0
            base = (
                comments * (0.3 if is_pr else 0.2)
                + match * 5.0
                + recency * (3.0 if is_pr else 2.0)
            )
            if is_pr:
                base += 1.0
            return base

        scored: List[Dict[str, Any]] = []
        for r in repos:
            scored.append({"type": "repo", "repo": r, "score": repo_score(r)})
        for item in agg_items:
            if item["type"] == "issue":
                s = issue_like_score(item["issue"], False)
                scored.append(
                    {
                        "type": "issue",
                        "repo": item["repo"],
                        "issue": item["issue"],
                        "score": s,
                    }
                )
            else:
                s = issue_like_score(item["pr"], True)
                scored.append(
                    {"type": "pr", "repo": item["repo"], "pr": item["pr"], "score": s}
                )

        svals = [x["score"] for x in scored] or [0.0]
        smin, smax = min(svals), max(svals)
        denom = (smax - smin) or 1.0
        for x in scored:
            x["norm_score"] = (x["score"] - smin) / denom * 10.0
        scored.sort(key=lambda x: x["norm_score"], reverse=True)
        top = arguments.get("top")
        if top is not None:
            try:
                top_int = int(top)
                if top_int > 0:
                    scored = scored[:top_int]
            except Exception:
                pass
        telemetry.emit_span(
            "ide_agents_github_rank_all",
            start_ts,
            extra={
                "mode": "heuristic",
                "repos": len(repos),
                "items": len(agg_items),
            },
        )
        return {"ranking": scored}

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Expose tool metadata for MCP discovery."""

        tools = []
        for name in self.tool_handlers:
            tools.append(
                {
                    "name": name,
                    "description": self._describe_tool(name),
                    "input_schema": self._tool_input_schema(name),
                }
            )
        return tools

    def _describe_tool(self, name: str) -> str:
        descriptions = {
            "ide_agents_run_command": "Execute a backend command with optional payload.",
            "ide_agents_list_entities": "List entity mappings known to the IDE agents backend.",
            "ide_agents_fetch_doc": "Fetch documentation snippets for a requested topic.",
            "ide_agents_ultra_rank": "Run ULTRA semantic ranking over provided candidates.",
            "ide_agents_ultra_calibrate": "Calibrate confidence scores using ULTRA pipeline.",
            "ide_agents_command": "Consolidated command tool supporting run|dry_run|explain.",
            "ide_agents_catalog": "Consolidated catalog tool for list_entities|get_doc.",
            "ide_agents_resource": "Access registered read-only resources (list|get).",
            "ide_agents_prompt": "List/get registered slash prompts for workflows.",
            "ide_agents_server_instructions": "Return server instructions and version.",
            "ide_agents_health": "Quick diagnostics returning ok, version, and flags.",
            "ide_agents_github_repos": (
                "List your GitHub repositories (public/private) with basic fields."
            ),
            "ide_agents_github_rank_repos": (
                "Rank your GitHub repositories by semantic relevance (ULTRA) or heuristic fallback."
            ),
            "ide_agents_github_rank_all": (
                "Aggregate ranking over repositories (future: issues/PRs) via ULTRA or "
                "heuristic fallback."
            ),
            # New prompts will reference ranking examples
        }
        return descriptions.get(name, "IDE Agents MCP tool")

    def _tool_input_schema(self, name: str) -> Dict[str, Any]:
        schemas: Dict[str, Dict[str, Any]] = {
            "ide_agents_run_command": {
                "type": "object",
                "required": ["command"],
                "properties": {
                    "command": {"type": "string"},
                    "payload": {"type": "object"},
                },
            },
            "ide_agents_list_entities": {"type": "object", "properties": {}},
            "ide_agents_fetch_doc": {
                "type": "object",
                "required": ["topic"],
                "properties": {"topic": {"type": "string"}},
            },
            "ide_agents_ultra_rank": {
                "type": "object",
                "required": ["query", "candidates"],
                "properties": {
                    "query": {"type": "string"},
                    "candidates": {"type": "array", "items": {"type": "string"}},
                },
            },
            "ide_agents_ultra_calibrate": {
                "type": "object",
                "required": ["scores"],
                "properties": {
                    "scores": {"type": "array", "items": {"type": "number"}},
                },
            },
            # Consolidated tools
            "ide_agents_command": command_args_schema(),
            "ide_agents_catalog": catalog_args_schema(),
            # Resources/prompts/instructions
            "ide_agents_resource": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["list", "get"]},
                    "name": {"type": "string"},
                },
            },
            "ide_agents_prompt": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["list", "get"]},
                    "name": {"type": "string"},
                },
            },
            "ide_agents_server_instructions": {"type": "object", "properties": {}},
            "ide_agents_health": {"type": "object", "properties": {}},
            "ide_agents_github_repos": {
                "type": "object",
                "properties": {
                    "visibility": {"type": "string", "enum": ["public", "private"]},
                    "limit": {"type": "number"},
                    "include": {"type": "array", "items": {"type": "string"}},
                    "exclude": {"type": "array", "items": {"type": "string"}},
                    "top": {"type": "number"},
                },
            },
            "ide_agents_github_rank_repos": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "visibility": {"type": "string", "enum": ["public", "private"]},
                    "limit": {"type": "number"},
                    "include": {"type": "array", "items": {"type": "string"}},
                    "exclude": {"type": "array", "items": {"type": "string"}},
                    "top": {"type": "number"},
                },
            },
            "ide_agents_github_rank_all": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "visibility": {"type": "string", "enum": ["public", "private"]},
                    "limit": {"type": "number"},
                    "state": {"type": "string", "enum": ["open", "closed"]},
                    "include": {"type": "array", "items": {"type": "string"}},
                    "exclude": {"type": "array", "items": {"type": "string"}},
                    "top": {"type": "number"},
                    "items_per_repo": {"type": "number"},
                    "page": {"type": "number"},
                },
            },
        }
        return schemas.get(name, {"type": "object"})

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self._dispatch_tool_call(name, arguments)

    async def shutdown(self) -> None:
        await self.backend.close()


def main() -> None:
    """Synchronous entry point.

    FastMCPServer.run() manages its own event loop (anyio.run). Wrapping it
    in asyncio.run or awaiting it caused a nested loop RuntimeError. We call
    it directly and then perform async shutdown in a fresh loop.
    """
    config = AgentsMCPConfig.from_env()
    server = AgentsMCPServer(config)

    import sys as _sys

    _sys.stderr.write(
        f"[ide-agents-mcp] Initialized (instructions {MCP_SERVER_INSTRUCTIONS_VERSION})\n"
    )

    try:
        server.server.run()  # synchronous; starts stdio processing
    finally:
        try:
            asyncio.run(server.shutdown())
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    main()
