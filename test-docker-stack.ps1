#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Automated Docker Stack Validation Script
.DESCRIPTION
    Validates all Docker services, health checks, and integrations automatically
    Project Creator: Herman Swanepoel
.EXAMPLE
    .\test-docker-stack.ps1
#>

param(
    [switch]$SkipStartup,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$script:FailureCount = 0
$script:SuccessCount = 0
$script:TestResults = @()

# Colors for output
function Write-TestHeader($message) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  $message" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Write-TestResult($testName, $passed, $details = "") {
    $script:TestResults += [PSCustomObject]@{
        Test = $testName
        Result = if ($passed) { "PASS" } else { "FAIL" }
        Details = $details
    }
    
    if ($passed) {
        $script:SuccessCount++
        Write-Host "[✓] $testName" -ForegroundColor Green
        if ($details -and $Verbose) {
            Write-Host "    $details" -ForegroundColor Gray
        }
    } else {
        $script:FailureCount++
        Write-Host "[✗] $testName" -ForegroundColor Red
        if ($details) {
            Write-Host "    Error: $details" -ForegroundColor Yellow
        }
    }
}

function Test-DockerRunning {
    Write-TestHeader "1. Docker Installation & Status"
    
    try {
        $dockerVersion = docker --version 2>&1
        Write-TestResult "Docker CLI installed" $true $dockerVersion
    } catch {
        Write-TestResult "Docker CLI installed" $false "Docker not found in PATH"
        return $false
    }
    
    try {
        $composeVersion = docker-compose --version 2>&1
        Write-TestResult "Docker Compose installed" $true $composeVersion
    } catch {
        Write-TestResult "Docker Compose installed" $false "Docker Compose not found"
        return $false
    }
    
    try {
        docker ps | Out-Null 2>&1
        Write-TestResult "Docker daemon running" $true
        return $true
    } catch {
        Write-TestResult "Docker daemon running" $false "Docker daemon not responding"
        Write-Host "`n⚠️  Please start Docker Desktop and try again" -ForegroundColor Yellow
        return $false
    }
}

function Start-DockerStack {
    if ($SkipStartup) {
        Write-Host "`nSkipping Docker stack startup (using existing containers)..." -ForegroundColor Yellow
        return $true
    }
    
    Write-TestHeader "2. Starting Docker Stack"
    
    try {
        Write-Host "Starting all services..." -ForegroundColor Cyan
        $output = docker-compose up -d 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-TestResult "Docker Compose up" $true "All services started"
            
            Write-Host "`nWaiting 10 seconds for services to initialize..." -ForegroundColor Yellow
            Start-Sleep -Seconds 10
            return $true
        } else {
            Write-TestResult "Docker Compose up" $false $output
            return $false
        }
    } catch {
        Write-TestResult "Docker Compose up" $false $_.Exception.Message
        return $false
    }
}

function Test-ContainerStatus {
    Write-TestHeader "3. Container Health Status"
    
    $expectedContainers = @(
        "aiagentsintegrationsystemforvscode-backend-1",
        "aiagentsintegrationsystemforvscode-redis-1",
        "aiagentsintegrationsystemforvscode-ollama-1",
        "aiagentsintegrationsystemforvscode-prometheus-1",
        "aiagentsintegrationsystemforvscode-grafana-1"
    )
    
    $allRunning = $true
    
    foreach ($containerName in $expectedContainers) {
        try {
            $status = docker inspect $containerName --format '{{.State.Status}}' 2>&1
            $health = docker inspect $containerName --format '{{.State.Health.Status}}' 2>&1
            
            if ($status -eq "running") {
                $healthInfo = if ($health -match "healthy|starting") { $health } else { "no healthcheck" }
                Write-TestResult "$containerName running" $true "Status: $healthInfo"
            } else {
                Write-TestResult "$containerName running" $false "Status: $status"
                $allRunning = $false
            }
        } catch {
            Write-TestResult "$containerName running" $false "Container not found"
            $allRunning = $false
        }
    }
    
    return $allRunning
}

