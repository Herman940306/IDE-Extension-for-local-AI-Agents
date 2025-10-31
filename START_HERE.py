"""
🎯 START HERE - One-Click E2E Testing Automation
Guides you through starting Ollama and running all tests
"""

import subprocess
import sys
import urllib.request
from pathlib import Path


def print_banner():
    print()
    print("=" * 80)
    print("  🚀 AuraIA Router v2.0 - Automated E2E Testing")
    print("  Quick Start Guide")
    print("=" * 80)
    print()


def check_ollama_running():
    """Check if Ollama is accessible"""
    try:
        response = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return response.getcode() == 200
    except Exception:
        return False


def main():
    print_banner()

    print("📋 Pre-flight Checks:")
    print()

    # Check Ollama
    print("1️⃣  Checking Ollama service...")
    if check_ollama_running():
        print("   ✅ Ollama is running and accessible!")
        print()
    else:
        print("   ❌ Ollama is NOT running")
        print()
        print("🔴 ACTION REQUIRED:")
        print()
        print("   Please start Ollama using ONE of these methods:")
        print()
        print("   🥇 RECOMMENDED - Desktop App:")
        print("      1. Click Windows Start Menu")
        print("      2. Search for 'Ollama'")
        print("      3. Launch the Ollama application")
        print("      4. Look for 🦙 icon in system tray")
        print()
        print("   OR")
        print()
        print("   📟 Command Line (keep window open):")
        print(
            '      Start-Process -FilePath "$env:USERPROFILE\\AppData\\Local\\Programs\\Ollama\\ollama.exe" -ArgumentList "serve"'
        )
        print()
        print(
            "   ⏱️  Wait 10-15 seconds for Ollama to start, then run this script again."
        )
        print()

        response = (
            input("Press Enter to exit and start Ollama, or 'r' to retry check: ")
            .strip()
            .lower()
        )
        if response == "r":
            return main()  # Retry
        return

    # Check Backend
    print("2️⃣  Checking Backend service...")
    try:
        response = urllib.request.urlopen("http://localhost:8001/health", timeout=3)
        if response.getcode() == 200:
            print("   ✅ Backend is running on port 8001")
            print()
        else:
            print("   ⚠️  Backend responded but status unclear")
            print()
    except Exception:
        print("   ❌ Backend is NOT running")
        print()
        print("   Please start the backend:")
        print("   cd backend")
        print("   python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8001")
        print()
        return

    # All checks passed
    print("=" * 80)
    print("  ✅ ALL SYSTEMS GO!")
    print("=" * 80)
    print()
    print("🚀 Ready to run complete E2E test automation!")
    print()
    print("This will:")
    print("  • Verify all 7 models are available")
    print("  • Run diagnostic tests with actual LLM responses")
    print("  • Execute 13 comprehensive E2E tests")
    print("  • Provide detailed pass/fail summary")
    print()
    print("⏱️  Expected time: 2-5 minutes (first run slower as models load)")
    print()

    response = input("Start automation now? (y/n): ").strip().lower()
    if response != "y":
        print("Cancelled by user")
        return

    print()
    print("=" * 80)
    print("  LAUNCHING AUTOMATED TEST SUITE...")
    print("=" * 80)
    print()

    # Run the automation
    python_path = Path(".venv/Scripts/python.exe")
    if not python_path.exists():
        python_path = Path("python")

    result = subprocess.run(
        [str(python_path), "automated_e2e_test.py"],
        cwd=Path(__file__).parent,
    )

    sys.exit(result.returncode)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Cancelled by user")
        sys.exit(1)
