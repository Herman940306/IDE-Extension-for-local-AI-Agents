<#!
.SYNOPSIS
  Installs pre-commit and enables a guard that blocks commits containing files under
  'AuraIA IDE Vision and Roadmap/'.

.DESCRIPTION
  - Detects Python (prefers .venv if present), installs/updates pre-commit
  - Runs 'pre-commit install' to activate hooks
  - Prints verification steps to test the guard safely

.USAGE
  pwsh -NoProfile -File scripts/Setup-PreCommitConfidentiality.ps1

.NOTES
  This script makes no commits. Verification steps are printed for you to run manually.
!#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Get-PythonCmd {
  $workspace = Split-Path -Parent $PSCommandPath | Split-Path -Parent
  $venvPython = Join-Path $workspace ".venv/Scripts/python.exe"
  if (Test-Path $venvPython) { return $venvPython }
  # Fallbacks
  $candidates = @('python', 'py')
  foreach ($c in $candidates) {
    try {
      & $c --version 2>$null
      if ($LASTEXITCODE -eq 0) { return $c }
    } catch {}
  }
  throw "Python not found. Please install Python 3.x or create a .venv first."
}

Write-Host "[1/3] Detecting Python..." -ForegroundColor Cyan
$python = Get-PythonCmd
Write-Host "Using: $python" -ForegroundColor Green

Write-Host "[2/3] Installing/Updating pre-commit..." -ForegroundColor Cyan
& $python -m pip install -U pre-commit | Write-Output

Write-Host "[3/3] Installing git hook..." -ForegroundColor Cyan
pre-commit install | Write-Output

Write-Host "`nDone. Pre-commit is installed and the hook is active." -ForegroundColor Green

Write-Host "`nHow to verify (manual steps):" -ForegroundColor Yellow
$confDir = "AuraIA IDE Vision and Roadmap"
Write-Host "1) Create a temporary file under '$confDir':"
Write-Host "   New-Item -ItemType File -Path '$confDir/__hook_test__.txt' -Force | Out-Null" -ForegroundColor Gray
Write-Host "2) Stage it:"
Write-Host "   git add '$confDir/__hook_test__.txt'" -ForegroundColor Gray
Write-Host "3) Attempt a commit (expect the hook to FAIL and block it):"
Write-Host "   git commit -m 'test: hook should block this'" -ForegroundColor Gray
Write-Host "4) Cleanup:"
Write-Host "   git reset HEAD~0; git rm --cached -f '$confDir/__hook_test__.txt'; Remove-Item -Force '$confDir/__hook_test__.txt'" -ForegroundColor Gray

Write-Host "`nNote: The folder is already in .gitignore and .dockerignore; this hook adds an extra safety net." -ForegroundColor Yellow