function Test-BackendHealth {
    Write-TestHeader "4. Backend Service Tests"
    
    # Test 1: Health endpoint
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing -TimeoutSec 10
        $healthData = $response.Content | ConvertFrom-Json
        
        if ($response.StatusCode -eq 200 -and $healthData.status -eq "healthy") {
            Write-TestResult "Backend health endpoint" $true "Status: $($healthData.status)"
        } else {
            Write-TestResult "Backend health endpoint" $false "Unexpected response"
        }
    } catch {
        Write-TestResult "Backend health endpoint" $false $_.Exception.Message
    }
    
    # Test 2: Swagger docs
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/docs" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-TestResult "Backend Swagger docs" $true "Accessible at /docs"
        } else {
            Write-TestResult "Backend Swagger docs" $false "Status: $($response.StatusCode)"
        }
    } catch {
        Write-TestResult "Backend Swagger docs" $false $_.Exception.Message
    }
    
    # Test 3: Metrics endpoint
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/metrics" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200 -and $response.Content -match "http_requests_total") {
            Write-TestResult "Backend Prometheus metrics" $true "Exposing metrics"
        } else {
            Write-TestResult "Backend Prometheus metrics" $false "No metrics found"
        }
    } catch {
        Write-TestResult "Backend Prometheus metrics" $false $_.Exception.Message
    }
    
    # Test 4: WebSocket endpoint availability
    try {
        # Just check if the port is listening (can't easily test WebSocket in PS without extra modules)
        $tcpTest = Test-NetConnection -ComputerName localhost -Port 8001 -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($tcpTest) {
            Write-TestResult "Backend WebSocket port" $true "Port 8001 accessible"
        } else {
            Write-TestResult "Backend WebSocket port" $false "Port 8001 not accessible"
        }
    } catch {
        Write-TestResult "Backend WebSocket port" $false $_.Exception.Message
    }
}

function Test-RedisHealth {
    Write-TestHeader "5. Redis Service Tests"
    
    # Test 1: Redis PING
    try {
        $pingResult = docker exec aiagentsintegrationsystemforvscode-redis-1 redis-cli ping 2>&1
        if ($pingResult -eq "PONG") {
            Write-TestResult "Redis PING command" $true "Responded with PONG"
        } else {
            Write-TestResult "Redis PING command" $false "Unexpected response: $pingResult"
        }
    } catch {
        Write-TestResult "Redis PING command" $false $_.Exception.Message
    }
    
    # Test 2: Redis SET/GET
    try {
        $setResult = docker exec aiagentsintegrationsystemforvscode-redis-1 redis-cli SET test_key "hello_docker" 2>&1
        $getResult = docker exec aiagentsintegrationsystemforvscode-redis-1 redis-cli GET test_key 2>&1
        
        if ($getResult -eq "hello_docker") {
            Write-TestResult "Redis SET/GET operations" $true "Data persistence working"
            # Cleanup
            docker exec aiagentsintegrationsystemforvscode-redis-1 redis-cli DEL test_key | Out-Null
        } else {
            Write-TestResult "Redis SET/GET operations" $false "Data mismatch"
        }
    } catch {
        Write-TestResult "Redis SET/GET operations" $false $_.Exception.Message
    }
    
    # Test 3: Redis INFO
    try {
        $infoResult = docker exec aiagentsintegrationsystemforvscode-redis-1 redis-cli INFO server 2>&1
        if ($infoResult -match "redis_version") {
            Write-TestResult "Redis server info" $true "Server responding"
        } else {
            Write-TestResult "Redis server info" $false "No version info"
        }
    } catch {
        Write-TestResult "Redis server info" $false $_.Exception.Message
    }
}

function Test-OllamaHealth {
    Write-TestHeader "6. Ollama Service Tests"
    
    # Test 1: Ollama version
    try {
        $versionResult = docker exec aiagentsintegrationsystemforvscode-ollama-1 ollama --version 2>&1
        if ($versionResult -match "ollama version") {
            Write-TestResult "Ollama installed" $true $versionResult
        } else {
            Write-TestResult "Ollama installed" $false "Version check failed"
        }
    } catch {
        Write-TestResult "Ollama installed" $false $_.Exception.Message
    }
    
    # Test 2: Ollama API endpoint
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            $models = ($response.Content | ConvertFrom-Json).models
            $modelCount = if ($models) { $models.Count } else { 0 }
            Write-TestResult "Ollama API endpoint" $true "API responding ($modelCount models)"
        } else {
            Write-TestResult "Ollama API endpoint" $false "Status: $($response.StatusCode)"
        }
    } catch {
        Write-TestResult "Ollama API endpoint" $false $_.Exception.Message
    }
}

