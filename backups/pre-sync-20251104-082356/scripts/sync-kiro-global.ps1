param(
    [string]$Source = (Join-Path $PSScriptRoot "..\.kiro"),
    [string]$Dest = (Join-Path $env:USERPROFILE ".kiro"),
    [switch]$UpdateSettings
)

Write-Host "Syncing .kiro from: $Source" -ForegroundColor Cyan
Write-Host "             to: $Dest" -ForegroundColor Cyan

if (!(Test-Path $Source)) { throw "Source path not found: $Source" }
if (!(Test-Path $Dest)) { New-Item -ItemType Directory -Path $Dest | Out-Null }

# Mirror directory
robocopy "$Source" "$Dest" /MIR | Out-Null
Write-Host "Mirror complete." -ForegroundColor Green

if ($UpdateSettings) {
    $mcpPath = Join-Path $Source "settings\mcp.json"
    if (!(Test-Path $mcpPath)) { throw "Missing MCP config: $mcpPath" }
    $mcp = Get-Content -Raw -Path $mcpPath | ConvertFrom-Json
    $mcpServers = $mcp.mcpServers

    $settingsCandidates = @(
        (Join-Path $env:APPDATA "Code\\User\\settings.json"),
        (Join-Path $env:APPDATA "Code - Insiders\\User\\settings.json")
    )

    foreach ($sp in $settingsCandidates) {
        $dir = Split-Path -Parent $sp
        if (!(Test-Path $dir)) { continue }
        if (Test-Path $sp) { $settings = Get-Content -Raw -Path $sp | ConvertFrom-Json } else { $settings = New-Object PSObject }
        $null = $settings | Add-Member -NotePropertyName 'github.copilot.chat.mcpServers' -NotePropertyValue $mcpServers -Force
        $json = $settings | ConvertTo-Json -Depth 20
        $json | Set-Content -Path $sp -Encoding UTF8
        Write-Host "Updated MCP servers in: $sp" -ForegroundColor Yellow
    }
}

Write-Host "Done." -ForegroundColor Green
