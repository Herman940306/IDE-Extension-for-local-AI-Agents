"""Test Task Orchestrator directly"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from src.core.container import Container
from src.models.session import TaskRequestPayload
from src.models.task import TaskType


async def main():
    print("Testing Task Orchestrator...")
    print()

    # Initialize container
    container = Container()
    container.init_resources()

    # Get task orchestrator
    orchestrator = container.task_orchestrator()
    print(f"✅ Task Orchestrator: {orchestrator}")
    print(f"   LLM Manager: {orchestrator.llm_manager}")
    print(f"   Reasoner: {orchestrator._reasoner}")
    print(f"   Reasoner LLM Manager: {orchestrator._reasoner.llm_manager}")
    print()

    # Create a simple task
    task = TaskRequestPayload(
        id="test-1",
        type=TaskType.CODE_GENERATION,
        description="Write a hello world function",
        content="",
        user_id="test-user",
        session_id="test-session",
    )

    print("Executing task...")
    try:
        result = await orchestrator.execute_task(task)
        print("✅ SUCCESS!")
        print(f"Text: {result.text[:200]}")
        print(f"Metadata: {result.metadata}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
