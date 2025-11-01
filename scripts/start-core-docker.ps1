$ErrorActionPreference = 'Stop'

function Fail($msg) { Write-Host "[ERR] $msg" -ForegroundColor Red; exit 1 }

# Check docker CLI
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "Docker CLI not found. Install Docker Desktop and retry."
}

# Check daemon
try {
    docker info | Out-Null
}
catch {
    Fail "Docker Desktop/daemon not running. Start Docker Desktop and retry."
}

$pwdBefore = Get-Location
try {
    Set-Location (Split-Path -Parent $PSCommandPath)  # scripts/
    Set-Location (Split-Path -Parent (Get-Location))  # repo root

    Write-Host "[UP] docker compose up -d --build caddy frontend backend"
    docker compose up -d --build caddy frontend backend
    Write-Host "[PS] docker compose ps"
    docker compose ps
}
finally {
    Set-Location $pwdBefore
}

Write-Host "[TIP] Run scripts/health-probe.ps1 after services are healthy." -ForegroundColor Yellow
