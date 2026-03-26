"""Historical event replay with NDCG@10 scoring.

Validates PPR rankings against real-world ground truth events.

Usage:
    python -m audit.event_replay                        # Run all events
    python -m audit.event_replay crude_2022 rbi_2022    # Specific events
    python -m audit.event_replay --verbose              # Show full rankings
    python -m audit.event_replay --json                 # Output JSON
"""

from __future__ import annotations

import argparse
import json
import math
import logging
import sys
from pathlib import Path

import yaml

from graph.merge import TaxonomyMerger
from graph.migrate_weights import apply_defaults
from graph.markov_engine import CausalMarkovEngine

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
GROUND_TRUTH_PATH = ROOT / "taxonomy" / "eval_results" / "ground_truth.yaml"


# ---------------------------------------------------------------------------
# NDCG implementation
# ---------------------------------------------------------------------------


def dcg_at_k(relevances: list[float], k: int = 10) -> float:
    """Discounted Cumulative Gain at position k."""
    dcg = 0.0
    for i, rel in enumerate(relevances[:k]):
        dcg += rel / math.log2(i + 2)  # i+2 because positions are 1-indexed
    return dcg


def ndcg_at_k(predicted_nodes: list[str], ground_truth: list[dict], k: int = 10) -> float:
    """Normalized DCG@k. ground_truth is [{node, rank, ...}] sorted by rank asc."""
    # Build relevance lookup from ground truth
    relevance_map = {}
    for i, item in enumerate(ground_truth):
        # Relevance = (n - rank) / n where rank is 0-indexed position
        relevance_map[item["node"]] = len(ground_truth) - i

    # Actual DCG from predicted ranking
    actual_rels = [relevance_map.get(n, 0) for n in predicted_nodes[:k]]
    actual_dcg = dcg_at_k(actual_rels, k)

    # Ideal DCG (ground truth in perfect order)
    ideal_rels = sorted(relevance_map.values(), reverse=True)
    ideal_dcg = dcg_at_k(ideal_rels, k)

    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


# ---------------------------------------------------------------------------
# Ground truth loading
# ---------------------------------------------------------------------------


def load_ground_truth(path: Path | None = None) -> list[dict]:
    """Load event definitions from ground_truth.yaml."""
    p = path or GROUND_TRUTH_PATH
    if not p.exists():
        print(f"Error: ground truth file not found: {p}")
        sys.exit(1)
    data = yaml.safe_load(p.read_text())
    return data.get("events", []) or []


# ---------------------------------------------------------------------------
# Event evaluation
# ---------------------------------------------------------------------------


