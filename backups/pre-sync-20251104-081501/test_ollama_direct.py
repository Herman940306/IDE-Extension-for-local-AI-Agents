"""Test Ollama connection directly"""

import ollama

print("Testing direct Ollama connection...")

# Create client with explicit URL
client = ollama.Client(host="http://localhost:11434")
print(f"Using host: {client._client.base_url}")

try:
    # Test connection
    response = client.chat(
        model="qwen3:8b",
        messages=[{"role": "user", "content": "Say hello in one short sentence"}],
    )

    print("✅ SUCCESS!")
    print(f"Response: {response['message']['content']}")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback

    traceback.print_exc()