function Test-PrometheusHealth {
    Write-TestHeader "7. Prometheus Monitoring Tests"
    
    # Test 1: Prometheus API
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9090/prometheus/api/v1/targets" -UseBasicParsing -TimeoutSec 10
        $data = $response.Content | ConvertFrom-Json
        
        if ($response.StatusCode -eq 200) {
            Write-TestResult "Prometheus API accessible" $true "API responding"
        } else {
            Write-TestResult "Prometheus API accessible" $false "Status: $($response.StatusCode)"
        }
    } catch {
        Write-TestResult "Prometheus API accessible" $false $_.Exception.Message
    }
    
    # Test 2: Backend target scraping
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9090/prometheus/api/v1/targets" -UseBasicParsing -TimeoutSec 10
        $data = $response.Content | ConvertFrom-Json
        
        $backendTarget = $data.data.activeTargets | Where-Object { $_.scrapeUrl -like "*backend*8001*" }
        
        if ($backendTarget.health -eq "up") {
            Write-TestResult "Prometheus scraping backend" $true "Backend target UP"
        } else {
            Write-TestResult "Prometheus scraping backend" $false "Target: $($backendTarget.health)"
        }
    } catch {
        Write-TestResult "Prometheus scraping backend" $false $_.Exception.Message
    }
    
    # Test 3: Query metrics
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9090/prometheus/api/v1/query?query=up" -UseBasicParsing -TimeoutSec 10
        $data = $response.Content | ConvertFrom-Json
        
        if ($data.status -eq "success" -and $data.data.result.Count -gt 0) {
            Write-TestResult "Prometheus metrics query" $true "$($data.data.result.Count) metrics found"
        } else {
            Write-TestResult "Prometheus metrics query" $false "No metrics returned"
        }
    } catch {
        Write-TestResult "Prometheus metrics query" $false $_.Exception.Message
    }
}

function Test-GrafanaHealth {
    Write-TestHeader "8. Grafana Dashboard Tests"
    
    # Test 1: Grafana UI
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-TestResult "Grafana UI accessible" $true "Login page responding"
        } else {
            Write-TestResult "Grafana UI accessible" $false "Status: $($response.StatusCode)"
        }
    } catch {
        Write-TestResult "Grafana UI accessible" $false $_.Exception.Message
    }
    
    # Test 2: Grafana API health
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 10
        $health = $response.Content | ConvertFrom-Json
        
        if ($health.database -eq "ok") {
            Write-TestResult "Grafana health check" $true "Database: $($health.database)"
        } else {
            Write-TestResult "Grafana health check" $false "Database: $($health.database)"
        }
    } catch {
        Write-TestResult "Grafana health check" $false $_.Exception.Message
    }
}

function Test-ServiceCommunication {
    Write-TestHeader "9. Inter-Service Communication Tests"
    
    # Test 1: Backend -> Redis
    try {
        $testScript = @"
import redis
r = redis.Redis(host='redis', port=6379)
r.set('docker_test', 'communication_ok')
result = r.get('docker_test')
print(result.decode('utf-8') if result else 'FAILED')
r.delete('docker_test')
"@
        
        $result = docker exec aiagentsintegrationsystemforvscode-backend-1 python -c $testScript 2>&1
        
        if ($result -match "communication_ok") {
            Write-TestResult "Backend → Redis communication" $true "Data exchange working"
        } else {
            Write-TestResult "Backend → Redis communication" $false "Communication failed: $result"
        }
    } catch {
        Write-TestResult "Backend → Redis communication" $false $_.Exception.Message
    }
    
    # Test 2: Backend -> Ollama
    try {
        $testScript = @"
import urllib.request
import json
try:
    response = urllib.request.urlopen('http://ollama:11434/api/tags', timeout=5)
    data = json.loads(response.read().decode('utf-8'))
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {e}')
"@
        
        $result = docker exec aiagentsintegrationsystemforvscode-backend-1 python -c $testScript 2>&1
        
        if ($result -match "SUCCESS") {
            Write-TestResult "Backend → Ollama communication" $true "API reachable"
        } else {
            Write-TestResult "Backend → Ollama communication" $false $result
        }
    } catch {
        Write-TestResult "Backend → Ollama communication" $false $_.Exception.Message
    }
}

