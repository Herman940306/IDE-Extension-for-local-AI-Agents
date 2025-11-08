"""Helper utilities for constructing retrieval adapters."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.config import get_settings
from src.services.memory_service import MemoryService
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
    settings = get_settings()

    # Only attempt to import LangChain adapters when the experimental flag is ON
    # to avoid heavy optional dependencies during test collection/import.
    if not getattr(settings, "experimental_rag_v2_enabled", False):
        return {}

    try:
        from src.services.retrieval.langchain_retrievers import (  # noqa: WPS433
            LANGCHAIN_AVAILABLE,
            ChatMemoryRetriever,
            CodeBaseRetriever,
        )
    except Exception:  # pragma: no cover - optional dependency not present
        return {}

    if not LANGCHAIN_AVAILABLE:
        return {}

    retrievers: Dict[str, Any] = {}

    if semantic_search is not None:
        retrievers["code"] = CodeBaseRetriever(
            semantic_search=semantic_search,
            top_k=int(getattr(settings, "rag_v2_code_top_k", 5)),
            min_relevance=float(getattr(settings, "rag_v2_min_relevance", 0.0)),
        )

    if memory_service is not None and session_id:
        retrievers["memory"] = ChatMemoryRetriever(
            memory_service=memory_service,
            session_id=session_id,
            limit=int(getattr(settings, "rag_v2_memory_message_limit", 20)),
        )

    return retrievers
