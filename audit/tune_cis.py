"""Grid search over CIS parameters to maximize NDCG@10.

Usage:
    python -m audit.tune_cis              # Run full grid search
    python -m audit.tune_cis --top 10     # Show top 10 combos
"""

from __future__ import annotations

import argparse
import itertools
import logging
from pathlib import Path

import yaml

from graph.merge import TaxonomyMerger
from graph.migrate_weights import apply_defaults
from graph.markov_engine import CausalMarkovEngine
from audit.event_replay import load_ground_truth, evaluate_event

logger = logging.getLogger(__name__)


GRID = {
    'i_world_boost': [1.5, 2.0, 3.0],
    'category_penalty': [0.2, 0.3, 0.5],
    'leaf_boost_l4': [1.0, 1.5, 2.0],
    'leaf_boost_l3': [0.8, 1.0, 1.2],
}


def run_grid_search(top_n: int = 20) -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    # Load graph once
    merger = TaxonomyMerger()
    G = merger.merge()
    apply_defaults(G)

    # Load ground truth events
    events = load_ground_truth()
    if not events:
        print("Error: no events in ground truth")
        return

    # Generate all param combinations
    keys = list(GRID.keys())
    values = list(GRID.values())
    combos = list(itertools.product(*values))
    print(f"Testing {len(combos)} parameter combinations against {len(events)} events...\n")

    results = []
    for i, combo in enumerate(combos):
        params = dict(zip(keys, combo))

        # Build engine with these CIS params
        engine = CausalMarkovEngine(
            G,
            i_world_boost=params['i_world_boost'],
            category_penalty=params['category_penalty'],
            leaf_boost_l4=params['leaf_boost_l4'],
            leaf_boost_l3=params['leaf_boost_l3'],
        )

        # Run all events, compute mean NDCG@10
        ndcg_scores = []
        for event in events:
            result = evaluate_event(engine, G, event)
            if "error" not in result:
                ndcg_scores.append(result["ndcg"])

        mean_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
        results.append({**params, 'mean_ndcg': mean_ndcg})

        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(combos)} done...")

    # Sort by NDCG descending
    results.sort(key=lambda x: x['mean_ndcg'], reverse=True)

    # Print results
    print(f"\n{'Rank':>4} {'i_world':>8} {'cat_pen':>8} {'l4_boost':>8} {'l3_boost':>8} {'NDCG@10':>8}")
    print("-" * 52)
    for i, r in enumerate(results[:top_n]):
        print(f"{i+1:>4} {r['i_world_boost']:>8.1f} {r['category_penalty']:>8.1f} "
              f"{r['leaf_boost_l4']:>8.1f} {r['leaf_boost_l3']:>8.1f} {r['mean_ndcg']:>8.4f}")

    # Best result
    best = results[0]
    print(f"\nBest: i_world_boost={best['i_world_boost']}, category_penalty={best['category_penalty']}, "
          f"leaf_boost_l4={best['leaf_boost_l4']}, leaf_boost_l3={best['leaf_boost_l3']}")
    print(f"Mean NDCG@10: {best['mean_ndcg']:.4f}")


def main():
    parser = argparse.ArgumentParser(description="Grid search over CIS parameters")
    parser.add_argument("--top", type=int, default=20, help="Show top N combos")
    args = parser.parse_args()
    run_grid_search(top_n=args.top)


if __name__ == "__main__":
    main()
