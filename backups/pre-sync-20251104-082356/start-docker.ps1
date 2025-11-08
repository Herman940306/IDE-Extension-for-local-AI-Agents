#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start AuraIA backend services with Docker Compose
.DESCRIPTION
    This script starts all AuraIA backend services including:
    - Ollama AI service
    - Backend API
    - Redis cache
    - Celery workers
    - Prometheus monitoring
.PARAMETER Pull
    Pull latest Docker images before starting
.PARAMETER Build
    Rebuild Docker images before starting
.PARAMETER Logs
    Follow logs after starting services
.EXAMPLE
    .\start-docker.ps1
    .\start-docker.ps1 -Build -Logs
#>

param(
    [switch]$Pull,
    [switch]$Build,
    [switch]$Logs,
    [switch]$Down
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = Split-Path -Parent $PSScriptRoot

Write-Host "🚀 AuraIA Docker Compose Startup" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker is running
try {
    docker version | Out-Null
} catch {
    Write-Host "❌ Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Docker is running" -ForegroundColor Green

# Navigate to workspace root
Set-Location $WorkspaceRoot

if ($Down) {
    Write-Host ""
    Write-Host "🛑 Stopping all services..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "✅ All services stopped" -ForegroundColor Green
    exit 0
}

if ($Pull) {
    Write-Host ""
    Write-Host "📦 Pulling latest images..." -ForegroundColor Cyan
    docker-compose pull
}

if ($Build) {
    Write-Host ""
    Write-Host "🔨 Building images..." -ForegroundColor Cyan
    docker-compose build --no-cache
}

Write-Host ""
Write-Host "🚀 Starting services..." -ForegroundColor Cyan
docker-compose up -d

Write-Host ""
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check service health
$services = @("redis", "ollama", "backend")
$allHealthy = $true

foreach ($service in $services) {
    $status = docker-compose ps -q $service
    if ($status) {
        $health = docker inspect --format='{{.State.Health.Status}}' $(docker-compose ps -q $service) 2>$null
        if ($health -eq "healthy" -or $null -eq $health) {
            Write-Host "✅ $service is running" -ForegroundColor Green
        } else {
            Write-Host "⚠️  $service is $health" -ForegroundColor Yellow
            $allHealthy = $false
        }
    } else {
        Write-Host "❌ $service is not running" -ForegroundColor Red
        $allHealthy = $false
    }
}

Write-Host ""
Write-Host "📊 Service URLs:" -ForegroundColor Cyan
Write-Host "  • Backend API:  http://localhost:8001" -ForegroundColor White
Write-Host "  • API Docs:     http://localhost:8001/docs" -ForegroundColor White
Write-Host "  • Ollama:       http://localhost:11434" -ForegroundColor White
Write-Host "  • Prometheus:   http://localhost:9090" -ForegroundColor White
Write-Host "  • Grafana:      http://localhost:3000" -ForegroundColor White

Write-Host ""
Write-Host "🔧 Useful commands:" -ForegroundColor Cyan
Write-Host "  • View logs:    docker-compose logs -f" -ForegroundColor White
Write-Host "  • Stop all:     docker-compose down" -ForegroundColor White
Write-Host "  • Restart:      docker-compose restart" -ForegroundColor White
Write-Host "  • Check status: docker-compose ps" -ForegroundColor White

if ($Logs) {
    Write-Host ""
    Write-Host "📜 Following logs (Ctrl+C to exit)..." -ForegroundColor Cyan
    docker-compose logs -f
}

if ($allHealthy) {
    Write-Host ""
    Write-Host "✅ All services are healthy!" -ForegroundColor Green
    Write-Host "🎉 AuraIA is ready to use!" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "⚠️  Some services may still be starting..." -ForegroundColor Yellow
    Write-Host "Run 'docker-compose logs -f' to monitor startup." -ForegroundColor Yellow
}
