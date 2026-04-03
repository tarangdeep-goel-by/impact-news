"""Event-based evaluation — test LLM engine against 16 real-world ground truth events.

Each event has a trigger, description, and 10 ranked I-world impact nodes.
Metrics: Recall@k, NDCG@10, MRR, per-event breakdown.

Usage:
    python -m tests.golden.eval_events                         # Run all events
    python -m tests.golden.eval_events --event gold_price      # Single event (substring)
"""

from __future__ import annotations

import argparse
import logging
import math
import time
from pathlib import Path

import yaml

from engine.base import ImpactResult
from engine.taxonomy_context import TaxonomyContext
from engine.llm_engine import ImpactAnalyzer
from config import settings

logger = logging.getLogger(__name__)

GT_PATH = Path(__file__).parent / "ground_truth.yaml"


# ---------------------------------------------------------------------------
# Engine wrapper
# ---------------------------------------------------------------------------


class LLMEngine:
    def __init__(self, taxonomy: TaxonomyContext) -> None:
        self._engine = ImpactAnalyzer(taxonomy=taxonomy)
        self.taxonomy = taxonomy

    def evaluate(self, event: dict) -> list[ImpactResult]:
        title = event["name"]
        summary = event["description"]
        result = self._engine.analyze_new(title, summary)
        results = result["impacts"]
        return results


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _dcg(relevances: list[float], k: int) -> float:
    score = 0.0
    for i, rel in enumerate(relevances[:k]):
        score += rel / math.log2(i + 2)
    return score


def compute_metrics(
    results: list[ImpactResult],
    ground_truth: list[dict],
    taxonomy: TaxonomyContext,
    k: int = 10,
) -> dict:
    gt_nodes = [g["node"] for g in ground_truth[:k]]
    result_nodes = [r["node"] for r in results[:50]]

    def node_matches(result_node: str, gt_node: str) -> bool:
        if result_node == gt_node:
            return True
        if taxonomy.is_ancestor_of(result_node, gt_node):
            return True
        if taxonomy.is_ancestor_of(gt_node, result_node):
            return True
        return False

    # Recall@k
    hits_at_k = set()
    for gt_node in gt_nodes:
        for rn in result_nodes[:k]:
            if node_matches(rn, gt_node):
                hits_at_k.add(gt_node)
                break
    recall_at_k = len(hits_at_k) / len(gt_nodes) if gt_nodes else 0.0

    # Recall@20
    hits_at_20 = set()
    for gt_node in gt_nodes:
        for rn in result_nodes[:20]:
            if node_matches(rn, gt_node):
                hits_at_20.add(gt_node)
                break
    recall_at_20 = len(hits_at_20) / len(gt_nodes) if gt_nodes else 0.0

    # NDCG@k
    gt_relevance = {g["node"]: k - i for i, g in enumerate(ground_truth[:k])}
    result_relevances = []
    for rn in result_nodes[:k]:
        rel = 0.0
        for gt_node, gt_rel in gt_relevance.items():
            if node_matches(rn, gt_node):
                rel = gt_rel
                break
        result_relevances.append(rel)

    dcg = _dcg(result_relevances, k)
    ideal_rels = sorted(gt_relevance.values(), reverse=True)
    idcg = _dcg(ideal_rels, k)
    ndcg = dcg / idcg if idcg > 0 else 0.0

    # MRR
    mrr = 0.0
    for i, rn in enumerate(result_nodes[:50]):
        for gt_node in gt_nodes:
            if node_matches(rn, gt_node):
                mrr = 1.0 / (i + 1)
                break
        if mrr > 0:
            break

    return {
        "recall_at_k": recall_at_k,
        "recall_at_20": recall_at_20,
        "ndcg": ndcg,
        "mrr": mrr,
        "hits_at_k": len(hits_at_k),
        "total_gt": len(gt_nodes),
        "total_results": len(results),
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Event-based LLM engine evaluation")
    parser.add_argument("--event", type=str, default=None, help="Filter by event ID (substring)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    with open(GT_PATH) as f:
        data = yaml.safe_load(f)
    events = data.get("events", [])

    if args.event:
        events = [e for e in events if args.event in e["id"]]
        if not events:
            print(f"No events matching '{args.event}'")
            return

    print("Loading taxonomy...", end=" ", flush=True)
    taxonomy = TaxonomyContext.from_merged_graph(settings.graph_path)
    print("done.")

    print(f"Initializing LLM engine...", end=" ", flush=True)
    engine = LLMEngine(taxonomy)
    print("done.")

    print(f"\nEvaluating {len(events)} events\n")
    print(f"{'Event':<35} | {'R@10':>5} | {'R@20':>5} | {'NDCG':>6} | {'MRR':>5} | {'#Res':>5} | {'Time':>6} | Hits")
    print("-" * 110)

    all_metrics: list[dict] = []

    for event in events:
        t0 = time.time()
        results = engine.evaluate(event)
        elapsed = time.time() - t0

        m = compute_metrics(results, event["ground_truth"], taxonomy)
        m["elapsed"] = elapsed
        m["event_id"] = event["id"]
        all_metrics.append(m)

        hits = [d for d in event["ground_truth"][:10]
                if any(r["node"] == d["node"] or
                       taxonomy.is_ancestor_of(r["node"], d["node"]) or
                       taxonomy.is_ancestor_of(d["node"], r["node"])
                       for r in results)]
        hit_names = [h["node"][:20] for h in hits]

        print(
            f"{event['id']:<35} | {m['recall_at_k']:>5.0%} | {m['recall_at_20']:>5.0%} | "
            f"{m['ndcg']:>6.3f} | {m['mrr']:>5.2f} | {m['total_results']:>5} | {elapsed:>5.1f}s | "
            f"{m['hits_at_k']}/{m['total_gt']} {', '.join(hit_names[:5])}"
        )

    # Summary
    n = len(all_metrics)
    if n:
        print(f"\n{'='*70}")
        print(
            f"AVG: R@10={sum(m['recall_at_k'] for m in all_metrics)/n:.1%}  "
            f"NDCG={sum(m['ndcg'] for m in all_metrics)/n:.3f}  "
            f"MRR={sum(m['mrr'] for m in all_metrics)/n:.3f}  "
            f"Time={sum(m['elapsed'] for m in all_metrics)/n:.1f}s"
        )


if __name__ == "__main__":
    main()
