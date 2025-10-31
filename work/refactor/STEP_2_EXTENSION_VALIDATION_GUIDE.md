# 🚀 Step 2: Extension Validation Guide

**Project Creator:** Herman Swanepoel
**Date:** October 25, 2025
**Status:** ✅ Step 1 Complete - Ready for Extension Testing

---

## 📋 Prerequisites Checklist

Before starting, verify:

- [x] ✅ All 870 tests passing (Step 1 complete)
- [x] ✅ Backend code ready at `backend/run.py`
- [x] ✅ Extension built at `extension/aura-ai-assistant-1.0.0.vsix`
- [ ] 🔲 Backend server running
- [ ] 🔲 Extension installed in VS Code
- [ ] 🔲 Extension configured with backend URL

---

## 🎯 Step 2 Tasks

### Task 1: Start Backend Server (5 minutes)

**Option A: Run in Terminal (Recommended for testing)**

```bash
# Open a NEW PowerShell terminal
cd "e:\Visual Studio Coode Projects\AI Agents Integration system for VS Code"
.\.venv\Scripts\python.exe backend/run.py
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started server process
INFO:     Application startup complete.
```

**Verify Backend is Running:**

Open browser: <http://127.0.0.1:8001/health>

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-24T...",
  "services": {
    "api": "operational",
    "memory": "operational"
  }
}
```

Or test with curl:
```bash
curl http://127.0.0.1:8001/health
```

**Alternative: View API Docs**
- Swagger UI: <http://127.0.0.1:8001/docs>
- ReDoc: <http://127.0.0.1:8001/redoc>

---

### Task 2: Install Extension (5 minutes)

**Two Methods:**

**Method A: Using VS Code Command Palette**

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type: `Extensions: Install from VSIX...`
3. Navigate to: `e:\Visual Studio Coode Projects\AI Agents Integration system for VS Code\extension\aura-ai-assistant-1.0.0.vsix`
4. Click "Install"
5. Restart VS Code when prompted

**Method B: Using Command Line**

```bash
code --install-extension "e:\Visual Studio Coode Projects\AI Agents Integration system for VS Code\extension\aura-ai-assistant-1.0.0.vsix"
```

**Verify Installation:**
1. Open VS Code
2. Press `Ctrl+Shift+X` (Extensions view)
3. Search for "Aura AI Assistant"
4. Should show as "Installed"

---

### Task 3: Configure Extension (2 minutes)

**Open Settings:**
1. Press `Ctrl+,` (or `Cmd+,` on Mac)
2. Search for: `aura`

**Configure Backend URLs:**

Set these settings:

```json
{
  "aura.backend.url": "http://127.0.0.1:8001",
  "aura.backend.websocket": "ws://127.0.0.1:8001/ws"
}
```

**Method 1: Via Settings UI**
- Find "Aura: Backend Url" → Set to `http://127.0.0.1:8001`
- Find "Aura: Backend Websocket" → Set to `ws://127.0.0.1:8001/ws`

**Method 2: Via settings.json**
1. Press `Ctrl+Shift+P`
2. Type: `Preferences: Open Settings (JSON)`
3. Add the configuration above

---

### Task 4: Test Extension Commands (30 minutes)

**Open a Test File:**

Create a test Python file: `test_extension.py`

```python
def calculate_sum(a, b):
    return a + b

# TODO: Add more functions
```

---

#### **Test 1: Generate Code** (5 min)

1. Open Command Palette (`Ctrl+Shift+P`)
2. Type: `Aura: Generate Code`
3. When prompted, enter: "Create a function to calculate factorial"
4. Wait for response

**Expected Behavior:**
- ✅ Shows "Generating code..." notification
- ✅ Backend logs show request received
- ✅ Generated code appears in editor or output panel
- ✅ No errors in console

**If It Fails:**
- Check backend terminal for errors
- Check VS Code Developer Console (`Help` → `Toggle Developer Tools`)
- Verify backend URL in settings

---

#### **Test 2: Explain Code** (5 min)

1. Select the `calculate_sum` function in your test file
2. Open Command Palette (`Ctrl+Shift+P`)
3. Type: `Aura: Explain Code`
4. Wait for explanation

**Expected Behavior:**
- ✅ Shows "Explaining code..." notification
- ✅ Explanation appears in output panel or notification
- ✅ Explanation is relevant to the selected code

---

#### **Test 3: Refactor Code** (5 min)

1. Select the `calculate_sum` function
2. Open Command Palette (`Ctrl+Shift+P`)
3. Type: `Aura: Refactor Code`
4. When prompted, enter: "Add type hints and docstring"
5. Wait for refactored code

**Expected Behavior:**
- ✅ Shows "Refactoring code..." notification
- ✅ Refactored code appears with improvements
- ✅ Code is syntactically valid

---

#### **Test 4: Fix Bugs** (5 min)

Create code with an intentional bug:

```python
def divide(a, b):
    return a / b  # Bug: no zero division check
```

1. Select the `divide` function
2. Open Command Palette (`Ctrl+Shift+P`)
3. Type: `Aura: Fix Bugs`
4. Wait for bug fix suggestions

