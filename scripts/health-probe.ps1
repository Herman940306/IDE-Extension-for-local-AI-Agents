param(
    [string[]]$Urls = @(
        "http://127.0.0.1:8001/docs",
        "http://localhost:5288/",
        "http://localhost/api/docs",
        "http://localhost/agent-1/docs",
        "http://localhost/agent-2/docs",
        "http://localhost/agent-3/docs"
    ),
    [int]$Retries = 15,
    [int]$DelaySeconds = 1
)

function Test-Url([string]$u) {
    for ($i = 0; $i -lt $Retries; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 5
            Write-Host ("[OK] {0} status={1}" -f $u, $r.StatusCode)
            return
        }
        catch {
            Start-Sleep -Seconds $DelaySeconds
        }
    }
    Write-Host ("[FAIL] {0}" -f $u)
}

foreach ($u in $Urls) { Test-Url $u }
