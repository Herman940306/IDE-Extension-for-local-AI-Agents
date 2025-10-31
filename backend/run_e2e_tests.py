"""
End-to-End Test Runner for Router v2.0
Comprehensive test suite for complete pipeline validation

Project Creator: Herman Swanepoel
"""

import subprocess
import sys
import urllib.request
from pathlib import Path

print("=" * 80)
print("🧪 AuraIA Router v2.0 - End-to-End Test Suite")
print("=" * 80)
print()

# Check if backend is running
print("📡 Checking if backend is running on http://localhost:8001...")

try:
    response = urllib.request.urlopen("http://localhost:8001/health", timeout=5)
    if response.getcode() == 200:
        print("✅ Backend is running")
    else:
        print("❌ Backend returned non-200 status")
        sys.exit(1)
except Exception as e:
    print(f"❌ Backend is not running: {e}")
    print()
    print("Please start the backend first:")
    print("  cd backend")
    print("  python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8001")
    sys.exit(1)

print()
print("🚀 Running End-to-End Tests...")
print("-" * 80)
print()

# Run pytest
test_file = (
    Path(__file__).parent / "tests" / "integration" / "test_end_to_end_router_v2.py"
)

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        str(test_file),
        "-v",
        "-s",
        "--tb=short",
        "--color=yes",
    ],
    cwd=Path(__file__).parent,
)

print()
print("=" * 80)
if result.returncode == 0:
    print("✅ All End-to-End Tests PASSED!")
else:
    print("❌ Some tests failed. Please review the output above.")
print("=" * 80)

sys.exit(result.returncode)
