import asyncio

import pytest
from src.config.settings import get_settings
from src.models.session import TaskRequestPayload
from src.models.task import TaskType
from src.services.task_orchestrator import TaskOrchestrator


class FakeDoc:
    def __init__(self, text: str):
        self.page_content = text


class FakeRetriever:
    def __init__(self, text: str):
        self._text = text

    async def aget_relevant_documents(self, _query: str):
        await asyncio.sleep(0)
        return [FakeDoc(self._text)]


@pytest.mark.asyncio
async def test_rag_v2_combines_code_and_memory(monkeypatch):
    settings_obj = get_settings()

    # Ensure flag is enabled during this test
    original_flag = settings_obj.experimental_rag_v2_enabled
    settings_obj.experimental_rag_v2_enabled = True

    try:
        # Orchestrator with only a CODE retriever injected
        code_retr = FakeRetriever("code-snippet")
        orch = TaskOrchestrator(rag_retrievers={"code": code_retr})

        # Patch helper used within orchestrator to return a MEMORY retriever
        def fake_build_retriever_dict(**_kwargs):
            return {"memory": FakeRetriever("memory-snippet")}

        monkeypatch.setattr(
            "src.services.task_orchestrator.build_retriever_dict",
            fake_build_retriever_dict,
            raising=False,
        )

        # Build request with session_id in metadata to activate memory retriever
        payload = TaskRequestPayload(
            id="t1",
            type=TaskType.BUG_FIX,
            description="Use both code and memory",
            content="fix issue with function",
            metadata={"session_id": "sess-123"},
        )

        result = await orch.execute_task(payload)
        assert result is not None
        # The pipeline should note the retrieval stage
        stages = result.metrics.get("pipeline", {}).get("stages", [])
        assert "rag_v2_retrieval" in stages
        # The request should be annotated with retrieval info including snippet_count
        snippet_info = payload.metadata.get("retrieval", {})
        assert snippet_info.get("source") == "rag_v2"
        assert snippet_info.get("snippet_count", 0) >= 2
    finally:
        settings_obj.experimental_rag_v2_enabled = original_flag
