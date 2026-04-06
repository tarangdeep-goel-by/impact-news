"""Tier 2 evaluation — impact analysis quality.

Runs Tier 2 analyzer on ground truth events and reports:
- NDCG@10: ranking quality of predicted impacts vs ground truth
- Recall@k: fraction of ground truth impacts found in top-k predictions
- Per-event breakdown

Usage:
    python -m tests.eval.tier2_eval                    # Run all events
    python -m tests.eval.tier2_eval --limit 3          # First 3 events
    python -m tests.eval.tier2_eval --event gold_price # Single event
    python -m tests.eval.tier2_eval --dry-run          # Show cases only
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import time
from pathlib import Path

from engine.llm_engine import ImpactAnalyzer
from engine.taxonomy_context import TaxonomyContext
from pipeline.gemini import GeminiClient

logger = logging.getLogger(__name__)

CASES_PATH = Path(__file__).parent / "tier2_cases.json"


def load_cases(
    path: Path = CASES_PATH,
    event: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    with open(path) as f:
        cases = json.load(f)
    if event:
        cases = [c for c in cases if event.lower() in c["id"].lower()]
    if limit:
        cases = cases[:limit]
    return cases


def dcg(relevances: list[float], k: int = 10) -> float:
    """Discounted Cumulative Gain at k."""
    return sum(
        rel / math.log2(i + 2) for i, rel in enumerate(relevances[:k])
    )


def ndcg(predicted_nodes: list[str], ground_truth: list[dict], k: int = 10) -> float:
    """NDCG@k — measures ranking quality.

    ground_truth: [{"i_node": ..., "rank": 1..10}] where rank 1 = most important.
    """
    # Build relevance scores: rank 1 → score 10, rank 10 → score 1
    gt_scores = {}
    for gt in ground_truth:
        gt_scores[gt["i_node"]] = 11 - gt["rank"]  # rank 1 → 10, rank 10 → 1

    # Predicted relevances in prediction order
    pred_rels = [gt_scores.get(node, 0.0) for node in predicted_nodes[:k]]

    # Ideal relevances (sorted descending)
    ideal_rels = sorted(gt_scores.values(), reverse=True)[:k]

    dcg_val = dcg(pred_rels, k)
    idcg_val = dcg(ideal_rels, k)

    return dcg_val / idcg_val if idcg_val > 0 else 0.0


def recall_at_k(predicted_nodes: list[str], ground_truth: list[dict], k: int = 10) -> float:
    """Recall@k — fraction of ground truth nodes found in top-k predictions."""
    gt_nodes = {gt["i_node"] for gt in ground_truth}
    pred_set = set(predicted_nodes[:k])
    if not gt_nodes:
        return 0.0
    return len(gt_nodes & pred_set) / len(gt_nodes)


def precision_at_k(predicted_nodes: list[str], ground_truth: list[dict], k: int = 10) -> float:
    """Precision@k — fraction of top-k predictions that are in ground truth."""
    gt_nodes = {gt["i_node"] for gt in ground_truth}
    pred_top = predicted_nodes[:k]
    if not pred_top:
        return 0.0
    return len(gt_nodes & set(pred_top)) / len(pred_top)


def run_eval(cases: list[dict], analyzer: ImpactAnalyzer, taxonomy: TaxonomyContext) -> list[dict]:
    """Run Tier 2 on all cases and collect results."""
    results = []

    for i, case in enumerate(cases):
        print(f"\n[{i+1}/{len(cases)}] {case['name']}", flush=True)
        print(f"  Trigger: {case['macro_shifts'][0]['t_node']} ({case['macro_shifts'][0]['trajectory']})")

        # Get filtered I-trees (exclude irrelevant L1 categories if specified)
        i_trees = taxonomy.format_i_trees()

        t0 = time.time()
        try:
            output = analyzer.analyze_new_v3(
                title=case["title"],
                summary=case["summary"],
                macro_shifts=case["macro_shifts"],
                i_trees=i_trees,
            )
            elapsed_ms = int((time.time() - t0) * 1000)
        except Exception as e:
            elapsed_ms = int((time.time() - t0) * 1000)
            print(f"  ERROR ({elapsed_ms}ms): {e}")
            results.append({**case, "pred_impacts": [], "error": str(e), "ms": elapsed_ms})
            continue

        # Extract predicted I-nodes sorted by probability*magnitude
        pred_impacts = output.get("micro_impacts", [])
        # Sort by probability * magnitude descending
        for imp in pred_impacts:
            imp["score"] = imp.get("probability", 0) * imp.get("magnitude", 0)
        pred_impacts.sort(key=lambda x: x["score"], reverse=True)
        # Filter to valid leaf nodes only (exclude L2 category IDs)
        valid_leaves = taxonomy.get_all_i_leaf_ids()
        pred_nodes = [imp["i_node"] for imp in pred_impacts if imp.get("i_node") in valid_leaves]

        # Compute metrics
        gt = case["expected_impacts"]
        ndcg_10 = ndcg(pred_nodes, gt, k=10)
        recall_10 = recall_at_k(pred_nodes, gt, k=10)
        recall_5 = recall_at_k(pred_nodes, gt, k=5)
        prec_10 = precision_at_k(pred_nodes, gt, k=10)

        # Show results
        gt_nodes = [g["i_node"] for g in gt[:5]]
        pred_top5 = pred_nodes[:5]
        hits = set(pred_nodes[:10]) & {g["i_node"] for g in gt}

        print(f"  NDCG@10: {ndcg_10:.3f} | R@10: {recall_10:.1%} | P@10: {prec_10:.1%} ({elapsed_ms}ms)")
        print(f"  GT top-5:   {gt_nodes}")
        print(f"  Pred top-5: {pred_top5}")
        print(f"  Hits@10:    {hits}")

        results.append({
            **case,
            "pred_impacts": pred_impacts[:15],
            "pred_nodes": pred_nodes,
            "ndcg_10": ndcg_10,
            "recall_10": recall_10,
            "recall_5": recall_5,
            "precision_10": prec_10,
            "error": None,
            "ms": elapsed_ms,
        })

    return results


def print_report(results: list[dict]) -> None:
    """Print evaluation report."""
    valid = [r for r in results if not r.get("error")]
    errors = len(results) - len(valid)

    print(f"\n{'='*60}")
    print(f"TIER 2 EVALUATION — {len(valid)} events ({errors} errors)")
    print(f"{'='*60}")

    if not valid:
        print("No valid results.")
        return

    avg_ndcg = sum(r["ndcg_10"] for r in valid) / len(valid)
    avg_recall_10 = sum(r["recall_10"] for r in valid) / len(valid)
    avg_recall_5 = sum(r["recall_5"] for r in valid) / len(valid)
    avg_prec_10 = sum(r.get("precision_10", 0) for r in valid) / len(valid)

    print(f"\n--- Aggregate Metrics ---")
    print(f"  NDCG@10:       {avg_ndcg:.3f}")
    print(f"  Recall@10:     {avg_recall_10:.1%}")
    print(f"  Precision@10:  {avg_prec_10:.1%}")
    print(f"  Recall@5:      {avg_recall_5:.1%}")

    # Per-event breakdown
    print(f"\n--- Per-Event ---")
    print(f"  {'Event':45s} {'NDCG':>6s} {'R@10':>6s} {'P@10':>6s} {'#pred':>5s} {'ms':>6s}")
    for r in sorted(valid, key=lambda x: x["ndcg_10"]):
        n_pred = len(r.get("pred_nodes", []))
        print(f"  {r['name']:45s} {r['ndcg_10']:6.3f} {r['recall_10']:5.0%} {r.get('precision_10',0):5.0%} {n_pred:5d} {r['ms']:5d}ms")

    # Latency
    times = [r["ms"] for r in valid]
    print(f"\n--- Latency ---")
    print(f"  Avg: {sum(times)/len(times):.0f}ms")
    print(f"  P50: {sorted(times)[len(times)//2]}ms")
    print(f"  P95: {sorted(times)[int(len(times)*0.95)]}ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tier 2 evaluation")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--event", type=str, default=None, help="Filter by event ID substring")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    cases = load_cases(event=args.event, limit=args.limit)
    print(f"Loaded {len(cases)} Tier 2 eval cases")

    if args.dry_run:
        for c in cases:
            impacts = [i["i_node"] for i in c["expected_impacts"][:3]]
            print(f"  {c['name']:45s} trigger={c['macro_shifts'][0]['t_node']:30s} top3={impacts}")
        return

    # Init
    print("Loading taxonomy...", end=" ", flush=True)
    taxonomy = TaxonomyContext.from_merged_graph("data/merged_graph.yaml")
    print("done.")

    gemini = GeminiClient()
    analyzer = ImpactAnalyzer(taxonomy, gemini)

    # Run
    results = run_eval(cases, analyzer, taxonomy)
    print_report(results)

    # Save
    out_path = Path(__file__).parent / "tier2_results.json"
    with open(out_path, "w") as f:
        json.dump({"results": results}, f, indent=2, default=str)
    print(f"\nDetailed results saved to {out_path}")


if __name__ == "__main__":
    main()
