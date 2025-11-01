param(
    [Parameter(Mandatory = $true)][int]$Port,
    [string]$Instance = "agent",
    [int]$DelaySeconds = 0,
    [string]$OllamaHost = $env:OLLAMA_HOST,
    [string]$PythonPath = ".\\.venv\\Scripts\\python.exe",
    [string]$AppModule = "src.main:app",
    [string]$BindHost = "127.0.0.1",
    [string]$LogDir = "logs",
    [string]$PidDir = ".pids"
)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
Push-Location ..  # go to backend root

# Ensure dirs
if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
if (!(Test-Path $PidDir)) { New-Item -ItemType Directory -Path $PidDir | Out-Null }

if (-not $OllamaHost -or [string]::IsNullOrWhiteSpace($OllamaHost)) { $OllamaHost = "http://127.0.0.1:11434" }

if ($DelaySeconds -gt 0) { Start-Sleep -Seconds $DelaySeconds }

# Check port free
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host ("Port {0} is already in use. Aborting start for {1}." -f $Port, $Instance)
    Pop-Location; Pop-Location; exit 2
}

# Wait for Ollama (max 30s)
$ollamaReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri ("{0}/api/version" -f $OllamaHost) -TimeoutSec 2
        if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { $ollamaReady = $true; break }
    }
    catch { Start-Sleep -Milliseconds 500 }
}
if (-not $ollamaReady) { Write-Host ("Warning: Ollama not reachable at {0}; continuing anyway." -f $OllamaHost) }

$logFile = Join-Path $LogDir ("agent-{0}.log" -f $Port)
$errFile = Join-Path $LogDir ("agent-{0}.err.log" -f $Port)
$pidFile = Join-Path $PidDir ("agent-{0}.pid" -f $Port)

$envMap = @{ PYTHONPATH = (Get-Location).Path; APP_INSTANCE = $Instance; OLLAMA_HOST = $OllamaHost; PYTHONIOENCODING = 'utf-8'; PYTHONUTF8 = '1' }

$argList = "-m uvicorn {0} --host {1} --port {2} --log-level info" -f $AppModule, $BindHost, $Port

# Start detached process with redirected output
$proc = Start-Process -FilePath $PythonPath -ArgumentList $argList -WorkingDirectory (Get-Location).Path -PassThru -WindowStyle Minimized -RedirectStandardOutput $logFile -RedirectStandardError $errFile -Environment $envMap
$proc.Id | Out-File -FilePath $pidFile -Encoding ascii -Force
Write-Host ("Started {0} on :{1} (PID {2}), logging to {3}" -f $Instance, $Port, $proc.Id, $logFile)

Pop-Location; Pop-Location
