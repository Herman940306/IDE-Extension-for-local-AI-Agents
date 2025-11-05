# GitHub MCP Server — VS Code Integration and Quick Commands

This guide integrates GitHub’s official MCP Server with your workspace to give Copilot Agent Mode rich GitHub context and actions (repos, issues, PRs, Actions, security, and more).

## Overview
 
- Server repo: <https://github.com/github/github-mcp-server>
- Recommended install: Docker-based local server (no Go toolchain needed)
- Auth: GitHub Personal Access Token (fine‑grained PAT recommended)
- VS Code: Copilot Chat Agent Mode must be enabled (VS Code 1.101+)

## 1) Prepare a GitHub PAT

Create a PAT with the minimal scopes you need (e.g., repo, pull_request, issues). Keep it safe.
 
- Generate: <https://github.com/settings/personal-access-tokens/new>

## 2) Install the server (local via Docker)

Docker is available on this machine. Pull and run the server via VS Code MCP configuration.

Option A — Workspace config file (.vscode/mcp.json):

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "github_token",
      "description": "GitHub Personal Access Token",
      "password": true
    }
  ],
  "servers": {
    "github": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${input:github_token}"
      }
    }
  }
}
```

- Place this file at `.vscode/mcp.json` in your repo. VS Code Copilot Agent Mode reads this format.
- When prompted, paste your PAT.

Option B — User settings (VS Code Settings → Copilot Chat → MCP Servers):
Add the same configuration under MCP Servers. If your UI expects the JSON under a `mcp` key, wrap the above inside `{ "mcp": { ... } }` as needed.

Notes:

- To target GitHub Enterprise Server or data residency (ghe.com), also set `GITHUB_HOST` env, e.g.:
  - `"env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${input:github_token}", "GITHUB_HOST": "https://YOURSUBDOMAIN.ghe.com" }`
- To enable only certain toolsets: set `GITHUB_TOOLSETS` (e.g., `repos,issues,pull_requests,actions`).
- To run read-only: set `GITHUB_READ_ONLY=1`.

## 3) Verify the server in Copilot Agent Mode

- Toggle Agent Mode (icon near the Copilot Chat input). You should see GitHub tools available automatically.
- Try a basic prompt: “List open pull requests in this repository.”

## 4) Remote server (optional, simplest)

Instead of Docker, you can use the hosted remote MCP server:

```json
{
  "servers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${input:github_mcp_pat}"
      }
    }
  },
  "inputs": [
    { "type": "promptString", "id": "github_mcp_pat", "description": "GitHub Personal Access Token", "password": true }
  ]
}
```

Use this if your MCP host supports remote MCP servers with OAuth/PAT.

## 5) Quick Commands (/command) — Practical Patterns

While the GitHub MCP Server exposes rich toolsets, here are quick “slash-style” prompts you can use in Copilot Chat for fast actions. These map to GitHub tools internally; just type them in Agent Mode:

- /command pr list — “List open PRs for the current repo with titles and authors.”
- /command pr create — “Create a PR from branch `feat/mcp-phase0-foundations` into `main` with title ‘Phase 0 foundations’.”
- /command pr review — “Review PR #123 for potential regressions and summarize requested changes.”
- /command issues list — “List open issues with labels and assignees.”
- /command issue create — “Create an issue titled ‘Add approval helper tool’ with body and label `enhancement`.”
- /command actions runs — “Show the latest workflow runs, highlight failures, and link the failing jobs.”
- /command code search — “Search this repo for ‘MCP_SERVER_INSTRUCTIONS_VERSION’ and summarize usage.”

Tips:

- Add context like “in this repo” or specify a repo (e.g., `owner/name`) if working across multiple repos.
- For enterprises, include `organization/project` context when referencing Projects or Discussions.

## 6) Advanced configuration (toolsets)

You can restrict/extend capabilities with toolsets:

- Default: `context,repos,issues,pull_requests,users`
- Example env: `GITHUB_TOOLSETS="repos,issues,pull_requests,actions,code_security"`
- Enable all: `GITHUB_TOOLSETS="all"`
- Dynamic tool discovery (beta): `GITHUB_DYNAMIC_TOOLSETS=1`
- Read-only mode: `GITHUB_READ_ONLY=1`

## 7) Build from source (optional)

If you prefer not to use Docker:

- Requires Go.
- Build: `go build -o github-mcp-server ./cmd/github-mcp-server`
- Configure in MCP servers as:

```json
{
  "servers": {
    "github": {
      "command": "${workspaceFolder}/external/github-mcp-server/github-mcp-server",
      "args": ["stdio"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${input:github_token}"
      }
    }
  }
}
```

## 8) Security

- Use least-privilege PAT scopes.
- Prefer read-only mode unless you explicitly need write actions.
- Review which toolsets are enabled to limit accidental operations.

## 9) Troubleshooting

- If Docker pull fails, ensure Docker Desktop is running and you’re logged out of ghcr if needed: `docker logout ghcr.io`.
- If tools don’t appear, confirm Agent Mode is on and the MCP server is listed as running in Copilot settings.
- Check that your PAT is valid and has the right scopes.

---

Cloned repo location in this workspace: `external/github-mcp-server`
You can browse the full docs there under `docs/` for deeper configuration, Enterprise settings, and toolset reference.
