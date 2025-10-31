from fastapi.testclient import TestClient
from src.main import app as main_app
from src.services.retrieval.trace import RetrievalDocTrace, retrieval_trace_buffer


def _make_client() -> TestClient:
    return TestClient(main_app)


def test_rag_config_endpoint_returns_expected_fields() -> None:
    client = _make_client()

    response = client.get("/config/rag")
    assert response.status_code == 200

    payload = response.json()

    expected_fields = {
        "experimental_rag_v2_enabled",
        "hybrid_fusion_enabled",
        "fusion_weight_vector",
        "fusion_weight_bm25",
        "reranker_model",
        "relevance_threshold",
        "rag_v2_code_top_k",
    }
    assert expected_fields.issubset(payload.keys())


def test_rag_trace_endpoint_exposes_buffer_snapshot() -> None:
    retrieval_trace_buffer.clear()
    retrieval_trace_buffer.append(
        RetrievalDocTrace(
            file="src/example.py",
            vector_score=0.8,
            lexical_score=0.4,
            fusion_score=0.68,
            kept_after_threshold=True,
            extras={"stage": "rag_v2", "event": "kept"},
        )
    )

    client = _make_client()
    response = client.get("/debug/rag_trace")
    assert response.status_code == 200

    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["file"] == "src/example.py"


def test_rag_overview_endpoint_summarizes_recent_traces() -> None:
    retrieval_trace_buffer.clear()
    retrieval_trace_buffer.append(
        RetrievalDocTrace(
            file="src/foo.py",
            vector_score=0.9,
            lexical_score=0.5,
            fusion_score=0.78,
            kept_after_threshold=True,
            extras={"stage": "rag_v2", "event": "considered"},
        )
    )
    retrieval_trace_buffer.append(
        RetrievalDocTrace(
            file="src/bar.py",
            vector_score=0.2,
            lexical_score=0.1,
            fusion_score=0.18,
            kept_after_threshold=False,
            extras={"stage": "rag_v2", "event": "considered"},
        )
    )

    client = _make_client()
    response = client.get("/debug/rag_overview")
    assert response.status_code == 200

    payload = response.json()

    assert payload["count"] == 2
    means = payload["means"]
    assert set(means.keys()) == {"vector", "lexical", "fusion"}

    top_files = payload["top_files"]
    assert any(entry["file"] == "src/foo.py" for entry in top_files)
