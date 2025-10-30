import importlib
import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

MetricsService = importlib.import_module("src.services.metrics_service").MetricsService
semantic_search_module = importlib.import_module("src.services.semantic_search")
SearchCache = semantic_search_module.SearchCache
SemanticSearchService = semantic_search_module.SemanticSearchService


class _StubEmbeddingsService:
    def __init__(self):
        self.calls = 0

    async def find_similar_code(
        self,
        query: str,
        top_k: int = 5,
        file_extension=None,
    ):
        self.calls += 1
        _ = (query, top_k, file_extension)
        return [
            {
                "distance": 0.2,
                "metadata": {
                    "file_path": "backend/src/example.py",
                    "file_name": "example.py",
                    "size": 123,
                },
            }
        ]


@pytest.mark.asyncio
async def test_semantic_search_records_metrics_and_cache_stats(tmp_path):
    metrics_path = tmp_path / "metrics.json"
    metrics_service = MetricsService(metrics_path=metrics_path)
    embeddings = _StubEmbeddingsService()
    service = SemanticSearchService(
        embeddings_service=embeddings,  # type: ignore[arg-type]
        metrics_service=metrics_service,
    )

    first_results = await service.search("cache me", top_k=1)
    assert first_results
    query_metrics = metrics_service.get_model_metrics("semantic_search.query")
    assert query_metrics is not None
    assert query_metrics["calls"] == 1
    assert query_metrics["success_count"] == 1

    cached_results = await service.search("cache me", top_k=1)
    assert cached_results == first_results
    cache_metrics = metrics_service.get_model_metrics("semantic_search.cache_hit")
    assert cache_metrics is not None
    assert cache_metrics["calls"] == 1
    assert embeddings.calls == 1

    stats = service.get_cache_stats()
    assert stats["cache_hit_rate"] == pytest.approx(0.5)

    persisted = json.loads(Path(metrics_path).read_text(encoding="utf-8"))
    assert "semantic_search.query" in persisted
    assert "semantic_search.cache_hit" in persisted


def test_search_cache_clear_resets_counters():
    cache = SearchCache(maxsize=4, ttl=60.0)
    cache.put("key", "value")
    assert cache.get("key") == "value"
    assert cache.hit_rate() == pytest.approx(1.0)

    cache.clear()
    assert cache.hit_rate() == 0.0
    assert cache.cache == {}
    assert cache.timestamps == {}
