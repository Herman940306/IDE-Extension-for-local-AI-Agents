# Ranking Evaluation Harness (Draft)

This document outlines a lightweight evaluation approach for the GitHub ranking feature.

## Goals

- Measure correlation between heuristic and semantic scores.
- Track stability of top-N repositories/issues/PRs across changes.
- Provide regression indicators when modifying ULTRA modes.

## Dataset

Curate a small JSON dataset: `evaluation/sample_ranking_set.json`

Structure:
```jsonc
[
  {
    "query": "performance bug fix",
    "expected_top_repo_full_names": ["owner/core-lib", "owner/engine"],
    "focus_repos": ["owner/core-lib", "owner/engine", "owner/ui-module"],
    "notes": "Core-lib is dense in perf commits; engine has active bug triage"
  }
]
```

## Metrics

| Metric | Description |
|--------|-------------|
| TopHit@K | Fraction of expected repos appearing in top K |
| MeanRank | Average rank position of expected repos |
| Stability@K | Jaccard similarity of top K vs previous run |
| ULTRAImpact | Delta in MeanRank when switching heuristic vs ULTRA |

## Procedure

1. For each dataset entry, run `rank_repos` and `rank_all` across modes: disabled, mock, local, backend.
2. Collect ranking arrays and compute metrics.
3. Output a summary table + JSON report (`evaluation/report.json`).

## Implementation Sketch (Python)

```python
import json, requests
MODES = ["disabled","mock","local","backend"]
BASE = "http://127.0.0.1:8001"

def run(query, mode):
    r = requests.post(f"{BASE}/mcp/github/rank_repos", json={"query": query, "ultraMode": mode})
    r.raise_for_status()
    return r.json().get("ranking", [])

def top_hit_at_k(expected, ranking, k):
    names = [x.get("repo",{}).get("full_name") for x in ranking[:k] if x.get("repo")]
    return len(set(expected) & set(names)) / max(1,len(expected))

def mean_rank(expected, ranking):
    pos = []
    for e in expected:
        for i,r in enumerate(ranking):
            if r.get("repo",{}).get("full_name") == e:
                pos.append(i+1); break
    return sum(pos)/len(pos) if pos else float('inf')

with open("evaluation/sample_ranking_set.json") as f:
    dataset = json.load(f)

report = []
for entry in dataset:
    q = entry["query"]; expected = entry["expected_top_repo_full_names"]
    prev_top = None
    for m in MODES:
        ranking = run(q,m)
        stability = None
        topk = [x.get("repo",{}).get("full_name") for x in ranking[:10]]
        if prev_top:
            inter = len(set(prev_top)&set(topk)); union = len(set(prev_top)|set(topk))
            stability = inter/union if union else 1.0
        prev_top = topk
        report.append({
            "query": q,
            "mode": m,
            "topHit@10": top_hit_at_k(expected, ranking, 10),
            "meanRank": mean_rank(expected, ranking),
            "stability@10": stability,
        })

with open("evaluation/report.json","w") as f:
    json.dump(report,f,indent=2)
print("Wrote evaluation/report.json")
```

## Next Steps

- Automate execution in CI nightly (optional).
- Add PR comment bot summarizing metric deltas.
- Expand dataset over time (coverage: perf, security, refactor, reliability queries).

## References

- `aitk-get_evaluation_code_gen_best_practices` for comprehensive evaluation guidance.
