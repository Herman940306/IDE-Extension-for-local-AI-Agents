---
inclusion: always
priority: critical
---

# Dependency Management Rules

**CRITICAL: Install and Verify All Dependencies Before Proceeding**

## Core Principle

**NEVER move to the next task until ALL dependencies are installed, tested, and verified to work correctly.**

## Mandatory Workflow

### 1. Detect Dependencies

When writing code, ALWAYS identify:
- Python packages (imports)
- Node.js packages (require/import)
- System dependencies
- External libraries
- Type definitions (@types/*)

### 2. Install Immediately

**Before marking any task complete, you MUST:**

#### For Python Dependencies:
```powershell
# Activate virtual environment first
cd backend
.\venv\Scripts\Activate.ps1

# Install package
pip install [package-name]

# Verify installation
python -c "import [package_name]; print([package_name].__version__)"

# Update requirements.txt
pip freeze > requirements.txt
```

#### For Node.js Dependencies:
```powershell
cd extension

# Install package
npm install [package-name]

# Install dev dependencies
npm install --save-dev [package-name]

# Install type definitions if needed
npm install --save-dev @types/[package-name]

# Verify installation
npm list [package-name]
```

### 3. Test Installation

**MANDATORY: Test every dependency after installation**

```powershell
# Python: Try importing
python -c "import [package]; print('✓ Success')"

# Node.js: Check if module resolves
node -e "require('[package]'); console.log('✓ Success')"

# TypeScript: Check types
npx tsc --noEmit
```

### 4. Retry on Failure

**If installation fails, you MUST try ALL these options in order:**

#### Python Retry Options:
1. **Try with pip upgrade:**
   ```powershell
   pip install --upgrade pip
   pip install [package-name]
   ```

2. **Try specific version:**
   ```powershell
   pip install [package-name]==[version]
   ```

3. **Try with --no-cache:**
   ```powershell
   pip install --no-cache-dir [package-name]
   ```

4. **Try with --force-reinstall:**
   ```powershell
   pip install --force-reinstall [package-name]
   ```

5. **Try alternative package name:**
   ```powershell
   # Example: opencv-python vs cv2
   pip install opencv-python
   ```

6. **Install from source:**
   ```powershell
   pip install git+https://github.com/[repo]/[package].git
   ```

#### Node.js Retry Options:
1. **Clear cache and retry:**
   ```powershell
   npm cache clean --force
   npm install [package-name]
   ```

2. **Try with --legacy-peer-deps:**
   ```powershell
   npm install [package-name] --legacy-peer-deps
   ```

3. **Try with --force:**
   ```powershell
   npm install [package-name] --force
   ```

4. **Try specific version:**
   ```powershell
   npm install [package-name]@[version]
   ```

5. **Try with yarn:**
   ```powershell
   yarn add [package-name]
   ```

6. **Delete node_modules and reinstall:**
   ```powershell
   Remove-Item -Recurse -Force node_modules
   Remove-Item package-lock.json
   npm install
   npm install [package-name]
   ```

### 5. Verify Imports Work

**After installation, ALWAYS verify:**

```powershell
# Run diagnostics on the file
# This checks for import errors, type errors, etc.
```

Use the `getDiagnostics` tool to check for:
- Import errors
- Type errors
- Missing dependencies
- Syntax errors

### 6. Document Installation

**Add to commit message:**
```
SP-XXX: [Task description]
- Installed: [package1], [package2]
- Updated: requirements.txt / package.json
- Verified: All imports working
```

## Enforcement Rules

### ❌ NEVER Do This:
- Write code with imports and move on without installing
- Assume packages are already installed
- Skip verification steps
- Leave broken imports
- Mark task complete with missing dependencies

### ✅ ALWAYS Do This:
- Install packages immediately when adding imports
- Test every installation
- Retry with all options if it fails
- Verify with getDiagnostics
- Update requirements.txt or package.json
- Document what was installed

## Common Packages

### Python Backend:
```powershell
# FastAPI ecosystem
pip install fastapi uvicorn pydantic python-dotenv

# WebSocket
pip install websockets python-socketio

# AI/ML
pip install openai anthropic langchain crewai

# Database
pip install sqlalchemy redis chromadb

# Testing
pip install pytest pytest-asyncio pytest-cov httpx

# Utilities
pip install python-multipart aiofiles
```

### TypeScript Extension:
```powershell
# VS Code extension
npm install @types/vscode @types/node

# WebSocket
npm install ws @types/ws socket.io-client

# Utilities
npm install axios dotenv

# Testing
npm install --save-dev @vscode/test-electron mocha @types/mocha

# Build tools
npm install --save-dev typescript @types/node esbuild
```

## Error Handling

### If All Retry Options Fail:

1. **Document the issue:**
   ```
   ERROR: Unable to install [package-name]
   Tried: pip, specific version, no-cache, force-reinstall
   Error: [error message]
   ```

2. **Check for alternatives:**
   - Look for similar packages
   - Check if package is deprecated
   - Find maintained forks

3. **Ask user for guidance:**
   - Report the specific error
   - List what was tried
   - Ask for alternative approach

4. **NEVER proceed with broken dependencies**

## Pre-Task Checklist

Before starting ANY task:
- [ ] Check if virtual environment is activated (Python)
- [ ] Check if node_modules exists (Node.js)
- [ ] Verify existing dependencies are working
- [ ] Update pip/npm if needed

## Post-Task Checklist

Before marking task complete:
- [ ] All new imports have packages installed
- [ ] All installations tested and verified
- [ ] getDiagnostics shows no import errors
- [ ] requirements.txt or package.json updated
- [ ] Changes committed with dependency info
- [ ] No broken imports or missing types

## Integration with Core Rules

This rule works with **Module 1: Core Development Rules**:
- **Rule 4: Install Packages as You Go** - This is the detailed implementation
- **Rule 2: Fix Errors Immediately** - Includes dependency errors
- **Rule 3: Test and Validate** - Verify imports work

## Priority

This rule has **CRITICAL** priority and is **MANDATORY** for all development work.

Violation of this rule (moving forward with uninstalled dependencies) will result in:
- Broken code
- Failed tests
- Wasted time debugging
- Incomplete tasks

---

**Rule Created By:** Herman Swanepoel  
**Date:** 2025-01-13  
**Version:** 1.0  
**Enforcement:** MANDATORY