**Expected Behavior:**
- ✅ Shows "Analyzing bugs..." notification
- ✅ Identifies the division by zero issue
- ✅ Suggests fix with try/except or if check

---

#### **Test 5: WebSocket Real-time (10 min)**

**Monitor WebSocket Connection:**

1. Open VS Code Developer Tools (`Help` → `Toggle Developer Tools`)
2. Go to "Console" tab
3. Run any command (Generate/Explain/Refactor/Fix)
4. Watch for WebSocket messages

**Expected Console Messages:**
```
WebSocket connected to ws://127.0.0.1:8001/ws
Sending task: { type: "generate", ... }
Received response: { status: "processing", ... }
Received response: { status: "complete", result: "..." }
```

**Backend Terminal Should Show:**
```
INFO:     127.0.0.1:xxxxx - "WebSocket /ws" [accepted]
{"event": "task_received", "task_type": "generate", ...}
{"event": "task_processing", ...}
{"event": "task_complete", ...}
```

---

### Task 5: Integration Testing (10 minutes)

**Scenario: Complete Workflow**

1. **Open a real project file** (any Python file in your workspace)
2. **Generate new code:**
   - Command: "Aura: Generate Code"
   - Prompt: "Create a logging utility function"
3. **Explain the generated code:**
   - Select generated code
   - Command: "Aura: Explain Code"
4. **Refactor it:**
   - Keep selection
   - Command: "Aura: Refactor Code"
   - Prompt: "Add error handling"
5. **Check for bugs:**
   - Command: "Aura: Fix Bugs"

**Success Criteria:**
- ✅ All 4 commands work without errors
- ✅ Backend responds within reasonable time (<10 seconds)
- ✅ WebSocket stays connected throughout
- ✅ Generated code is relevant and useful
- ✅ No crashes or exceptions

---

## 🔍 Troubleshooting

### Backend Not Responding

**Symptoms:**
- Extension commands timeout
- "Cannot connect to backend" error

**Solutions:**
1. Verify backend is running: `curl http://127.0.0.1:8001/health`
2. Check backend logs for errors
3. Restart backend: `Ctrl+C` then rerun `python backend/run.py`
4. Check firewall isn't blocking port 8001

---

### Extension Not Found

**Symptoms:**
- Commands don't appear in Command Palette
- Extension not in Extensions view

**Solutions:**
1. Verify installation: Check Extensions view (`Ctrl+Shift+X`)
2. Reinstall extension: Uninstall → Install from VSIX
3. Restart VS Code completely
4. Check VS Code version (needs 1.80.0+)

---

### WebSocket Connection Failed

**Symptoms:**
- Console shows "WebSocket connection failed"
- Commands timeout

**Solutions:**
1. Verify WebSocket URL: `ws://127.0.0.1:8001/ws` (not `wss://`)
2. Check backend supports WebSocket (it does)
3. Try disabling VS Code extensions that might interfere
4. Check Developer Console for detailed error

---

### Ollama Not Available (Optional)

**Symptoms:**
- Backend logs show "Ollama not available"
- Commands work but slower

**Solutions:**
1. This is **optional** - backend has fallback mechanisms
2. To enable Ollama (optional):
   - Install Ollama: <https://ollama.ai>
   - Pull model: `ollama pull llama3.2:3b-q4_K_M`
   - Backend will auto-detect

---

## ✅ Validation Checklist

Mark each test as complete:

### Backend
- [ ] Backend starts without errors
- [ ] Health endpoint returns 200 OK
- [ ] API docs accessible at /docs
- [ ] Backend logs show no errors

### Extension Installation
- [ ] Extension installed from VSIX
- [ ] Extension appears in Extensions view
- [ ] Settings configured correctly
- [ ] Commands appear in Command Palette

### Command Testing
- [ ] "Aura: Generate Code" works
- [ ] "Aura: Explain Code" works
- [ ] "Aura: Refactor Code" works
- [ ] "Aura: Fix Bugs" works

### WebSocket
- [ ] WebSocket connects successfully
- [ ] Real-time messages in console
- [ ] Connection stays stable
- [ ] Backend logs show WebSocket events

### Integration
- [ ] Complete workflow executes
- [ ] All commands work together
- [ ] No errors or crashes
- [ ] Performance acceptable

---

## 📊 Success Criteria

**Step 2 is complete when:**

1. ✅ Backend running and healthy
2. ✅ Extension installed and configured
3. ✅ All 4 commands tested and working
4. ✅ WebSocket communication verified
5. ✅ Complete workflow executed successfully
6. ✅ No blocking errors or crashes

**Time Estimate:** 1-2 hours
**Actual Time:** _____ (fill in after completion)

---

## 🎯 After Step 2

Once Step 2 is complete, you'll be ready for:

**Step 3: Docker Deployment Validation** (30 min)
- Spin up full Docker stack
- Test all services
- Verify extension connects to containerized backend

---

## 📝 Notes & Observations

Use this space to record any issues, observations, or improvements:

```
Date: ___________
Issues Found:


Resolutions:


Performance Notes:


Improvements Needed:


```

---

**Status:** 🔄 **IN PROGRESS**
**Started:** October 25, 2025
**Completed:** _____________

**Next Step:** Step 3 - Docker Deployment Validation