def evaluate_event(
    engine: CausalMarkovEngine,
    graph,
    event: dict,
    verbose: bool = False,
) -> dict:
    """Run PPR for one event and compute NDCG@10 against ground truth.

    Returns dict with event_id, ndcg, hits, misses, false_positives, details.
    """
    trigger = event["trigger"]
    direction = event.get("direction", 1)
    gt_items = event["ground_truth"]

    # Check which ground truth nodes exist in the graph
    missing_nodes = [item["node"] for item in gt_items if item["node"] not in graph]
    valid_gt = [item for item in gt_items if item["node"] in graph]

    if trigger not in graph:
        return {
            "event_id": event["id"],
            "event_name": event["name"],
            "ndcg": 0.0,
            "error": f"Trigger node '{trigger}' not in graph",
            "hits": [],
            "misses": [],
            "false_positives": [],
            "missing_nodes": [item["node"] for item in gt_items],
        }

    # Run PPR
    results = engine.evaluate_impact(
        trigger_node=trigger,
        event_direction=direction,
        prob_threshold=0.001,
    )

    # Top 20 results ranked by CIS (already sorted)
    predicted_nodes = [r["node"] for r in results[:20]]
    predicted_set = set(predicted_nodes)
    gt_node_set = {item["node"] for item in valid_gt}

    # Compute NDCG@10
    ndcg = ndcg_at_k(predicted_nodes, valid_gt, k=10)

    # Hits: ground truth nodes found in top 20
    # Build full result lookup for path tracking
    result_map = {r["node"]: r for r in results}

    hits = []
    for item in valid_gt:
        if item["node"] in predicted_set:
            pred_rank = predicted_nodes.index(item["node"]) + 1
            r = result_map[item["node"]]
            hits.append({
                "node": item["node"],
                "predicted_rank": pred_rank,
                "expected_rank": item["rank"],
                "probability": r["probability"],
                "magnitude": r["magnitude"],
                "cis": r["cis"],
                "path": r["path"],
                "delay": r["delay"],
                "via_contains": r.get("via_contains", False),
            })

    # Misses: ground truth nodes NOT in top 20
    misses = []
    for item in valid_gt:
        if item["node"] not in predicted_set:
            r = result_map.get(item["node"])
            actual_rank = None
            if r:
                all_nodes = [x["node"] for x in results]
                actual_rank = all_nodes.index(item["node"]) + 1
            misses.append({
                "node": item["node"],
                "expected_rank": item["rank"],
                "actual_rank": actual_rank,
                "probability": r["probability"] if r else 0.0,
                "magnitude": r["magnitude"] if r else 0.0,
                "cis": r["cis"] if r else 0.0,
                "path": r["path"] if r else [],
                "delay": r["delay"] if r else "",
                "via_contains": r.get("via_contains", False) if r else False,
            })

    # False positives: top-5 PPR nodes not in ground truth
    false_positives = []
    for node in predicted_nodes[:5]:
        if node not in gt_node_set:
            false_positives.append({"node": node, "predicted_rank": predicted_nodes.index(node) + 1})

    return {
        "event_id": event["id"],
        "event_name": event["name"],
        "trigger": trigger,
        "direction": direction,
        "ndcg": ndcg,
        "hits": hits,
        "misses": misses,
        "false_positives": false_positives,
        "missing_nodes": missing_nodes,
        "total_gt": len(gt_items),
        "valid_gt": len(valid_gt),
        "total_results": len(results),
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_full_path(path: list[str], graph=None) -> str:
    """Format a full causal path with hop count and edge types."""
    if not path or len(path) < 2:
        return "(no path)"
    hops = len(path) - 1
    parts = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_type = ""
        if graph and graph.has_edge(u, v):
            edge_type = graph.edges[u, v].get("type", "")
        if edge_type:
            parts.append(f"{u} →[{edge_type}]→ {v}")
        else:
            parts.append(f"{u} → {v}")
    return f"({hops} hops) " + " | ".join(parts)


def print_event_result(result: dict, verbose: bool = False, graph=None) -> None:
    """Print results for a single event with full hop tracing."""
    status = "pass" if result["ndcg"] >= 0.5 else "FAIL"
    print(f"\nEvent: {result['event_name']}")
    print(f"  Trigger: {result['trigger']} (direction: {'+1' if result['direction'] == 1 else '-1'})")

    if result.get("error"):
        print(f"  ERROR: {result['error']}")
        return

    print(f"  NDCG@10: {result['ndcg']:.2f} {'ok' if status == 'pass' else 'FAIL'}")

    # Missing nodes warning
    if result["missing_nodes"]:
        print(f"\n  Missing from graph ({len(result['missing_nodes'])}):")
        for node in result["missing_nodes"]:
            print(f"    {node}")

    # Hits
    hits = result["hits"]
    valid_gt = result["valid_gt"]
    print(f"\n  Hits ({len(hits)}/{valid_gt}):")
    for h in sorted(hits, key=lambda x: x["predicted_rank"]):
        contains = " [C]" if h.get("via_contains") else ""
        hops = len(h["path"]) - 1 if h.get("path") and len(h["path"]) > 1 else 0
        print(f"    #{h['predicted_rank']:<3} {h['node']:<30} exp#{h['expected_rank']}  cis={h['cis']:.5f}  [{hops} hops]{contains}")
        if h.get("path"):
            print(f"         {format_full_path(h['path'], graph)}")

    # Misses
    misses = result["misses"]
    if misses:
        print(f"\n  Misses ({len(misses)}/{valid_gt}):")
        for m in misses:
            if m["actual_rank"]:
                contains = " [C]" if m.get("via_contains") else ""
                hops = len(m["path"]) - 1 if m.get("path") and len(m["path"]) > 1 else 0
                print(f"    #{m['actual_rank']:<3} {m['node']:<30} exp#{m['expected_rank']}  cis={m['cis']:.5f}  [{hops} hops]{contains}")
                if m.get("path"):
                    print(f"         {format_full_path(m['path'], graph)}")
            else:
                print(f"    --- {m['node']:<30} exp#{m['expected_rank']}  not in results")

    # False positives
    fps = result["false_positives"]
    if fps:
        print(f"\n  False positives in top-5:")
        for fp in fps:
            print(f"    {fp['node']:<30} predicted #{fp['predicted_rank']}")


def print_summary(results: list[dict]) -> None:
    """Print aggregate summary across all events."""
    ndcg_scores = [r["ndcg"] for r in results if "error" not in r]
    if not ndcg_scores:
        print("\nSummary: no valid results")
        return

    mean_ndcg = sum(ndcg_scores) / len(ndcg_scores)
    all_above = all(s >= 0.5 for s in ndcg_scores)

    print(f"\nSummary:")
    print(f"  Events: {len(results)}")
    print(f"  Mean NDCG@10: {mean_ndcg:.2f}")
    print(f"  All above 0.5: {'YES' if all_above else 'NO'}")

    # Per-event one-liner
    print(f"\n  {'Event':<30} {'NDCG@10':>8} {'Hits':>6} {'Status':>8}")
    print(f"  {'-'*56}")
    for r in results:
        if r.get("error"):
            print(f"  {r['event_id']:<30} {'ERROR':>8} {'-':>6} {'ERROR':>8}")
        else:
            status = "ok" if r["ndcg"] >= 0.5 else "FAIL"
            hits = f"{len(r['hits'])}/{r['valid_gt']}"
            print(f"  {r['event_id']:<30} {r['ndcg']:>8.2f} {hits:>6} {status:>8}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Historical event replay with NDCG@10 scoring"
    )
    parser.add_argument(
        "events", nargs="*",
        help="Event IDs to run (default: all)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show full PPR rankings",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--ground-truth", type=Path, default=None,
        help="Path to ground_truth.yaml (default: taxonomy/eval_results/ground_truth.yaml)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    # Load graph
    merger = TaxonomyMerger()
    G = merger.merge()
    apply_defaults(G)
    engine = CausalMarkovEngine(G)

    # Load ground truth
    all_events = load_ground_truth(args.ground_truth)
    if not all_events:
        print("Error: no events found in ground truth file")
        sys.exit(1)

    # Filter events if specific IDs given
    if args.events:
        event_ids = set(args.events)
        events = [e for e in all_events if e["id"] in event_ids]
        unknown = event_ids - {e["id"] for e in events}
        if unknown:
            print(f"Unknown event IDs: {', '.join(sorted(unknown))}")
            print(f"Available: {', '.join(e['id'] for e in all_events)}")
            sys.exit(1)
    else:
        events = all_events

    # Run evaluations
    results = []
    for event in events:
        result = evaluate_event(engine, G, event, verbose=args.verbose)
        results.append(result)

    # Output
    if args.json_output:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            print_event_result(result, verbose=args.verbose, graph=G)
        print_summary(results)


if __name__ == "__main__":
    main()
