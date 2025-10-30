"""Helper utilities for constructing retrieval adapters."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.config import get_settings
from src.services.memory_service import MemoryService
from src.services.retrieval.langchain_retrievers import (
    LANGCHAIN_AVAILABLE,
    ChatMemoryRetriever,
    CodeBaseRetriever,
)
from src.services.semantic_search import SemanticSearchService


def build_retriever_dict(
    *,
    semantic_search: Optional[SemanticSearchService] = None,
    memory_service: Optional[MemoryService] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return LangChain retrievers when dependencies are available.

    The helper keeps the legacy pipeline untouched by returning an empty dictionary
    when LangChain is missing or required services are not supplied. Callers can
    provide the semantic search and memory services from the DI container to obtain
    fully configured retrievers for the experimental RAG v2 path.
    """

    if not LANGCHAIN_AVAILABLE:
        return {}

    settings = get_settings()
    rag_cfg = settings.rag_v2

    retrievers: Dict[str, Any] = {}

    if semantic_search is not None:
        retrievers["code"] = CodeBaseRetriever(
            semantic_search=semantic_search,
            top_k=rag_cfg.code_top_k,
            min_relevance=rag_cfg.code_min_relevance,
        )

    if memory_service is not None and session_id:
        retrievers["memory"] = ChatMemoryRetriever(
            memory_service=memory_service,
            session_id=session_id,
            limit=rag_cfg.memory_message_limit,
        )

    return retrievers
