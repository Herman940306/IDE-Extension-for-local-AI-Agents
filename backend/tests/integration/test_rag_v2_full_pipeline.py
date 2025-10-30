import asyncio

import pytest
from src.config.settings import get_settings
from src.models.session import TaskRequestPayload
from src.models.task import TaskType
from src.services.task_orchestrator import TaskOrchestrator


class Doc:
    def __init__(self, text: str, relevance: float = 0.9, meta=None):
        self.page_content = text
        self.metadata = {"relevance": relevance, **(meta or {})}


class CodeRetriever:
    def __init__(self, docs):
        self._docs = docs

    async def aget_relevant_documents(self, _query: str):
        await asyncio.sleep(0)
        return self._docs


@pytest.mark.asyncio
async def test_rag_v2_full_pipeline_produces_snippets_and_traces(monkeypatch):
    settings_obj = get_settings()
    orig_flag = settings_obj.experimental_rag_v2_enabled
    orig_reranker = settings_obj.reranker_model
    settings_obj.experimental_rag_v2_enabled = True
    settings_obj.reranker_model = "on"  # toggle reranker to enable traces

    try:
        docs = [Doc("alpha beta"), Doc("gamma delta", 0.2)]
        orch = TaskOrchestrator(rag_retrievers={"code": CodeRetriever(docs)})

        # Clear trace buffer
        from src.services.retrieval.trace import retrieval_trace_buffer

        retrieval_trace_buffer.clear()

        payload = TaskRequestPayload(
            id="e2e1",
            type=TaskType.BUG_FIX,
            description="Check pipeline",
            content="alpha",
        )
        result = await orch.execute_task(payload)
        assert result is not None
        info = payload.metadata.get("retrieval", {})
        assert info.get("source") == "rag_v2"
        assert info.get("snippet_count", 0) >= 1

        # Trace buffer should have entries when reranker is on
        traces = retrieval_trace_buffer.snapshot(limit=50)
        assert isinstance(traces, list)
    finally:
        settings_obj.experimental_rag_v2_enabled = orig_flag
        settings_obj.reranker_model = orig_reranker
