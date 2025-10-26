"""Test LLM Manager directly from DI container"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from src.core.container import Container


async def main():
    print("Testing LLM Manager from DI Container...")
    print()

    # Initialize container
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    print("✅ Container initialized")

    # Get LLM manager
    llm_manager = container.llm_manager()
    print(f"✅ LLM Manager: {llm_manager}")
    print(f"   Provider: {llm_manager.provider}")
    print(f"   Model: {llm_manager.model}")
    print(f"   Base URL: {llm_manager.base_url}")
    print()

    # Try to generate
    print("Testing LLM generation...")
    try:
        response = await llm_manager.generate(
            prompt="Say hello in one sentence", model="qwen3:8b"
        )
        print("✅ SUCCESS!")
        print(f"Response: {response}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
