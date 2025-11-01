param(
    [string]$OllamaHost = $env:OLLAMA_HOST
)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
Push-Location ..

if (-not $OllamaHost -or [string]::IsNullOrWhiteSpace($OllamaHost)) { $OllamaHost = "http://127.0.0.1:11434" }

# Start 8001, wait for /docs 200
& "$PSScriptRoot\start-agent.ps1" -Port 8001 -Instance agent-1 -DelaySeconds 0 -OllamaHost $OllamaHost
for ($i = 0; $i -lt 30; $i++) {
    try { $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8001/docs" -TimeoutSec 2; if ($r.StatusCode -eq 200) { break } } catch {}
    Start-Sleep -Milliseconds 500
}

# Start 8002
& "$PSScriptRoot\start-agent.ps1" -Port 8002 -Instance agent-2 -DelaySeconds 2 -OllamaHost $OllamaHost
for ($i = 0; $i -lt 30; $i++) {
    try { $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8002/docs" -TimeoutSec 2; if ($r.StatusCode -eq 200) { break } } catch {}
    Start-Sleep -Milliseconds 500
}

# Start 8003
& "$PSScriptRoot\start-agent.ps1" -Port 8003 -Instance agent-3 -DelaySeconds 4 -OllamaHost $OllamaHost
for ($i = 0; $i -lt 30; $i++) {
    try { $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8003/docs" -TimeoutSec 2; if ($r.StatusCode -eq 200) { break } } catch {}
    Start-Sleep -Milliseconds 500
}

Write-Host "All agents started sequence completed."
Pop-Location; Pop-Location
