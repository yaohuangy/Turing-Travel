"""RAG retrieval evaluation script."""
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.retriever import retrieve

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("eval")


def load_cases() -> list[dict]:
    cases_path = Path(__file__).parent / "eval_cases.json"
    with open(cases_path, encoding="utf-8") as f:
        return json.load(f)


def hit_rate_at_k(results: list[str], expected: list[str], k: int) -> float:
    """Compute whether at least one expected chunk is in top-k results."""
    top_k = set(results[:k])
    for exp in expected:
        if exp in top_k:
            return 1.0
    return 0.0


def reciprocal_rank(results: list[str], expected: list[str]) -> float:
    """Compute reciprocal rank of the first matching expected chunk."""
    for i, res in enumerate(results, 1):
        if res in set(expected):
            return 1.0 / i
    return 0.0


def precision_at_k(results: list[str], expected: list[str], k: int) -> float:
    """Compute precision@k."""
    top_k = set(results[:k])
    expected_set = set(expected)
    hits = len(top_k & expected_set)
    return hits / min(k, len(results)) if results else 0.0


def evaluate(cases: list[dict], use_rerank: bool = True, verbose: bool = True) -> dict:
    """Run evaluation over all test cases."""
    scores_1 = []
    scores_5 = []
    mrr_scores = []
    latencies = []
    precision_scores = []

    for case in cases:
        query = case["query"]
        city = case["city"]
        expected = case["expected_chunks"]

        start = time.perf_counter()
        results = retrieve(query, city, top_k=5, use_rerank=use_rerank)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

        result_ids = [r["id"] for r in results]

        h1 = hit_rate_at_k(result_ids, expected, 1)
        h5 = hit_rate_at_k(result_ids, expected, 5)
        mrr = reciprocal_rank(result_ids, expected)
        p5 = precision_at_k(result_ids, expected, 5)

        scores_1.append(h1)
        scores_5.append(h5)
        mrr_scores.append(mrr)
        precision_scores.append(p5)

        if verbose:
            status = "✓" if h1 else ("○" if h5 else "✗")
            print(f"  {status} {case['id']}: query='{query[:40]}' → top1={result_ids[0] if result_ids else 'N/A'}, "
                  f"expected={expected}, MRR={mrr:.3f}, {elapsed*1000:.0f}ms")

    metrics = {
        "num_cases": len(cases),
        "hit_rate@1": round(sum(scores_1) / len(scores_1), 4),
        "hit_rate@5": round(sum(scores_5) / len(scores_5), 4),
        "MRR": round(sum(mrr_scores) / len(mrr_scores), 4),
        "precision@5": round(sum(precision_scores) / len(precision_scores), 4),
        "avg_latency_ms": round(sum(latencies) / len(latencies) * 1000, 1),
        "rerank_enabled": use_rerank,
    }
    return metrics


def main():
    print("=" * 60)
    print("RAG Retrieval Evaluation")
    print("=" * 60)

    # Ensure ChromaDB is populated
    from rag.vector_db import add_documents, search
    guides_dir = Path(__file__).parent.parent / "data" / "guides"

    # Check if ChromaDB has data
    test_results = search("test", "dali", top_k=1)
    if not test_results:
        print(" indexing travel guides into ChromaDB...")
        n = add_documents(guides_dir)
        print(f"  indexed {n} chunks")
    else:
        print(f"ChromaDB already populated with guides")

    cases = load_cases()
    print(f"\nLoaded {len(cases)} test cases")
    print("-" * 40)

    # Evaluate with rerank
    print("\nWith Rerank (qwen3-rerank):")
    metrics_rerank = evaluate(cases, use_rerank=True)
    print(f"\nResults:")
    print(f"  Hit Rate@1:  {metrics_rerank['hit_rate@1']}")
    print(f"  Hit Rate@5:  {metrics_rerank['hit_rate@5']}")
    print(f"  MRR:         {metrics_rerank['MRR']}")
    print(f"  Precision@5: {metrics_rerank['precision@5']}")
    print(f"  Avg Latency: {metrics_rerank['avg_latency_ms']}ms")

    # Evaluate without rerank for comparison
    print("\nWithout Rerank (vector only):")
    metrics_vector = evaluate(cases, use_rerank=False)
    print(f"\nResults:")
    print(f"  Hit Rate@1:  {metrics_vector['hit_rate@1']}")
    print(f"  Hit Rate@5:  {metrics_vector['hit_rate@5']}")
    print(f"  MRR:         {metrics_vector['MRR']}")
    print(f"  Precision@5: {metrics_vector['precision@5']}")
    print(f"  Avg Latency: {metrics_vector['avg_latency_ms']}ms")

    # Save results
    output = {"rerank": metrics_rerank, "vector_only": metrics_vector}
    out_path = Path(__file__).parent / "eval_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