function Test-ExtensionIntegration {
    Write-TestHeader "10. Extension Integration Tests"
    
    # Test 1: WebSocket connection (simulated)
    try {
        $testScript = @"
import asyncio
import websockets
import json

async def test_websocket():
    try:
        uri = 'ws://localhost:8001/ws/test-client-automation'
        async with websockets.connect(uri, timeout=5) as websocket:
            # Wait for connection message
            response = await asyncio.wait_for(websocket.recv(), timeout=3)
            data = json.loads(response)
            if data.get('type') == 'connection_established':
                print('CONNECTED')
            else:
                print(f'UNEXPECTED: {data}')
    except Exception as e:
        print(f'FAILED: {e}')

asyncio.run(test_websocket())
"@
        
        # Create temp file for Python script
        $tempFile = New-TemporaryFile
        $testScript | Out-File -FilePath $tempFile.FullName -Encoding UTF8
        
        # Copy to container and execute
        docker cp $tempFile.FullName aiagentsintegrationsystemforvscode-backend-1:/tmp/ws_test.py | Out-Null
        $result = docker exec aiagentsintegrationsystemforvscode-backend-1 python /tmp/ws_test.py 2>&1
        
        Remove-Item $tempFile.FullName -Force
        
        if ($result -match "CONNECTED") {
            Write-TestResult "WebSocket connection test" $true "Extension can connect"
        } else {
            Write-TestResult "WebSocket connection test" $false $result
        }
    } catch {
        Write-TestResult "WebSocket connection test" $false $_.Exception.Message
    }
    
    # Test 2: Check extension .vsix exists
    $vsixPath = "extension/aura-ai-assistant-1.0.0.vsix"
    if (Test-Path $vsixPath) {
        Write-TestResult "Extension package exists" $true $vsixPath
    } else {
        Write-TestResult "Extension package exists" $false "File not found"
    }
}

function Show-Summary {
    Write-TestHeader "Test Summary"
    
    Write-Host "Results:" -ForegroundColor Cyan
    $script:TestResults | Format-Table -AutoSize
    
    $total = $script:SuccessCount + $script:FailureCount
    $passRate = if ($total -gt 0) { [math]::Round(($script:SuccessCount / $total) * 100, 1) } else { 0 }
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  Total Tests: $total" -ForegroundColor White
    Write-Host "  Passed: $script:SuccessCount" -ForegroundColor Green
    Write-Host "  Failed: $script:FailureCount" -ForegroundColor Red
    Write-Host "  Pass Rate: $passRate%" -ForegroundColor $(if ($passRate -ge 80) { "Green" } else { "Yellow" })
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    if ($script:FailureCount -eq 0) {
        Write-Host "🎉 ALL TESTS PASSED! Docker stack is fully operational!" -ForegroundColor Green
        return 0
    } else {
        Write-Host "⚠️  Some tests failed. Review the results above." -ForegroundColor Yellow
        return 1
    }
}

# Main execution
try {
    Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║     AI Agents Integration System - Docker Stack Test     ║
║              Automated Validation Suite                  ║
║            Project Creator: Herman Swanepoel             ║
╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

    if (-not (Test-DockerRunning)) {
        exit 1
    }
    
    if (-not (Start-DockerStack)) {
        Write-Host "`n❌ Failed to start Docker stack. Exiting." -ForegroundColor Red
        exit 1
    }
    
    Test-ContainerStatus
    Test-BackendHealth
    Test-RedisHealth
    Test-OllamaHealth
    Test-PrometheusHealth
    Test-GrafanaHealth
    Test-ServiceCommunication
    Test-ExtensionIntegration
    
    $exitCode = Show-Summary
    
    Write-Host "`nDocker Stack Status:" -ForegroundColor Cyan
    docker-compose ps
    
    exit $exitCode
    
} catch {
    Write-Host "`n❌ CRITICAL ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    exit 1
}
