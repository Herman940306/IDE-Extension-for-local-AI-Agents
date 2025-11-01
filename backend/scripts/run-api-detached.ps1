param(
    [int]$Port = 8001,
    [string]$Instance = 'agent-1',
    [string]$HostIP = '127.0.0.1'
)
$ErrorActionPreference = 'Stop'

$ws = Split-Path -Parent (Split-Path -Parent $PSCommandPath)  # .../backend
$root = Split-Path -Parent $ws
$python = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path $python)) {
    Write-Host "[ERR] Python venv not found at $python" -ForegroundColor Red
    exit 1
}

# If port already listening, skip starting
try {
    $listening = (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop) | Select-Object -First 1
}
catch { $listening = $null }
if ($listening) {
    Write-Host "[SKIP] Port $Port already in LISTEN state. Not starting another instance."
    exit 0
}

# Env and working dir
Push-Location $ws
$env:PYTHONPATH = $ws
$env:APP_INSTANCE = $Instance
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

# Start backend detached
$argList = @('-m', 'uvicorn', 'src.main:app', '--host', $HostIP, '--port', "$Port")
Write-Host "[START] $python $($argList -join ' ')"
Start-Process -FilePath $python -ArgumentList $argList -WorkingDirectory $ws -WindowStyle Minimized

# Probe readiness
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://${HostIP}:${Port}/docs" -UseBasicParsing -TimeoutSec 5
        Write-Host "[OK] http://${HostIP}:${Port}/docs status=$($resp.StatusCode)"
        exit 0
    }
    catch {
        Start-Sleep -Seconds 1
    }
}
Write-Host "[WARN] Backend not responding on http://${HostIP}:${Port}/docs after timeout" -ForegroundColor Yellow
exit 0
