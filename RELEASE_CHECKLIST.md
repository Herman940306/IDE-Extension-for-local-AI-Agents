# Aura AI Assistant – Release Checklist

This checklist ensures consistent, safe releases of the Aura AI project (VS Code extension + backend/MCP).

## 0) Preconditions
- Confirm branch: feature work merged into a release branch (e.g., `feat/...`) and ready to merge to `main`.
- Confirm CI green on the release branch (build, type-check, tests, gitleaks).
- Confirm local Node/VS Code versions:
  - Node 18.x LTS
  - VS Code engine compatibility in `extension/package.json` (`engines.vscode`).

## 1) Versioning + Changelog
- Bump version in `extension/package.json` (semver):
  - Patch: bug fixes only
  - Minor: new features, backward compatible
  - Major: breaking changes
- Update `RELEASE_NOTES.md` with:
  - Added / Changed / Fixed / Security sections
  - Minimum VS Code version changes
  - Known issues & mitigations

## 2) Security & Compliance
- Confirm no secrets in repo (CI gitleaks job is green).
- Confirm GitHub token guidance present (see `SECURITY.md`).
- Verify licenses and notices (no new dependencies with incompatible licenses).

## 3) Testing & Quality Gates
- Run unit tests locally (extension):
  ```powershell
  cd extension
  npm ci
  npm run compile
  npm test
  ```
- Optional backend checks (if applicable to this release):
  ```powershell
  pwsh -NoProfile -Command "Invoke-WebRequest http://127.0.0.1:8001/mcp/health -UseBasicParsing"
  ```
- Manual sanity tests in VS Code (F5):
  - `Aura: Rank GitHub Repos`
  - `Aura: Rank GitHub Repos + Issues/PRs`
  - Status bar health indicator (latency + ULTRA mode)
  - Telemetry toggle command

## 4) Build Artifacts
- Package the extension:
  ```powershell
  cd extension
  npm ci
  npm run package
  ```
- Output should be a `.vsix` file in `extension/`.
- Install locally to verify:
  ```powershell
  code --install-extension (Get-ChildItem *.vsix | Select-Object -Last 1).FullName
  ```

## 5) Marketplace Prep (if publishing)
- Ensure marketplace assets:
  - Icon present: `extension/images/AuraIA_logo.jpg`
  - Screenshots / animated GIF added to repo (and referenced in README)
  - Clear README features + setup + troubleshooting
- Ensure VSCE PAT is set before publishing:
  ```powershell
  $env:VSCE_PAT = "<your_marketplace_pat>"
  cd extension
  npm run package:publish
  ```

## 6) Release on GitHub
- Create a signed tag (optional but recommended):
  ```powershell
  git checkout main
  git pull --rebase
  git tag -a vX.Y.Z -m "Aura AI Assistant vX.Y.Z"
  git push origin vX.Y.Z
  ```
- Create GitHub Release:
  - Title: `vX.Y.Z`
  - Notes: paste from `RELEASE_NOTES.md`
  - Attach `.vsix` artifact (if not publishing to Marketplace)

## 7) Post-Release Validation
- Install from Marketplace and test commands on a clean machine/workspace.
- Verify health status latency, ULTRA mode switching, ranking endpoints.
- Monitor issues: error reports, feedback, download stats.

## 8) Rollback Plan
- Keep previous `.vsix` handy for rollback.
- If critical issue is found:
  - Unpublish or deprecate the release in Marketplace.
  - Create hotfix branch, patch, bump version (X.Y.Z+1), repeat checklist.

## 9) Housekeeping
- Close fixed issues and link them to the release/milestone.
- Update `README.md` if user-facing changes occurred.
- Add next milestones/tasks to the roadmap.

---

Quick commands recap (PowerShell):
```powershell
cd extension
npm ci
npm run compile
npm test
npm run package
code --install-extension (Get-ChildItem *.vsix | Select-Object -Last 1).FullName
```
