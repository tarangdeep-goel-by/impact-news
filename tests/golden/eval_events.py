"""Event-based evaluation — compare engines against 16 real-world ground truth events.

Each event has a trigger, description, and 10 ranked I-world impact nodes.
Metrics: Recall@k, NDCG@10, MRR, per-event breakdown.

Usage:
    python -m tests.golden.eval_events                         # Both engines
    python -m tests.golden.eval_events --engine llm            # LLM only
    python -m tests.golden.eval_events --engine graph-direct   # Graph direct only
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
from graph.markov_engine import CausalMarkovEngine
from graph.merge import TaxonomyMerger
from graph.migrate_weights import apply_defaults
from config import settings

logger = logging.getLogger(__name__)

GT_PATH = Path(__file__).parent / "ground_truth.yaml"


# ---------------------------------------------------------------------------
# Engine wrappers
# ---------------------------------------------------------------------------


class DirectGraphEngine:
    def __init__(self, taxonomy: TaxonomyContext) -> None:
        merger = TaxonomyMerger()
        G = merger.merge()
        apply_defaults(G)
        self.engine = CausalMarkovEngine(
            G,
            i_world_boost=settings.i_world_boost,
            category_penalty=settings.category_penalty,
            leaf_boost_l4=settings.leaf_boost_l4,
            leaf_boost_l3=settings.leaf_boost_l3,
        )
        self.taxonomy = taxonomy
        self.graph = G

    def evaluate(self, event: dict) -> list[ImpactResult]:
        trigger = event["trigger"]
        if trigger not in self.graph:
            return []
        direction = event.get("direction", 1)
        results = self.engine.evaluate_impact(trigger, event_direction=direction)
        return [
            ImpactResult(
                node=r["node"],
                probability=r["probability"],
                magnitude=r["magnitude"],
                polarity=r["polarity"],
                delay=r["delay"],
                mechanism=" -> ".join(r.get("path", [])),
                path=r.get("path", []),
            )
            for r in results
        ]


class LLMEngine:
    def __init__(self, taxonomy: TaxonomyContext) -> None:
        from engine.llm_engine import LLMImpactEngine

        self._engine = LLMImpactEngine(taxonomy=taxonomy)
        self.taxonomy = taxonomy

    def evaluate(self, event: dict) -> list[ImpactResult]:
        title = f"{event['name']}"
        summary = event["description"]
        results, _meta = self._engine.evaluate_article(title, summary)
        return results


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _dcg(relevances: list[float], k: int) -> float:
    """Discounted Cumulative Gain at k."""
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
    """Compute Recall@k, NDCG@k, MRR against ground truth ranked list."""
    gt_nodes = [g["node"] for g in ground_truth[:k]]
    gt_set = set(gt_nodes)

    # Build result node list (top-k by prob*mag)
    result_nodes = [r["node"] for r in results[:50]]  # take more for recall

    # Match with ancestor/descendant flexibility
    def node_matches(result_node: str, gt_node: str) -> bool:
        if result_node == gt_node:
            return True
        if taxonomy.is_ancestor_of(result_node, gt_node):
            return True
        if taxonomy.is_ancestor_of(gt_node, result_node):
            return True
        return False

    # Recall@k: how many GT nodes appear in top-k results?
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

    # NDCG@k: assign relevance based on GT rank position
    # GT rank 1 → relevance 10, rank 2 → 9, ..., rank 10 → 1
    gt_relevance = {g["node"]: k - i for i, g in enumerate(ground_truth[:k])}

    # Build relevance vector for engine results
    result_relevances = []
    for rn in result_nodes[:k]:
        rel = 0.0
        for gt_node, gt_rel in gt_relevance.items():
            if node_matches(rn, gt_node):
                rel = gt_rel
                break
        result_relevances.append(rel)

    dcg = _dcg(result_relevances, k)
    # Ideal DCG: GT in perfect order
    ideal_rels = sorted(gt_relevance.values(), reverse=True)
    idcg = _dcg(ideal_rels, k)
    ndcg = dcg / idcg if idcg > 0 else 0.0

    # MRR: rank of first GT hit
    mrr = 0.0
    for i, rn in enumerate(result_nodes[:50]):
        for gt_node in gt_nodes:
            if node_matches(rn, gt_node):
                mrr = 1.0 / (i + 1)
                break
        if mrr > 0:
            break

    # Per-GT-node hit tracking
    hit_details = []
    for g in ground_truth[:k]:
        found_rank = None
        for i, rn in enumerate(result_nodes[:50]):
            if node_matches(rn, g["node"]):
                found_rank = i + 1
                break
        hit_details.append({
            "node": g["node"],
            "gt_rank": g["rank"],
            "engine_rank": found_rank,
            "hit": found_rank is not None,
        })

    return {
        "recall_at_k": recall_at_k,
        "recall_at_20": recall_at_20,
        "ndcg": ndcg,
        "mrr": mrr,
        "hits_at_k": len(hits_at_k),
        "total_gt": len(gt_nodes),
        "total_results": len(results),
        "hit_details": hit_details,
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Event-based engine evaluation")
    parser.add_argument(
        "--engine",
        choices=["llm", "graph-direct", "both"],
        default="both",
        help="Engine(s) to evaluate",
    )
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

    engine_names = []
    if args.engine in ("graph-direct", "both"):
        engine_names.append("graph-direct")
    if args.engine in ("llm", "both"):
        engine_names.append("llm")

    print("Loading taxonomy...", end=" ", flush=True)
    taxonomy = TaxonomyContext.from_merged_graph(settings.graph_path)
    print("done.")

    engines = {}
    for name in engine_names:
        print(f"Initializing {name}...", end=" ", flush=True)
        if name == "graph-direct":
            engines[name] = DirectGraphEngine(taxonomy)
        else:
            engines[name] = LLMEngine(taxonomy)
        print("done.")

    print(f"\nEvaluating {len(events)} events x {len(engine_names)} engines\n")

    # Header
    print(f"{'Event':<35} | {'Engine':<14} | {'R@10':>5} | {'R@20':>5} | {'NDCG':>6} | {'MRR':>5} | {'#Res':>5} | {'Time':>6} | Hits")
    print("-" * 120)

    all_metrics: dict[str, list[dict]] = {n: [] for n in engine_names}

    for event in events:
        for name in engine_names:
            t0 = time.time()
            results = engines[name].evaluate(event)
            elapsed = time.time() - t0

            m = compute_metrics(results, event["ground_truth"], taxonomy)
            m["elapsed"] = elapsed
            m["event_id"] = event["id"]
            all_metrics[name].append(m)

            # Hit summary: show which GT nodes were found
            hits = [d["node"][:20] for d in m["hit_details"] if d["hit"]]
            misses = [d["node"][:20] for d in m["hit_details"] if not d["hit"]]
            hit_str = f"{m['hits_at_k']}/{m['total_gt']}"

            print(
                f"{event['id']:<35} | {name:<14} | {m['recall_at_k']:>5.0%} | {m['recall_at_20']:>5.0%} | "
                f"{m['ndcg']:>6.3f} | {m['mrr']:>5.2f} | {m['total_results']:>5} | {elapsed:>5.1f}s | "
                f"{hit_str} {', '.join(hits[:5])}"
            )
            if misses and args.verbose:
                print(f"{'':>35}   {'':>14}   MISSED: {', '.join(misses)}")

    # Summary
    print(f"\n{'='*90}")
    print("SUMMARY")
    print(f"{'='*90}")
    print(f"{'Engine':<14} | {'Events':>6} | {'Avg R@10':>8} | {'Avg R@20':>8} | {'Avg NDCG':>9} | {'Avg MRR':>8} | {'Avg #Res':>8} | {'Avg Time':>8}")
    print("-" * 90)

    for name in engine_names:
        metrics = all_metrics[name]
        n = len(metrics)
        avg_r10 = sum(m["recall_at_k"] for m in metrics) / n
        avg_r20 = sum(m["recall_at_20"] for m in metrics) / n
        avg_ndcg = sum(m["ndcg"] for m in metrics) / n
        avg_mrr = sum(m["mrr"] for m in metrics) / n
        avg_res = sum(m["total_results"] for m in metrics) / n
        avg_time = sum(m["elapsed"] for m in metrics) / n

        print(
            f"{name:<14} | {n:>6} | {avg_r10:>8.1%} | {avg_r20:>8.1%} | "
            f"{avg_ndcg:>9.3f} | {avg_mrr:>8.3f} | {avg_res:>8.1f} | {avg_time:>7.1f}s"
        )

    print()


if __name__ == "__main__":
    main()
