"""Quick manual test of Router v2.0"""

import asyncio

import httpx


async def main():
    print("Testing Router v2.0...")

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Simple test
        request = {
            "prompt": "Write a hello world function in Python",
            "task_type": "code_generation",
            "user_id": "test",
            "session_id": "test1",
        }

        print("Sending request...")
        print(f"Prompt: {request['prompt']}")
        print("Waiting for response (this may take 30-60 seconds)...")

        try:
            response = await client.post("http://localhost:8001/api/v1/route", json=request)

            print(f"\nStatus: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("\n✅ SUCCESS!")
                print(f"\nResponse text:\n{data.get('text', 'NO TEXT')}")
                print("\nMetadata:")
                print(f"  Uses LLM: {data.get('metadata', {}).get('uses_llm', False)}")
                print(f"  Models: {data.get('metadata', {}).get('models_used', [])}")
                print(f"  Verified: {data.get('verified', 'N/A')}")
            else:
                print(f"❌ Error: {response.text}")

        except httpx.ReadTimeout:
            print("❌ Request timed out after 120 seconds")
            print("This usually means:")
            print("  - Models are taking too long to respond")
            print("  - Check Ollama is running properly")
            print("  - Check backend logs for errors")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
