param(
    [int]$Count = 3,
    [int]$BasePort = 8001,
    [string]$BindHost = "127.0.0.1",
    [switch]$NoReload
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $workspaceRoot 'backend'
$pythonExe = Join-Path $backendDir '.venv\Scripts\python.exe'

if (-not (Test-Path $pythonExe)) {
    Write-Host "Python venv not found at $pythonExe. Creating one and installing deps..." -ForegroundColor Yellow
    Push-Location $backendDir
    try {
        if (-not (Test-Path '.venv')) { python -m venv .venv }
        .\.venv\Scripts\python -m pip install -r requirements.txt
    }
    finally {
        Pop-Location
    }
}

for ($i = 0; $i -lt $Count; $i++) {
    $port = $BasePort + $i
    $instanceName = "agent-{0}" -f ($i + 1)
    $uvicornArgs = @('-m', 'uvicorn', 'src.main:app', '--host', $BindHost, '--port', $port)
    if (-not $NoReload) { $uvicornArgs += '--reload' }

    $command = @(
        "Push-Location `"$backendDir`"",
        "$env:PYTHONPATH = `"$backendDir`"",
        "$env:APP_INSTANCE = `"$instanceName`"",
        "`"$pythonExe`" $($uvicornArgs -join ' ')"
    ) -join '; '

    Start-Process -FilePath "pwsh" -ArgumentList @('-NoExit', '-NoLogo', '-Command', $command) -WorkingDirectory $backendDir | Out-Null
    Write-Host ("Launched {0} on http://{1}:{2}" -f $instanceName, $BindHost, $port) -ForegroundColor Green
}

Write-Host "All requested agent instances have been launched in separate terminals." -ForegroundColor Cyan
