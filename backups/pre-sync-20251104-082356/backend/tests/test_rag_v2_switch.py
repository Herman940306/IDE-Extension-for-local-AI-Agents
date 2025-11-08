import logging

import pytest
from src.config.settings import get_settings
from src.models.session import TaskRequestPayload
from src.models.task import TaskType
from src.services.task_orchestrator import TaskOrchestrator


@pytest.mark.asyncio
async def test_rag_v2_flag_switch(monkeypatch):
    orchestrator = TaskOrchestrator()
    settings_obj = get_settings()
    original_flag = settings_obj.experimental_rag_v2_enabled
    original_rag_enabled = getattr(orchestrator, "_rag_enabled", False)

    # Ensure the settings flag is restored after the test finishes
    monkeypatch.setattr(
        settings_obj,
        "experimental_rag_v2_enabled",
        original_flag,
        raising=False,
    )
    monkeypatch.setattr(
        orchestrator,
        "_rag_enabled",
        original_rag_enabled,
        raising=False,
    )

    for flag in (False, True):
        settings_obj.experimental_rag_v2_enabled = flag
        orchestrator._rag_enabled = flag  # simulate injected retriever
        logging.info(
            "Flag %s: RAG v2 %s",
            flag,
            "active" if flag else "fallback",
        )
        payload = TaskRequestPayload(
            id=f"rag-v2-{flag}",
            type=TaskType.BUG_FIX,
            description="Summarize recent project changes",
            content="print('context for retrieval smoke test')",
        )
        result = await orchestrator.execute_task(payload)
        assert result is not None
