import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_server.ide_agents_mcp_server import (  # noqa: E402
    AgentsMCPServer,
    MCP_SERVER_INSTRUCTIONS_VERSION,
)
from mcp_server import streaming  # noqa: E402


@pytest.mark.asyncio
async def test_server_instructions_version_available():
    server = AgentsMCPServer()
    resp = await server.call_tool("ide_agents.server_instructions", {})
    assert resp["version"] == MCP_SERVER_INSTRUCTIONS_VERSION


@pytest.mark.asyncio
async def test_consolidated_command_explain_and_telemetry(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MCP_TOOL_SPANS_DIR", str(tmp_path))
    server = AgentsMCPServer()
    out = await server.call_tool(
        "ide_agents.command",
        {"method": "explain", "command": "echo hello", "payload": {"k": 1}},
    )
    assert "explanation" in out
    # Check telemetry file exists with at least one span
    log_file = tmp_path / "mcp_tool_spans.jsonl"
    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    span = json.loads(lines[-1])
    assert span["tool_name"] == "ide_agents.command"


@pytest.mark.asyncio
async def test_resource_list_and_get():
    server = AgentsMCPServer()
    listed = await server.call_tool("ide_agents.resource", {"method": "list"})
    names = [r["name"] for r in listed["resources"]]
    assert "repo.graph" in names
    got = await server.call_tool(
        "ide_agents.resource", {"method": "get", "name": "repo.graph"}
    )
    assert "content" in got and isinstance(got["content"], dict)


@pytest.mark.asyncio
async def test_prompt_list_and_get():
    server = AgentsMCPServer()
    listed = await server.call_tool("ide_agents.prompt", {"method": "list"})
    assert "/diff_review" in listed["prompts"]
    got = await server.call_tool(
        "ide_agents.prompt", {"method": "get", "name": "/diff_review"}
    )
    assert got["name"] == "/diff_review" and isinstance(got["content"], str)


@pytest.mark.asyncio
async def test_approval_gating_blocks_run(monkeypatch):
    server = AgentsMCPServer()
    with pytest.raises(Exception) as ei:
        await server.call_tool(
            "ide_agents.command", {"method": "run", "command": "touch x"}
        )
    msg = str(ei.value)
    assert "approval_required" in msg


def test_streaming_server_emits_events():
    srv, thread = streaming.start_server()
    try:
        import requests

        with requests.get(
            "http://127.0.0.1:8765/_mcp/stream_test", stream=True, timeout=5
        ) as r:
            assert r.status_code == 200
            chunks = []
            for chunk in r.iter_lines():
                if chunk:
                    chunks.append(chunk)
                if len(chunks) >= 3:
                    break
            assert len(chunks) >= 3
    finally:
        streaming.stop_server(srv)
