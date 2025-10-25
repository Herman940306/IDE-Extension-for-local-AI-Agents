"""
🚀 AuraIA Router v2.0 - Automated E2E Testing Suite
Comprehensive automation for testing complete pipeline with LLM validation

Project Creator: Herman Swanepoel
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def find_ollama():
    """Find Ollama executable path"""
    # Common installation locations on Windows
    possible_paths = [
        Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
        Path(r"C:\Program Files\Ollama\ollama.exe"),
        Path(r"C:\Program Files (x86)\Ollama\ollama.exe"),
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    # Try PATH
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            timeout=5,
            shell=True,
        )
        if result.returncode == 0:
            return "ollama"
    except Exception:
        pass

    return None


OLLAMA_PATH = find_ollama()


def print_header(text):
    """Print formatted header"""
    print()
    print("=" * 80)
    print(f"  {text}")
    print("=" * 80)
    print()


def print_step(step_num, text):
    """Print formatted step"""
    print(f"\n{'─' * 80}")
    print(f"📌 Step {step_num}: {text}")
    print("─" * 80)


def print_success(text):
    """Print success message"""
    print(f"✅ {text}")


def print_error(text):
    """Print error message"""
    print(f"❌ {text}")


def print_warning(text):
    """Print warning message"""
    print(f"⚠️  {text}")


def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")


def run_command(cmd, description, check=True, capture=True):
    """Run shell command and return output"""
    print(f"   Running: {description}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=capture,
            text=True,
            timeout=30,
        )
        if capture and result.stdout:
            print(f"   Output: {result.stdout.strip()[:200]}")
        return result
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out: {description}")
        return None
    except subprocess.CalledProcessError as e:
        if check:
            print_error(f"Command failed: {description}")
            if capture and e.stderr:
                print(f"   Error: {e.stderr.strip()[:200]}")
        return None
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return None


def check_ollama_service():
    """Check if Ollama service is running"""
    print_step(1, "Checking Ollama Service")

    if not OLLAMA_PATH:
        print_error("Ollama not found on this system")
        print_info("Please install Ollama from: https://ollama.ai")
        print_info("Or ensure it's in your PATH")
        return False

    print_info(f"Found Ollama at: {OLLAMA_PATH}")

    # Try to connect to Ollama API
    try:
        response = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        if response.getcode() == 200:
            print_success("Ollama service is running on http://localhost:11434")
            return True
    except urllib.error.URLError:
        print_warning("Ollama service is not responding")
    except Exception as e:
        print_warning(f"Could not connect to Ollama: {e}")

    # Try to start Ollama
    print_info("Attempting to start Ollama service...")
    run_command(
        f'"{OLLAMA_PATH}" serve',
        "Starting Ollama service",
        check=False,
        capture=False,
    )

    # Give it time to start
    time.sleep(3)

    # Check again
    try:
        response = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        if response.getcode() == 200:
            print_success("Ollama service started successfully")
            return True
    except Exception:
        pass

    print_error("Could not start Ollama service")
    print_info("Please start Ollama manually:")
    print_info(f"  Option 1: Run '{OLLAMA_PATH} serve' in a separate terminal")
    print_info("  Option 2: Start Ollama desktop application")
    return False


def check_ollama_models():
    """Check if required models are available"""
    print_step(2, "Checking Ollama Models")

    if not OLLAMA_PATH:
        print_error("Ollama not found")
        return False

    required_models = {
        "qwen3:8b": "System 1 Fast Reasoner",
        "qwen3:4b": "System 1 Light",
        "deepseek-r1:8b": "System 2 Verifier",
        "gemma3:12b": "Output Composer (Premium)",
        "gemma3:4b": "Output Composer (Light)",
        "phi3:mini": "Safety Layer",
        "nomic-embed-text": "Context Engine",
    }

    result = run_command(
        f'"{OLLAMA_PATH}" list', "Listing available models", check=False
    )

    if not result or result.returncode != 0:
        print_error("Could not list Ollama models")
        return False

    available_models = result.stdout.lower()
    missing_models = []

    for model, purpose in required_models.items():
        model_name = model.split(":")[0]
        if model_name in available_models:
            print_success(f"{model:<20} ({purpose})")
        else:
            print_warning(f"{model:<20} MISSING - {purpose}")
            missing_models.append(model)

    if missing_models:
        print()
        print_warning(f"Missing {len(missing_models)} model(s)")
        print_info("To download missing models, run:")
        for model in missing_models:
            print(f'   "{OLLAMA_PATH}" pull {model}')
        print()

        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != "y":
            return False

    return True


def check_backend_health():
    """Check if backend is running and healthy"""
    print_step(3, "Checking Backend Health")

    try:
        response = urllib.request.urlopen("http://localhost:8001/health", timeout=5)
        if response.getcode() == 200:
            data = json.loads(response.read())
            print_success("Backend is running on http://localhost:8001")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Components: {data.get('components', {})}")
            return True
    except urllib.error.URLError:
        print_error("Backend is not running")
    except Exception as e:
        print_error(f"Could not connect to backend: {e}")

    print()
    print_info("Please start the backend:")
    print_info("  cd backend")
    print_info("  python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8001")
    return False


def run_diagnostic_test():
    """Run diagnostic test to verify LLM integration"""
    print_step(4, "Running Diagnostic Test")

    # Use absolute path to venv Python
    script_dir = Path(__file__).parent.absolute()
    python_path = script_dir / ".venv" / "Scripts" / "python.exe"

    if not python_path.exists():
        print_error(f"Python not found at: {python_path}")
        return False

    print_info("This may take 1-2 minutes as LLMs process requests...")
    print_info("Please wait while models generate responses...")
    print()

    result = subprocess.run(
        [str(python_path), str(script_dir / "backend" / "diagnostic_test.py")],
        capture_output=True,
        text=True,
        timeout=180,  # 3 minutes for LLM operations
        cwd=str(script_dir),
    )

    # Print the output for visibility
    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print("Stderr:")
        print(result.stderr)

    print(f"Return code: {result.returncode}")
    print()

    if result.returncode == 0:
        # Check if LLM is being used
        output = result.stdout.lower()
        if '"uses_llm": true' in output or "has llm: true" in output:
            print_success("LLM integration is working!")
            print_success("Models are responding correctly")
            return True
        elif '"uses_llm": false' in output or "has llm: false" in output:
            print_warning("System is in FALLBACK MODE")
            print_warning("LLM manager is not being used")
            print_info("This means responses will be deterministic placeholders")
            print()

            response = input("Continue with fallback mode? (y/n): ").strip().lower()
            if response != "y":
                return False

            return "fallback"
    else:
        print_error("Diagnostic test failed")
        return False


def run_e2e_tests():
    """Run full E2E test suite"""
    print_step(5, "Running E2E Test Suite")

    # Use absolute path to venv Python
    script_dir = Path(__file__).parent.absolute()
    python_path = script_dir / ".venv" / "Scripts" / "python.exe"

    if not python_path.exists():
        print_error(f"Python not found at: {python_path}")
        return False

    test_file = (
        script_dir
        / "backend"
        / "tests"
        / "integration"
        / "test_end_to_end_router_v2.py"
    )

    print_info("Starting pytest with verbose output...")
    print()

    result = subprocess.run(
        [
            str(python_path),
            "-m",
            "pytest",
            str(test_file),
            "-v",
            "-s",
            "--tb=short",
            "--color=yes",
        ],
        capture_output=False,
        cwd=str(script_dir),
    )

    return result.returncode == 0


def display_summary(results):
    """Display final summary"""
    print_header("🎯 Test Automation Summary")

    steps = [
        ("Ollama Service", results.get("ollama_service", False)),
        ("Ollama Models", results.get("ollama_models", False)),
        ("Backend Health", results.get("backend_health", False)),
        ("Diagnostic Test", results.get("diagnostic", False)),
        ("E2E Test Suite", results.get("e2e_tests", False)),
    ]

    print("Status of each step:")
    print()

    all_passed = True
    for step_name, status in steps:
        if status is True:
            print(f"  ✅ {step_name:<20} PASSED")
        elif status == "fallback":
            print(f"  ⚠️  {step_name:<20} FALLBACK MODE")
            all_passed = False
        else:
            print(f"  ❌ {step_name:<20} FAILED")
            all_passed = False

    print()
    print("=" * 80)

    if all_passed:
        print()
        print("🎉 SUCCESS! All tests passed with LLM integration working!")
        print()
        print("✅ Router v2.0 is production ready")
        print("✅ All 6 pipeline stages operational")
        print("✅ Multi-model orchestration working")
        print("✅ Ready for Alpha launch")
        print()
        print("Next Steps:")
        print("  1. Update COMPLETE_VISION.md - Mark Sprint 1 complete")
        print("  2. Commit test files to git")
        print("  3. Move to Week 2: Visual Agent Graph")
        print()
    elif results.get("diagnostic") == "fallback":
        print()
        print("⚠️  PARTIAL SUCCESS: Tests passed but system is in fallback mode")
        print()
        print("This means:")
        print("  - Pipeline architecture is working")
        print("  - API endpoints are responding")
        print("  - But LLM models are not being used")
        print()
        print("To enable full LLM integration:")
        print("  1. Ensure Ollama is running: ollama serve")
        print("  2. Verify models are loaded: ollama list")
        print("  3. Check backend config: backend/src/config.yaml")
        print("  4. Restart backend and re-run tests")
        print()
    else:
        print()
        print("❌ Some tests failed. Please review the output above.")
        print()
        print("Common issues:")
        print("  - Ollama not running: ollama serve")
        print("  - Models not downloaded: ollama pull <model>")
        print("  - Backend not running: check terminal")
        print("  - Port conflicts: check if 8001/11434 are in use")
        print()

    print("=" * 80)


def main():
    """Main automation flow"""
    print_header("🚀 AuraIA Router v2.0 - Automated E2E Testing")

    print("This script will:")
    print("  1. Check if Ollama service is running")
    print("  2. Verify required models are available")
    print("  3. Check backend health")
    print("  4. Run diagnostic test for LLM integration")
    print("  5. Execute full E2E test suite")
    print()

    response = input("Start automated testing? (y/n): ").strip().lower()
    if response != "y":
        print("Aborted by user")
        return

    results = {}

    # Step 1: Check Ollama
    results["ollama_service"] = check_ollama_service()
    if not results["ollama_service"]:
        print_error("Cannot proceed without Ollama service")
        display_summary(results)
        sys.exit(1)

    # Step 2: Check Models
    results["ollama_models"] = check_ollama_models()
    if not results["ollama_models"]:
        print_error("Cannot proceed without required models")
        display_summary(results)
        sys.exit(1)

    # Step 3: Check Backend
    results["backend_health"] = check_backend_health()
    if not results["backend_health"]:
        print_error("Cannot proceed without backend")
        display_summary(results)
        sys.exit(1)

    # Step 4: Diagnostic Test
    diagnostic_result = run_diagnostic_test()
    results["diagnostic"] = diagnostic_result
    if not diagnostic_result:
        print_error("Diagnostic test failed")
        display_summary(results)
        sys.exit(1)

    # Step 5: E2E Tests
    results["e2e_tests"] = run_e2e_tests()

    # Display summary
    display_summary(results)

    # Exit with appropriate code
    if results["e2e_tests"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
