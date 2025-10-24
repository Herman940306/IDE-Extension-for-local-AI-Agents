"""
Backend Monitoring Script
Project Creator: Herman Swanepoel
"""

import sys
import time
from datetime import datetime

import requests


def check_health():
    """Check backend health"""
    try:
        response = requests.get("http://127.0.0.1:8001/health", timeout=5)
        data = response.json()

        status = data.get("status", "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if status == "healthy":
            print(f"✅ [{timestamp}] Backend healthy")
        elif status == "degraded":
            print(f"⚠️  [{timestamp}] Backend degraded")
        else:
            print(f"❌ [{timestamp}] Backend unhealthy")

        return status == "healthy"

    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"❌ [{timestamp}] Backend unreachable: {e}")
        return False


def monitor(interval=60):
    """Monitor backend continuously"""
    print("🔍 Starting backend monitoring...")
    print(f"Checking every {interval} seconds")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            check_health()
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped")
        sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor backend health")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds (default: 60)",
    )
    parser.add_argument("--once", action="store_true", help="Check once and exit")

    args = parser.parse_args()

    if args.once:
        healthy = check_health()
        sys.exit(0 if healthy else 1)
    else:
        monitor(args.interval)
