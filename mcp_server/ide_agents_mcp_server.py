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
        "ide_agents.command": {
            "schema": "command { method: run|dry_run|explain, command, cwd?, timeout?, payload? }",
        },
        "ide_agents.catalog": {
            "schema": "catalog { method: list_entities|get_doc, query? }",
        },
        "ide_agents.resource": {
            "schema": "resource { method: list|get, name? }",
        },
        "ide_agents.prompt": {
            "schema": "prompt { method: list|get, name? }",
        },
    },
    "resources": ["repo.graph", "kb.snippet", "build.logs"],
    "prompts": ["/diff_review", "/test_failures", "/hotfix_plan"],
}

logger = logging.getLogger("ide_agents.mcp")


@dataclass(slots=True)
class AgentsMCPConfig:
    """Runtime configuration for the IDE Agents MCP bridge."""

    backend_base_url: str = "http://127.0.0.1:8001"
    request_timeout: float = 30.0
    ultra_enabled: bool = False
    ultra_config_path: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AgentsMCPConfig":
        """Initialize configuration from environment variables."""
        default_url = "http://127.0.0.1:8001"
        base_url = os.getenv("IDE_AGENTS_BACKEND_URL", default_url)
        timeout_env = os.getenv("IDE_AGENTS_REQUEST_TIMEOUT")
        ultra_enabled_env = os.getenv("IDE_AGENTS_ULTRA_ENABLED")
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

        return cls(
            backend_base_url=base_url,
            request_timeout=timeout,
            ultra_enabled=ultra_enabled,
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
            "ide_agents.run_command": self._handle_run_command,
            "ide_agents.list_entities": self._handle_list_entities,
            "ide_agents.fetch_doc": self._handle_fetch_doc,
            # Consolidated tools (Phase 0)
            "ide_agents.command": self._handle_command_consolidated,
            "ide_agents.catalog": self._handle_catalog_consolidated,
            # Resources & prompts access (Phase 0)
            "ide_agents.resource": self._handle_resource,
            "ide_agents.prompt": self._handle_prompt,
            # Server instructions access (Phase 0)
            "ide_agents.server_instructions": self._handle_server_instructions,
        }

        if self.config.ultra_enabled:
            self.tool_handlers.update(
                {
                    "ide_agents.ultra.rank": self._handle_ultra_rank,
                    "ide_agents.ultra.calibrate": self._handle_ultra_calibrate,
                }
            )

        # Register tools using fallback API (register_tool). FastMCP dynamic API disabled.
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
                "ide_agents.command", action_id
            ):
                approval_mod.approval_queue.request("ide_agents.command", action_id)
                payload = {
                    "approval_required": True,
                    "action_id": action_id,
                    "tool": "ide_agents.command",
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
            return {"prompts": ["/diff_review", "/test_failures", "/hotfix_plan"]}
        if method == "get":
            name = arguments.get("name")
            if name not in {"/diff_review", "/test_failures", "/hotfix_plan"}:
                raise ValueError("Unknown prompt name")
            file_map = {
                "/diff_review": self._prompts_dir / "diff_review.md",
                "/test_failures": self._prompts_dir / "test_failures.md",
                "/hotfix_plan": self._prompts_dir / "hotfix_plan.md",
            }
            p = file_map[name]
            return {"name": name, "content": p.read_text(encoding="utf-8")}
        raise ValueError(f"Unsupported method for prompt: {method}")

    async def _handle_server_instructions(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        return SERVER_INSTRUCTIONS

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
            "ide_agents.run_command": "Execute a backend command with optional payload.",
            "ide_agents.list_entities": "List entity mappings known to the IDE agents backend.",
            "ide_agents.fetch_doc": "Fetch documentation snippets for a requested topic.",
            "ide_agents.ultra.rank": "Run ULTRA semantic ranking over provided candidates.",
            "ide_agents.ultra.calibrate": "Calibrate confidence scores using ULTRA pipeline.",
            "ide_agents.command": "Consolidated command tool supporting run|dry_run|explain.",
            "ide_agents.catalog": "Consolidated catalog tool for list_entities|get_doc.",
            "ide_agents.resource": "Access registered read-only resources (list|get).",
            "ide_agents.prompt": "List/get registered slash prompts for workflows.",
            "ide_agents.server_instructions": "Return server instructions and version.",
        }
        return descriptions.get(name, "IDE Agents MCP tool")

    def _tool_input_schema(self, name: str) -> Dict[str, Any]:
        schemas: Dict[str, Dict[str, Any]] = {
            "ide_agents.run_command": {
                "type": "object",
                "required": ["command"],
                "properties": {
                    "command": {"type": "string"},
                    "payload": {"type": "object"},
                },
            },
            "ide_agents.list_entities": {"type": "object", "properties": {}},
            "ide_agents.fetch_doc": {
                "type": "object",
                "required": ["topic"],
                "properties": {"topic": {"type": "string"}},
            },
            "ide_agents.ultra.rank": {
                "type": "object",
                "required": ["query", "candidates"],
                "properties": {
                    "query": {"type": "string"},
                    "candidates": {"type": "array", "items": {"type": "string"}},
                },
            },
            "ide_agents.ultra.calibrate": {
                "type": "object",
                "required": ["scores"],
                "properties": {
                    "scores": {"type": "array", "items": {"type": "number"}},
                },
            },
            # Consolidated tools
            "ide_agents.command": command_args_schema(),
            "ide_agents.catalog": catalog_args_schema(),
            # Resources/prompts/instructions
            "ide_agents.resource": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["list", "get"]},
                    "name": {"type": "string"},
                },
            },
            "ide_agents.prompt": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["list", "get"]},
                    "name": {"type": "string"},
                },
            },
            "ide_agents.server_instructions": {"type": "object", "properties": {}},
        }
        return schemas.get(name, {"type": "object"})

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self._dispatch_tool_call(name, arguments)

    async def shutdown(self) -> None:
        await self.backend.close()


async def main() -> None:
    """Entry point used by MCP launcher."""
    config = AgentsMCPConfig.from_env()
    server = AgentsMCPServer(config)

    # NOTE: Do not emit any non-protocol bytes on stdout before FastMCPServer.run.

    # Emit startup banner to stderr so MCP stdio protocol isn't polluted
    # Moved banner earlier; keep a debug note on stderr only.
    import sys as _sys

    _sys.stderr.write(
        f"[ide-agents-mcp] Initialized (instructions {MCP_SERVER_INSTRUCTIONS_VERSION})\n"
    )

    try:
        await server.server.run()
    finally:
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
