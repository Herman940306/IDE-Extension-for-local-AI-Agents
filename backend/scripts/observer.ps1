param(
    [int[]]$Ports = @(8001, 8002, 8003),
    [int]$Seconds = 300
)

$stopAt = (Get-Date).AddSeconds($Seconds)
Write-Host ("Starting observer for ports: {0} (duration: {1}s)" -f ($Ports -join ','), $Seconds)

while ((Get-Date) -lt $stopAt) {
    $ts = (Get-Date).ToString('HH:mm:ss')
    foreach ($p in $Ports) {
        try {
            $listening = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
        }
        catch { $listening = $null }
        if ($listening) {
            Write-Host ("[$ts] Port {0}: LISTEN" -f $p)
        }
        else {
            Write-Host ("[$ts] Port {0}: (no listener)" -f $p)
        }
        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:{0}/docs" -f $p) -TimeoutSec 2
            Write-Host ("       /docs: {0}" -f $resp.StatusCode)
        }
        catch {
            $msg = $_.Exception.Message.Split([Environment]::NewLine)[0]
            Write-Host ("       /docs: fail - {0}" -f $msg)
        }
    }
    Start-Sleep -Seconds 1
}
