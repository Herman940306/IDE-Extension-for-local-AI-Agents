# MCP Changelog

## [Phase 0] Foundations (v0.1)

- mcp-phase0: add server instructions and version (v0.1) with consolidated tool schemas
- mcp-phase0: add consolidated tools `ide_agents.command` and `ide_agents.catalog`
- mcp-phase0: add resources (`repo.graph`, `kb.snippet`, `build.logs`) and prompts (`/diff_review`, `/test_failures`, `/hotfix_plan`)
- mcp-phase0: add telemetry spans to `logs/mcp_tool_spans.jsonl`
- mcp-phase0: add simple approval gating and per-tool rate limiting
- mcp-phase0: add SSE streaming scaffold at `/_mcp/stream_test`
- mcp-phase0: add tests for instructions, tools, streaming, approval, telemetry
