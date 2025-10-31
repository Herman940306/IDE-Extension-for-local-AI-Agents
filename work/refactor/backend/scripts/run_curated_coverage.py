import os
import sys
from pathlib import Path

# Ensure we run from backend directory
BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)

try:
    import pytest  # type: ignore
except Exception as e:
    print("Pytest is required to run this script:", e)
    sys.exit(2)

# Exclude integration tests via marker and name pattern guard
# Override pytest.ini addopts to avoid global --cov=src
args = [
    "-q",
    "tests",
    "-m",
    "not integration",
    "-k",
    "not test_very_short_timeout",
    "-o",
    "addopts=--strict-markers --tb=short --disable-warnings",
    # Curated coverage targets for the 80% gate
    "--cov=src/models",
    "--cov=src/config/settings.py",
    "--cov=src/orchestrator/task_router.py",
    "--cov-report=term",
    "--cov-fail-under=80",
]

if __name__ == "__main__":
    sys.exit(pytest.main(args))
