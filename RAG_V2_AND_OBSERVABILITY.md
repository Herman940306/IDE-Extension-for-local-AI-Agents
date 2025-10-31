# AuraIA Project Documentation: RAG v2 & Observability

**Project Creator:** Herman Swanepoel
**Version:** 2.0.0

---

## 1. RAG v2: Advanced Retrieval Architecture

The `feat/rag-v2-observability-and-context` branch introduces a significant upgrade to the Retrieval-Augmented Generation pipeline. This new architecture is designed to improve the relevance and accuracy of contextual information provided to the LLM, leading to more precise and helpful AI responses.

### Key Features of RAG v2

* **Hybrid Fusion Retrieval:**
  * RAG v2 moves beyond simple vector similarity by implementing a **hybrid fusion** approach. It combines traditional lexical search (like BM25) with modern semantic vector search.
  * This allows the system to find documents that are both **lexically relevant** (containing exact keywords) and **semantically relevant** (matching the query's intent).
  * The balance between these two search methods is configurable, allowing for fine-tuning of retrieval performance.

* **Optional Cross-Encoder Reranking:**
  * After an initial set of candidate documents is retrieved, an optional **Cross-Encoder reranking model** can be applied.
  * Unlike simpler models, a Cross-Encoder directly compares the user's query with each document, providing a much more accurate relevance score. This step filters out noise and ensures only the most relevant context is passed to the LLM.

* **Configurable Pipeline:**
  * The entire RAG v2 pipeline is controlled by feature flags, allowing for incremental rollouts and A/B testing. Key configuration options include:
    * Enabling/disabling the RAG v2 pipeline.
    * Tuning the weights for hybrid fusion.
    * Specifying the reranker model.
    * Setting relevance thresholds and the number of documents to retrieve (`top_k`).

### Architectural Diagram: RAG v2

```
┌─────────────────────────────────────────────────────────┐
│                      User Query                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                 Hybrid Fusion Retrieval                  │
│   ┌──────────────────────────┬────────────────────────┐   │
│   │   Semantic Search        │   Lexical Search       │   │
│   │   (Vector Similarity)    │   (BM25/Keyword)       │   │
│   └──────────────────────────┴────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │ (Initial Candidate Documents)
                     ▼
┌─────────────────────────────────────────────────────────┐
│           Optional: Cross-Encoder Reranking              │
│      (Filters and re-scores for higher accuracy)         │
└────────────────────┬────────────────────────────────────┘
                     │ (Final, High-Relevance Context)
                     ▼
┌─────────────────────────────────────────────────────────┐
│                Large Language Model (LLM)                │
│ (Receives query + finely-tuned context for generation)   │
└─────────────────────────────────────────────────────────┘
```

## 2. Observability & Debugging

To support the complexity of the RAG v2 pipeline, a lightweight observability and debugging framework has been introduced.

### Key Features

* **Debug Endpoints:**
  * New API endpoints provide real-time visibility into the RAG pipeline's internal state.
  * `GET /debug/rag_trace`: Returns detailed traces of recent retrieval operations, including the scores for each considered document.
  * `GET /config/rag`: Shows the currently active RAG configuration, making it easy to verify settings.

* **Prometheus Metrics:**
  * The system now exposes key performance indicators in a **Prometheus-compatible format**. This allows for easy integration with modern monitoring and alerting systems like Grafana.
  * Tracked metrics include:
    * The total number of documents considered and kept.
    * The mean fusion score, providing insight into retrieval relevance.

* **Debounced File Watching:**
  * The system watches for file changes to keep embeddings up-to-date. This process is now **debounced**, preventing excessive and redundant updates during operations like branch switching or large refactors.

## 3. How to Use & Configure

The new features are managed via environment variables or a settings file.

* **Enable RAG v2:**
  * `experimental_rag_v2_enabled=true`

* **Configure Hybrid Fusion:**
  * `hybrid_fusion_enabled=true`
  * `fusion_weight_vector=0.6` (weight for semantic search)
  * `fusion_weight_bm25=0.4` (weight for lexical search)

* **Enable Reranking:**
  * `reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2"`

* **Access Debug Information:**
  * Navigate to `http://127.0.0.1:8001/debug/rag_trace` in your browser while the backend is running.
