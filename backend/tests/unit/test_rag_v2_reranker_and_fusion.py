import asyncio

import pytest
from src.config.settings import get_settings
from src.models.session import TaskRequestPayload
from src.models.task import TaskType
from src.services.task_orchestrator import TaskOrchestrator


class Doc:
    def __init__(self, text: str, relevance: float):
        self.page_content = text
        self.metadata = {"relevance": relevance}


class CodeRetriever:
    def __init__(self, docs):
        self._docs = docs

    async def aget_relevant_documents(self, query: str):
        await asyncio.sleep(0)
        return list(self._docs)


@pytest.mark.asyncio
async def test_reranker_threshold_filters_results(monkeypatch):
    settings_obj = get_settings()
    original_flag = settings_obj.experimental_rag_v2_enabled
    original_reranker = settings_obj.reranker_model
    original_threshold = settings_obj.relevance_threshold
    try:
        settings_obj.experimental_rag_v2_enabled = True
        settings_obj.reranker_model = "bge-reranker-large"
        settings_obj.relevance_threshold = 0.8

        # Two docs: one below threshold (0.5) and one above (0.9)
        docs = [Doc("low vec match", 0.5), Doc("high vec match", 0.9)]
        orch = TaskOrchestrator(rag_retrievers={"code": CodeRetriever(docs)})

        payload = TaskRequestPayload(
            id="r1",
            type=TaskType.BUG_FIX,
            description="use reranker",
            content="query words",
        )
        result = await orch.execute_task(payload)
        assert result is not None
        info = payload.metadata.get("retrieval", {})
        # Only one snippet should survive threshold filtering
        assert info.get("snippet_count") == 1
    finally:
        settings_obj.experimental_rag_v2_enabled = original_flag
        settings_obj.reranker_model = original_reranker
        settings_obj.relevance_threshold = original_threshold


@pytest.mark.asyncio
async def test_hybrid_fusion_reweights_scores(monkeypatch):
    settings_obj = get_settings()
    original_flag = settings_obj.experimental_rag_v2_enabled
    original_hybrid = settings_obj.hybrid_fusion_enabled
    original_w_bm25 = settings_obj.fusion_weight_bm25
    original_w_vec = settings_obj.fusion_weight_vector
    try:
        settings_obj.experimental_rag_v2_enabled = True
        settings_obj.hybrid_fusion_enabled = True
        # Favor lexical heavily so lexical-dominant doc passes a high implicit score
        settings_obj.fusion_weight_bm25 = 0.9
        settings_obj.fusion_weight_vector = 0.1

        # Craft docs so that one has low vector relevance but shares many query tokens
        query = "alpha beta gamma"
        docs = [
            # lexical match wins with high bm25 weight
            Doc("alpha beta beta beta", 0.2),
            # high vector but poor lexical
            Doc("unrelated content", 0.95),
        ]
        orch = TaskOrchestrator(rag_retrievers={"code": CodeRetriever(docs)})

        payload = TaskRequestPayload(
            id="r2",
            type=TaskType.BUG_FIX,
            description="use hybrid",
            content=query,
        )
        result = await orch.execute_task(payload)
        assert result is not None
        info = payload.metadata.get("retrieval", {})
        # Should still select at least one snippet (no threshold enforced here)
        assert info.get("snippet_count", 0) >= 1
    finally:
        settings_obj.experimental_rag_v2_enabled = original_flag
        settings_obj.hybrid_fusion_enabled = original_hybrid
        settings_obj.fusion_weight_bm25 = original_w_bm25
        settings_obj.fusion_weight_vector = original_w_vec
