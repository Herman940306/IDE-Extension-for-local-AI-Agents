# mcp-phase0: foundations — server instructions, consolidated tools, streaming, approvals, telemetry

## Summary
Implements Phase 0 (Foundations) per IDE Agents MCP roadmap. Adds server instructions/versioning, consolidated `method` tools, resources/prompts, SSE streaming scaffold, approval gating + rate limits, and telemetry spans with focused tests.

## Tree-of-Thoughts Candidate Plans
- Plan A (Minimal shim):
  - Add consolidated wrappers in existing server file; stub resources/prompts; basic telemetry wrapper.
  - Risk: server file grows; moderate coupling. Tests: low surface area.
- Plan B (Modular split, no HTTP):
  - Create separate modules: telemetry.py, approval.py, tool_adapters.py; extend server to wire them; emulate resources/prompts via tools.
  - Risk: low; clear seams; fast rollback. Tests: straightforward unit tests.
- Plan C (Introduce FastAPI for streaming):
  - Add FastAPI + uvicorn for SSE; register lifecycle. Broader deps.
  - Risk: dependency/port conflicts; slower CI. Tests: async HTTP.
- Plan D (Spec-perfect MCP Resources/Prompts):
  - Implement MCP-native resources/prompts APIs; requires SDK parity.
  - Risk: SDK API mismatch; higher time. Tests: client harness.
- Plan E (Backend-proxy only):
  - Proxy all new features to backend; no local scaffolding.
  - Risk: backend coupling; brittle in offline dev.

ULTRA-ranking (safety, velocity, test pass probability, rollback):
- Rank 1: Plan B (selected) — modular, low risk, fast tests, small blast radius.
- Rank 2: Plan A — simplest but mixes concerns.
- Rank 3: Plan D — ideal spec but risky without SDK parity.
- Rank 4: Plan C — overkill for Phase 0.
- Rank 5: Plan E — couples to backend unnecessarily.

## Self-Consistency: Implementation Variants Considered
- Variant 1 (Minimal): only wrappers + inline telemetry in server; no modules.
- Variant 2 (Pragmatic) [Selected]: split small modules (telemetry, approval, adapters); emulate resources/prompts; fallback FastMCPServer for tests.
- Variant 3 (Comprehensive): full MCP resources/prompts, FastAPI SSE server, config service, persisted approvals.

## Changes
- mcp_server/ide_agents_mcp_server.py — server instructions, consolidated tools, resources/prompts, approval/rate-limit, telemetry wrap, startup version print, fallback FastMCPServer.
- mcp_server/tool_adapters.py — `command` and `catalog` adapters and schemas.
- mcp_server/telemetry.py — JSONL span writer to `logs/mcp_tool_spans.jsonl`.
- mcp_server/approval.py — in-memory approval queue and simple rate limiter.
- mcp_server/streaming.py — SSE-like endpoint at `/_mcp/stream_test` using stdlib HTTP.
- mcp_server/resources/* — repo.graph.json, kb.snippet/README.md, build.logs placeholders.
- mcp_server/prompts/* — /diff_review, /test_failures, /hotfix_plan.
- mcp_server/__init__.py — package init.
- mcp_server/requirements.txt — add httpx/requests for tests.
- tests/test_mcp_phase0.py — focused tests covering acceptance criteria.
- docs/CHANGELOG_MCP.md — entries for Phase 0.
- mcp_server/README.md — usage snippet for consolidated schema and instructions.

## How to Run Locally
```bash
# In repo root (venv active)
pip install -r mcp_server/requirements.txt
pytest -q tests/test_mcp_phase0.py
```

## Acceptance Criteria Checklist
- [x] Server starts and prints server instructions version (v0.1)
- [x] Consolidated tools reachable; `command(method=explain)` test passes
- [x] Streaming POC at `/_mcp/stream_test` emits incremental messages
- [x] Approval gating blocks write-like `command(method=run)` until approved
- [x] Telemetry spans written to `logs/mcp_tool_spans.jsonl`
- [x] Resources and prompts list/get work

## Security & Safety
- No secrets added
- Approval required for `command(method=run)` operations
- Simple per-tool+method rate limiting (throttles bursts)

## Rollout & Rollback
- Feature branch only; minimal surface
- Rollback by reverting this branch; modules are self-contained

## Reasoning Log (concise)
- ToT Plans: A/B/C/D/E; B selected for modularity and low risk
- Self-consistency: minimal vs pragmatic vs comprehensive; pragmatic selected
- Kept SSE via stdlib to avoid heavy deps; added FastMCP fallback for tests

## Request for Approval
Please add label `approve-mcp-phase0` to approve merging after review.
