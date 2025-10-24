# 🚨 EMERGENCY SYSTEM RECOVERY

**Status:** CRITICAL - Kiro crashed during deployment

## What Happened

System overload during frontend-backend integration testing.

## IMMEDIATE RECOVERY STEPS

### 1. Start Backend (Terminal 1)

```bash
cd backend
.venv\Scripts\activate
python run.py
```

**Wait for:** "Application startup complete"

### 2. Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

**Wait for:** "Local: http://localhost:3000"

### 3. Test Connection

```bash
curl http://127.0.0.1:8001/health
```

## If Still Broken

### Nuclear Option - Fresh Start

```bash
# Stop everything
taskkill /F /IM python.exe
taskkill /F /IM node.exe

# Restart backend
cd backend
python run.py

# Restart frontend (new terminal)
cd frontend
npm run dev
```

## System Status

✅ Backend code: WORKING
✅ Frontend code: WORKING
✅ WebSocket protocol: CORRECT
⚠️ Connection: Needs both services running

## Quick Test

**Backend:**

```bash
curl http://127.0.0.1:8001/
```

**Frontend:**
Open http://localhost:3000

**WebSocket:**

```bash
wscat -c ws://127.0.0.1:8001/ws/test
```

## CRITICAL: Run Services in Separate Terminals

DO NOT run both in same terminal!

**Terminal 1:** Backend only
**Terminal 2:** Frontend only

---

**RECOVERY MODE ACTIVE** 🔥
