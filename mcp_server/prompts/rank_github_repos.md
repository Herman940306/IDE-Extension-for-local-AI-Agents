# /rank_github_repos

Goal: Rank my GitHub repositories by relevance to a query.

Usage:
- Tool: `ide_agents_github_rank_repos`
- Args:
  - `query` (string): what you’re looking for (e.g., "ai agents")
  - `visibility` (public|private, optional)
  - `limit` (number, optional): repos fetched (max 100)
  - `include`/`exclude` (string[], optional): repo names or full_names
  - `top` (number, optional): return top-N results after ranking

Example:
```
/ask ide_agents_github_rank_repos {
  "query": "ai agents",
  "visibility": "public",
  "limit": 50,
  "top": 10
}
```

Notes:
- If ULTRA is enabled, semantic ranking is applied. Otherwise a heuristic fallback is used.
- Set `IDE_AGENTS_ULTRA_ENABLED=1` (and optionally `IDE_AGENTS_ULTRA_MOCK=1`) before invoking.
