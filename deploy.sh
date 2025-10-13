#!/bin/bash
# Deployment Script for Linux Server
# Project Creator: Herman Swanepoel

echo "🚀 Deploying Enterprise AI Agents Backend..."

# Stop existing containers
docker-compose down

# Pull latest changes
git pull origin feature/system-refactoring-v1

# Build and start
docker-compose build backend
docker-compose up -d

# Health check
sleep 5
curl -f http://localhost:8000/health || echo "⚠️ Health check failed"

echo "✅ Deployment complete"
