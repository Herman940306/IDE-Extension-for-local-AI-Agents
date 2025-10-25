# AuralA Router Kit - Copilot Instructions

## Files Included
- `router.py` — Main runtime router that loads model routing config and handles tasks dynamically.
- `AuralA_Model_Routing_Generated.yaml` — Your model auto-config output (place in same directory).
- `README_INSTRUCTIONS.txt` — This guide for your Copilot Agent.

## Purpose
This kit allows AuralA to automatically:
- Detect hardware capabilities
- Match the best local models (Ollama) to System roles
- Route user tasks intelligently between reasoning, code, verification, and safety layers

## How to Use
1. Place all files in your project root directory.
2. Ensure your Ollama models are installed (`ollama pull`).
3. Run `python router.py` to test routing manually.
4. Your IDE or local agent should call:
   ```python
   from router import route_request
   result = route_request("code_generation", "Write a Python function to reverse a string.")
   print(result["text"])
   ```
5. The router logs decisions and latency in `aura_router.log`.

## Copilot Agent Instructions
- Monitor `AuralA_Model_Routing_Generated.yaml` for updates.
- If the file changes, re-import routing config immediately.
- When a user prompt is received, call `route_request()` with task type and input.
- Respect model assignments as defined in YAML.
- Log performance metrics (latency, errors) to help improve auto-configuration.
