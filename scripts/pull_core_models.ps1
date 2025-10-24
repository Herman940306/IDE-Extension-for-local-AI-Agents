# Pre-pull core local models for deterministic, low-latency operation
# Run this occasionally or after clean installs. Safe to re-run.
# Usage (PowerShell 7):
#   pwsh -File ./scripts/pull_core_models.ps1

param(
    [switch]$Quiet
)

function Invoke-PullModel {
    param(
        [Parameter(Mandatory=$true)][string]$Model
    )
    try {
        if (-not $Quiet) { Write-Host "Pulling $Model..." -ForegroundColor Cyan }
        ollama pull $Model | Out-Null
    } catch {
        Write-Warning ("Failed to pull {0}: {1}" -f $Model, $_.Exception.Message)
        throw
    }
}

$models = @(
    # System 1 – Fast Reasoner
    "llama3.2:3b",
    # System 2 – Analytical Verifier
    "mistral:7b",
    # Advanced reasoning (CPU fallback OK)
    "codellama:13b-instruct-q4_0",
    # Conversational / UX layer
    "gemma2:9b",
    # Safety / summarizer
    "phi3:medium",
    "phi3:mini",
    # Embeddings
    "nomic-embed-text"
)

foreach ($m in $models) {
    Invoke-PullModel -Model $m
}

if (-not $Quiet) { Write-Host "All core models pulled." -ForegroundColor Green }
