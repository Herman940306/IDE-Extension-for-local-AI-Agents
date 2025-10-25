"""
Quick diagnostic test for Router v2.0
Checks if LLM models are available and responding

Project Creator: Herman Swanepoel
"""

import asyncio

import httpx


async def test_basic_route():
    """Test basic routing endpoint"""
    print("🔍 Testing Router v2.0 Basic Routing...")
    print()

    # Increase timeout for LLM operations (they can be slow)
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Test 1: Simple math
        print("Test 1: Simple Math (1+1)")
        request1 = {
            "prompt": "1+1",
            "task_type": "general",
            "user_id": "diagnostic",
            "session_id": "diag1",
        }

        try:
            response1 = await client.post(
                "http://localhost:8001/api/v1/route", json=request1
            )
            print(f"Status: {response1.status_code}")
            data1 = response1.json()
            print(f"Response: {data1.get('text', 'NO TEXT')[:200]}")
            print(f"Verified: {data1.get('verified', 'N/A')}")
            print(f"Models: {data1.get('metadata', {}).get('models_used', [])}")
            print()
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {str(e)}")
            import traceback

            traceback.print_exc()
            print()

        # Test 2: Code generation
        print("Test 2: Code Generation")
        request2 = {
            "prompt": "def hello():",
            "task_type": "code_generation",
            "user_id": "diagnostic",
            "session_id": "diag2",
        }

        try:
            response2 = await client.post(
                "http://localhost:8001/api/v1/route", json=request2
            )
            print(f"Status: {response2.status_code}")
            data2 = response2.json()
            print(f"Response: {data2.get('text', 'NO TEXT')[:200]}")
            print(f"Has LLM: {data2.get('metadata', {}).get('uses_llm', False)}")
            print()
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {str(e)}")
            import traceback

            traceback.print_exc()
            print()

        # Test 3: Check backend health
        print("Test 3: Backend Health")
        try:
            health = await client.get("http://localhost:8001/health")
            print(f"Status: {health.status_code}")
            print(f"Response: {health.json()}")
            print()
        except Exception as e:
            print(f"❌ Error: {e}")
            print()


if __name__ == "__main__":
    asyncio.run(test_basic_route())
