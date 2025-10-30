"""LangChain-compatible retriever adapters."""

from __future__ import annotations

from typing import Any, List, Optional

try:  # pragma: no cover - runtime dependency resolution
    from langchain.schema import BaseRetriever, Document  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - handled lazily
    LANGCHAIN_AVAILABLE = False
    LANGCHAIN_IMPORT_ERROR: Optional[ModuleNotFoundError] = exc

    class BaseRetriever:  # type: ignore[no-redef]
        """Fallback base class when LangChain is unavailable."""

    class Document:  # type: ignore[no-redef]
        """Fallback Document that raises if LangChain is missing."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError(
                "LangChain is not installed. Install 'langchain' to enable " "experimental_rag_v2."
            )

else:  # pragma: no cover - simple constant assignment
    LANGCHAIN_AVAILABLE = True
    LANGCHAIN_IMPORT_ERROR = None
from src.services.memory_service import MemoryService, MessageType
from src.services.semantic_search import SemanticSearchService


class CodeBaseRetriever(BaseRetriever):  # type: ignore[misc]
    """Expose the SemanticSearchService through the LangChain retriever API."""

    def __init__(
        self,
        semantic_search: SemanticSearchService,
        top_k: int = 5,
        min_relevance: float = 0.0,
    ):
        if not LANGCHAIN_AVAILABLE:
            raise RuntimeError(
                "LangChain dependency missing. Install 'langchain' or disable "
                "experimental_rag_v2."
            ) from LANGCHAIN_IMPORT_ERROR
        self._service = semantic_search
        self._top_k = top_k
        self._min_relevance = min_relevance

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        results = await self._service.search(
            query=query,
            top_k=self._top_k,
            min_relevance=self._min_relevance,
        )
        documents: List[Document] = []
        for entry in results:
            text = entry.get("code") or entry.get("snippet") or ""
            metadata = entry.get("metadata", {})
            metadata.setdefault("relevance", entry.get("relevance"))
            documents.append(Document(page_content=text, metadata=metadata))
        return documents

    def _get_relevant_documents(self, query: str) -> List[Document]:  # pragma: no cover
        raise NotImplementedError("Use the async interface (_aget_relevant_documents)")


class ChatMemoryRetriever(BaseRetriever):  # type: ignore[misc]
    """Retrieve conversational snippets from MemoryService for LangChain chains."""

    def __init__(
        self,
        memory_service: MemoryService,
        session_id: str,
        limit: int = 20,
        message_types: Optional[List[MessageType]] = None,
    ):
        if not LANGCHAIN_AVAILABLE:
            raise RuntimeError(
                "LangChain dependency missing. Install 'langchain' or disable "
                "experimental_rag_v2."
            ) from LANGCHAIN_IMPORT_ERROR
        self._memory = memory_service
        self._session_id = session_id
        self._limit = limit
        self._message_types = message_types

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        _ = query  # Query is part of the interface; memory retrieval ignores it.
        history = await self._memory.get_session_history(
            session_id=self._session_id,
            limit=self._limit,
            message_types=self._message_types,
        )
        documents: List[Document] = []
        for message in history:
            metadata: dict[str, Any] = {
                "message_type": message.type.value,
                "timestamp": message.timestamp,
            }
            metadata.update(message.metadata or {})
            documents.append(Document(page_content=message.content, metadata=metadata))
        return documents

    def _get_relevant_documents(self, query: str) -> List[Document]:  # pragma: no cover
        raise NotImplementedError("Use the async interface (_aget_relevant_documents)")


__all__ = [
    "ChatMemoryRetriever",
    "CodeBaseRetriever",
    "LANGCHAIN_AVAILABLE",
    "LANGCHAIN_IMPORT_ERROR",
]
