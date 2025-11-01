param([int[]]$Ports = @(8001, 8002, 8003))
foreach ($p in $Ports) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
        if ($conns) {
            $procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($procId in $procIds) {
                try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host ("Stopped PID {0} on port {1}" -f $procId, $p) }
                catch { Write-Host ("Failed to stop PID {0} on port {1}: {2}" -f $procId, $p, $_.Exception.Message) }
            }
        }
        else {
            Write-Host ("No listener on port {0}" -f $p)
        }
    }
    catch {
        Write-Host ("Error checking port {0}: {1}" -f $p, $_.Exception.Message)
    }
}
