<#
  Ops-OneClick.ps1 — One-click ops helpers for local AI Agents stack.
  Requires: Docker Desktop, PowerShell 7+, repo root as working dir.
#>

param(
  [ValidateSet('health','enable-smoke','disable-smoke','mode-success','mode-failure','restart-grafana','alert-activity','stack-status')]
  [string]$Action = 'health'
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$AlertRulesPath = Join-Path $RepoRoot 'monitoring/provisioning/alerting/alert-rules.yml'

function Invoke-HealthChecks {
  Write-Host '==> Health checks via Caddy (https://localhost)' -ForegroundColor Cyan
  try { curl -k https://localhost/api/health | Select-Object -ExpandProperty Content | Write-Host } catch { Write-Warning "API health failed: $_" }
  try { curl -k https://localhost/grafana/api/health | Select-Object -ExpandProperty Content | Write-Host } catch { Write-Warning "Grafana health failed: $_" }
  try { curl -k https://localhost/prometheus/-/ready | Select-Object -ExpandProperty Content | Write-Host } catch { Write-Warning "Prometheus ready failed: $_" }
}

function Restart-Grafana {
  Write-Host '==> Restarting Grafana to apply provisioning' -ForegroundColor Cyan
  docker compose restart grafana | Out-Host
}

function Show-AlertActivity {
  Write-Host '==> Recent Grafana alert activity (2m)' -ForegroundColor Cyan
  docker compose logs grafana -f --since 2m | Select-String -Pattern 'rule_uid=' | ForEach-Object { $_.Line } | Out-Host
}

function Show-StackStatus {
  Write-Host '==> docker compose ps' -ForegroundColor Cyan
  docker compose ps | Out-Host
}

function Set-SmokePaused([bool]$Paused) {
  if (-not (Test-Path $AlertRulesPath)) { throw "Alert rules file not found: $AlertRulesPath" }
  $content = Get-Content $AlertRulesPath -Raw
  # target block is uid: smoke_test_email; replace isPaused value
  $updated = $content -replace '(?ms)(uid:\s*smoke_test_email[\s\S]*?isPaused:\s*)(true|false)', ("`$1" + ($Paused.ToString().ToLower()))
  if ($updated -ne $content) {
    Set-Content -Path $AlertRulesPath -Value $updated -NoNewline
    Write-Host "Updated isPaused to $Paused for smoke_test_email" -ForegroundColor Green
  } else {
    Write-Host 'No change required (already matches)' -ForegroundColor Yellow
  }
}

function Set-SmokeMode([ValidateSet('success','failure')]$Mode) {
  if (-not (Test-Path $AlertRulesPath)) { throw "Alert rules file not found: $AlertRulesPath" }
  $expr = if ($Mode -eq 'success') { 'sum(up) > 0' } else { 'sum(up) == 0' }
  $content = Get-Content $AlertRulesPath -Raw
  # Replace expr in the smoke_test_email rule block
  $updated = $content -replace '(?ms)(uid:\s*smoke_test_email[\s\S]*?expr:\s*)(.+?)\r?\n', ("`$1$expr`r`n")
  if ($updated -ne $content) {
    Set-Content -Path $AlertRulesPath -Value $updated -NoNewline
    Write-Host "Set smoke_test_email expr to: $expr" -ForegroundColor Green
  } else {
    Write-Host 'No change required (expr already set)' -ForegroundColor Yellow
  }
}

switch ($Action) {
  'health' { Invoke-HealthChecks; break }
  'restart-grafana' { Restart-Grafana; break }
  'alert-activity' { Show-AlertActivity; break }
  'stack-status' { Show-StackStatus; break }
  'enable-smoke' { Set-SmokePaused -Paused:$false; Restart-Grafana; Show-AlertActivity; break }
  'disable-smoke' { Set-SmokePaused -Paused:$true; Restart-Grafana; Show-AlertActivity; break }
  'mode-success' { Set-SmokeMode -Mode success; Set-SmokePaused -Paused:$false; Restart-Grafana; Show-AlertActivity; break }
  'mode-failure' { Set-SmokeMode -Mode failure; Set-SmokePaused -Paused:$false; Restart-Grafana; Show-AlertActivity; break }
  default { Invoke-HealthChecks }
}
