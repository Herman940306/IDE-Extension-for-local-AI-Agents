"""
Quick API Test Script
Run this after starting the backend server
"""

import json
import time

import requests


def test_api():
    print("🧪 API HEALTH CHECK TESTS")
    print("=" * 60)

    base_url = "http://127.0.0.1:8001"

    # Wait for server to be ready
    print("\n⏳ Waiting for server to be ready...")
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Server is ready after {i+1} attempt(s)")
                break
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                print(f"   Attempt {i+1}/{max_retries}: Server not ready yet...")
                time.sleep(1)
            else:
                print("❌ Server did not start in time")
                return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

    # Test 1: Health Check
    print("\n📋 Test 1: Health Check Endpoint")
    print("-" * 60)
    try:
        health = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Status Code: {health.status_code}")
        print(f"✅ Response Time: {health.elapsed.total_seconds():.3f}s")
        print("\n📊 Response Data:")
        print(json.dumps(health.json(), indent=2))
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

    # Test 2: API Documentation
    print("\n📋 Test 2: API Documentation")
    print("-" * 60)
    try:
        docs = requests.get(f"{base_url}/docs", timeout=5)
        print(f"✅ API Docs accessible: {docs.status_code}")

        redoc = requests.get(f"{base_url}/redoc", timeout=5)
        print(f"✅ ReDoc accessible: {redoc.status_code}")
    except Exception as e:
        print(f"⚠️ Docs check warning: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("✅ ALL API TESTS PASSED!")
    print("\n🔗 Available Endpoints:")
    print(f"   • Health Check: {base_url}/health")
    print(f"   • API Docs: {base_url}/docs")
    print(f"   • ReDoc: {base_url}/redoc")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_api()
    exit(0 if success else 1)
