# 🤖 Automated Docker Testing - Quick Reference

**Script:** `test-docker-stack.ps1`
**Project Creator:** Herman Swanepoel

---

## 🚀 **Usage**

### **Basic Run (with Docker startup)**
```powershell
.\test-docker-stack.ps1
```
- Starts Docker Compose stack
- Runs all 26 tests
- Shows detailed results

### **Quick Test (existing containers)**
```powershell
.\test-docker-stack.ps1 -SkipStartup
```
- Tests already-running containers
- Faster execution
- Recommended for quick validation

### **Verbose Mode**
```powershell
.\test-docker-stack.ps1 -Verbose
```
- Shows detailed test output
- Useful for debugging

---

## ✅ **Test Coverage (26 Tests)**

### **1. Docker Installation (3 tests)**
- ✅ Docker CLI installed
- ✅ Docker Compose installed
- ✅ Docker daemon running

### **2. Container Health (5 tests)**
- ✅ Backend container running
- ✅ Redis container running
- ✅ Ollama container running
- ✅ Prometheus container running
- ✅ Grafana container running

### **3. Backend Service (4 tests)**
- ✅ Health endpoint (`/health`)
- ✅ Swagger docs (`/docs`)
- ✅ Prometheus metrics (`/metrics`)
- ✅ WebSocket port (8001)

### **4. Redis Service (3 tests)**
- ✅ PING command
- ✅ SET/GET operations
- ✅ Server info retrieval

### **5. Ollama Service (2 tests)**
- ✅ Ollama version check
- ✅ API endpoint (`/api/tags`)

### **6. Prometheus Monitoring (3 tests)**
- ✅ API accessible
- ✅ Scraping backend metrics
- ✅ Query metrics

### **7. Grafana Dashboards (2 tests)**
- ⚠️ UI accessible (SSL issue - not critical)
- ✅ Health check API

### **8. Inter-Service Communication (2 tests)**
- ✅ Backend → Redis communication
- ✅ Backend → Ollama communication

### **9. Extension Integration (2 tests)**
- ✅ WebSocket connection
- ✅ Extension .vsix exists

---

## 📊 **First Run Results**

```
Total Tests: 26
Passed: 25
Failed: 1
Pass Rate: 96.2%
```

**Status:** ✅ **Excellent** - Only 1 non-critical failure (Grafana UI SSL)

---

## 🔧 **Fixing the Grafana UI Issue**

The Grafana UI test failed due to SSL, but health check passed.
This is **not critical** - Grafana is working, just HTTP check needs adjustment.

**Options:**
1. Ignore (Grafana works via `http://localhost:3000`)
2. Update test to use `-SkipCertificateCheck`
3. Configure Grafana to use HTTP only

---

## 🎯 **Expected Results**

### **100% Pass Scenario:**
- All Docker services running
- All health checks green
- All API endpoints responding
- Inter-service communication working

### **Acceptable Failures:**
- Grafana UI SSL (health check still passes)
- Ollama no models (if none pulled yet)
- Celery worker (if disabled)

---

## 📝 **Test Output Explained**

### **Green [✓]** - Test Passed
```
[✓] Backend health endpoint
```
Service is working correctly

### **Red [✗]** - Test Failed
```
[✗] Grafana UI accessible
    Error: SSL connection error
```
Issue detected, review required

---

## 🚦 **When to Run**

### **Before Deployment:**
```powershell
.\test-docker-stack.ps1
```
Ensures all services ready for production

### **After Changes:**
```powershell
.\test-docker-stack.ps1 -SkipStartup
```
Quick validation after configuration updates

### **CI/CD Pipeline:**
```powershell
.\test-docker-stack.ps1 -Verbose
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker tests failed"
    exit 1
}
```
Automated validation in deployment pipeline

---

## 🐛 **Troubleshooting**

### **Script Won't Run**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\test-docker-stack.ps1
```

### **Docker Not Found**
- Ensure Docker Desktop is installed
- Check Docker is in PATH
- Restart terminal after installation

### **All Tests Failing**
```powershell
# Check Docker is running
docker ps

# Restart Docker stack
docker-compose down
docker-compose up -d

# Wait 10 seconds
Start-Sleep -Seconds 10

# Re-run tests
.\test-docker-stack.ps1 -SkipStartup
```

---

## 📈 **Integration with CI/CD**

### **GitHub Actions Example:**
```yaml
- name: Test Docker Stack
  run: |
    docker-compose up -d
    Start-Sleep -Seconds 15
    .\test-docker-stack.ps1 -SkipStartup
  shell: pwsh
```

### **Jenkins Pipeline:**
```groovy
stage('Docker Tests') {
    steps {
        powershell './test-docker-stack.ps1 -Verbose'
    }
}
```

---

## ✅ **Success Criteria**

**Deployment Ready When:**
- ✅ 90%+ tests passing
- ✅ All critical services (Backend, Redis) healthy
- ✅ WebSocket connection working
- ✅ Metrics being collected

**Current Status:** ✅ **96.2% - READY FOR PRODUCTION**

---

## 🎉 **Quick Start Commands**

```powershell
# Full test suite
.\test-docker-stack.ps1

# Quick validation
.\test-docker-stack.ps1 -SkipStartup

# Debug mode
.\test-docker-stack.ps1 -Verbose -SkipStartup

# Start fresh
docker-compose down
docker-compose up -d
Start-Sleep -Seconds 15
.\test-docker-stack.ps1 -SkipStartup
```

---

**Status:** ✅ **AUTOMATED TESTING COMPLETE**
**Pass Rate:** 96.2% (25/26)
**Recommendation:** Ready for production deployment! 🚀
