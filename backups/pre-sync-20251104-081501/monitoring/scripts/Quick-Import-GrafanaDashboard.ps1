param(
    [string]$GrafanaUrl = "http://localhost:3000",
    [string]$DashboardPath = "monitoring/dashboards/gpu_vram_and_latency.json",
    [string]$FolderId = "0",
    [switch]$Overwrite
)

# Quick-imports a Grafana dashboard via HTTP API.
# Auth options:
# 1) API Token: set $env:GRAFANA_API_TOKEN
# 2) Basic Auth: set $env:GRAFANA_ADMIN_USER and $env:GRAFANA_ADMIN_PASSWORD

function Get-AuthHeader {
    if ($env:GRAFANA_API_TOKEN) {
        return @{ Authorization = "Bearer $($env:GRAFANA_API_TOKEN)" }
    }
    if ($env:GRAFANA_ADMIN_USER -and $env:GRAFANA_ADMIN_PASSWORD) {
        $bytes = [System.Text.Encoding]::ASCII.GetBytes("$($env:GRAFANA_ADMIN_USER):$($env:GRAFANA_ADMIN_PASSWORD)")
        $b64 = [System.Convert]::ToBase64String($bytes)
        return @{ Authorization = "Basic $b64" }
    }
    throw "No Grafana credentials found. Set GRAFANA_API_TOKEN or GRAFANA_ADMIN_USER/GRAFANA_ADMIN_PASSWORD."
}

try {
    if (-not (Test-Path -Path $DashboardPath)) {
        throw "Dashboard file not found: $DashboardPath"
    }

    $headers = Get-AuthHeader

    Write-Host "Reading dashboard JSON from: $DashboardPath"
    $dashboardJson = Get-Content -Raw -Path $DashboardPath | ConvertFrom-Json

    $body = @{
        dashboard = $dashboardJson
        overwrite = [bool]$Overwrite
        folderId = [int]$FolderId
        message = "Imported by Quick-Import-GrafanaDashboard.ps1"
    } | ConvertTo-Json -Depth 20

    $uri = "$GrafanaUrl/api/dashboards/db"
    Write-Host "Importing dashboard to: $uri"

    $response = Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -ContentType 'application/json' -Body $body -ErrorAction Stop

    Write-Host "Import result:" ($response | ConvertTo-Json -Depth 5)
    Write-Host "Done."
}
catch {
    Write-Error $_
    exit 1
}
