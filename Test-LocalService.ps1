# Test-LocalService.ps1
# Simple utility to poll a local HTTP endpoint by URL or Port/Path until it responds or times out.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false, HelpMessage = "Full URL to test (e.g., http://127.0.0.1:8001/health)")]
    [string]$Url,

    [Parameter(Mandatory = $false, HelpMessage = "Local port to test (e.g., 8001)")]
    [int]$Port,

    [Parameter(Mandatory = $false, HelpMessage = "Path when using -Port (default: /)")]
    [string]$Path = "/",

    [Parameter(Mandatory = $false, HelpMessage = "Timeout in seconds (default: 10)")]
    [int]$TimeoutSec = 10
)

function Test-LocalService {
    [CmdletBinding()] param(
        [Parameter(Mandatory = $false)] [string]$Url,
        [Parameter(Mandatory = $false)] [int]$Port,
        [Parameter(Mandatory = $false)] [string]$Path = "/",
        [Parameter(Mandatory = $false)] [int]$TimeoutSec = 10
    )

    if (-not $Url) {
        if (-not $Port) {
            Write-Error "Specify -Url or -Port"
            return 2
        }
        if (-not $Path.StartsWith('/')) { $Path = "/$Path" }
        $Url = "http://127.0.0.1:{0}{1}" -f $Port, $Path
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -TimeoutSec 2
            $code = $resp.StatusCode
            if ($code -ge 200 -and $code -lt 500) {
                Write-Output $code
                return 0
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    Write-Output "DOWN"
    return 1
}

# If the script is invoked with parameters, run the function directly and set exit code accordingly.
if ($PSBoundParameters.Count -gt 0) {
    $result = Test-LocalService @PSBoundParameters
    if ($result -is [int]) { exit $result } else { exit 0 }
}

# Otherwise, just export the function into the caller's scope for dot-sourcing convenience.
Set-Item -Path Function:\Test-LocalService -Value (Get-Command Test-LocalService).ScriptBlock -Force | Out-Null
Write-Verbose "Function Test-LocalService is now available in the current session."
