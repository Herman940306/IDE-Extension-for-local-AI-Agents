param(
    [string]$RepoUrl = "https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents.git"
)

# Determine project root (assumes you run this from the project root)
$root = (Get-Location).Path
$remoteRoot = Join-Path $root "remote_clone"

Write-Host "[1/4] Preparing remote clone at: $remoteRoot" -ForegroundColor Cyan

# Clone or update remote
if (Test-Path (Join-Path $remoteRoot ".git")) {
    git -C "$remoteRoot" fetch origin
    git -C "$remoteRoot" reset --hard origin/main
    Write-Host "[Updated existing clone]" -ForegroundColor Green
}
else {
    git clone $RepoUrl "$remoteRoot"
    Write-Host "[Cloned fresh copy]" -ForegroundColor Green
}

# Copy local .env if present
$localEnv = Join-Path $root "backend/.env"
$remoteEnv = Join-Path $remoteRoot "backend/.env"
if (Test-Path $localEnv) {
    Copy-Item -Path $localEnv -Destination $remoteEnv -Force -ErrorAction SilentlyContinue
    Write-Host "[Copied backend/.env into remote_clone]" -ForegroundColor Green
}
else {
    Write-Host "[No backend/.env found locally to copy]" -ForegroundColor Yellow
}

# Generate diff reports (non-destructive)
Write-Host "[2/4] Generating diff: remote -> local (preview)" -ForegroundColor Cyan
$diffRemoteToLocal = Join-Path $root "_diff-remote-to-local.txt"
robocopy "$remoteRoot" "$root" /MIR /L | Out-File $diffRemoteToLocal -Encoding utf8

Write-Host "[3/4] Generating diff: local -> remote (preview)" -ForegroundColor Cyan
$diffLocalToRemote = Join-Path $root "_diff-local-to-remote.txt"
robocopy "$root" "$remoteRoot" /MIR /L | Out-File $diffLocalToRemote -Encoding utf8

Write-Host "[4/4] Done." -ForegroundColor Cyan
Write-Host "Review these files:" -ForegroundColor White
Write-Host " - $diffRemoteToLocal" -ForegroundColor White
Write-Host " - $diffLocalToRemote" -ForegroundColor White

Write-Host "Tip: Open them in VS Code (Explorer) to skim changes." -ForegroundColor DarkGray
