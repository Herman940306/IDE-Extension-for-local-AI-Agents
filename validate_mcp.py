from __future__ import annotations
import asyncio
import os
import json
from mcp_server.ide_agents_mcp_server import AgentsMCPServer, AgentsMCPConfig
import argparse
import httpx


async def validate_ide_agents(
    query: str,
    visibility: str | None,
    limit: int,
    use_all: bool,
    ultra: bool,
    state: str | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    top: int | None = None,
    since: str | None = None,
    items_per_repo: int | None = None,
) -> dict:
    if ultra:
        os.environ["IDE_AGENTS_ULTRA_ENABLED"] = "1"
    cfg = AgentsMCPConfig.from_env()
    server = AgentsMCPServer(cfg)
    # Call internal handlers directly
    health = await server._handle_health({})  # type: ignore[attr-defined]
    tools = await server.list_tools()
    ranking_sample = None
    # Attempt ranking sample if github token present
    if os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
        try:
            tool_name = (
                "ide_agents_github_rank_all"
                if use_all
                else "ide_agents_github_rank_repos"
            )
            args: dict[str, object] = {"query": query, "limit": limit}
            if visibility:
                args["visibility"] = visibility
            if state:
                args["state"] = state
            if include:
                args["include"] = include
            if exclude:
                args["exclude"] = exclude
            if top is not None:
                args["top"] = top
            if since:
                args["since"] = since
            if items_per_repo is not None:
                args["items_per_repo"] = items_per_repo
            ranking_sample = await server.call_tool(tool_name, args)
        except Exception as exc:  # noqa: BLE001
            ranking_sample = {"error": str(exc)}
    await server.shutdown()
    return {
        "health": health,
        "tool_count": len(tools),
        "tool_names": [t["name"] for t in tools],
        "ranking_sample": ranking_sample,
        "ultra_enabled_requested": ultra,
    }


async def validate_github_pat() -> dict:
    pat = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not pat:
        return {"error": "PAT missing in env"}
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient(base_url="https://api.github.com") as client:
        r_user = await client.get("/user", headers=headers)
        info: dict[str, object] = {"status": r_user.status_code}
        if r_user.status_code == 200:
            data = r_user.json()
            info.update(
                {
                    "login": data.get("login"),
                    "id": data.get("id"),
                    "public_repos": data.get("public_repos"),
                }
            )
        else:
            info["body"] = r_user.text[:300]
    return info


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="ai agents", help="Ranking query text")
    parser.add_argument("--visibility", choices=["public", "private"], default=None)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--all", action="store_true", dest="rank_all", help="Use rank_all aggregation"
    )
    parser.add_argument(
        "--ultra", action="store_true", help="Enable ULTRA path for semantic ranking"
    )
    parser.add_argument("--state", choices=["open", "closed"], default=None)
    parser.add_argument(
        "--include", nargs="*", default=None, help="Restrict to listed repo names"
    )
    parser.add_argument(
        "--exclude", nargs="*", default=None, help="Exclude listed repo names"
    )
    parser.add_argument(
        "--top", type=int, default=None, help="Return only top N results after ranking"
    )
    parser.add_argument(
        "--since",
        default=None,
        help="ISO8601 timestamp to filter issues/PRs updated since (e.g., 2025-10-01T00:00:00Z)",
    )
    parser.add_argument(
        "--items_per_repo",
        type=int,
        default=None,
        help="Number of issues/PRs to fetch per repo (rank_all)",
    )
    args = parser.parse_args()

    # For script demonstration we only wire basic params to internal call
    ide = await validate_ide_agents(
        args.query,
        args.visibility,
        args.limit,
        args.rank_all,
        args.ultra,
        state=args.state,
        include=args.include,
        exclude=args.exclude,
        top=args.top,
        since=args.since,
        items_per_repo=args.items_per_repo,
    )
    gh = await validate_github_pat()
    print(json.dumps({"ide_agents": ide, "github_pat": gh}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
