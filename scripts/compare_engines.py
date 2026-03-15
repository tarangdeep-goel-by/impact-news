"""Compare Dijkstra vs PPR engine outputs on all scenarios.

Usage:
    docker exec impact-news-ppr python -m scripts.compare_engines
"""

import yaml
from pathlib import Path
from graph.merge import TaxonomyMerger
from graph.migrate_weights import apply_defaults, apply_fan_out_penalty
from graph.traverse import analyze_impact as dijkstra_impact
from graph.markov_engine import CausalMarkovEngine


def main():
    # Load graph
    merger = TaxonomyMerger()
    G = merger.merge()
    apply_defaults(G)
    apply_fan_out_penalty(G)

    # Build PPR engine
    engine = CausalMarkovEngine(G)

    # Load scenarios
    scenarios_path = Path("taxonomy/scenarios.yaml")
    scenarios = yaml.safe_load(scenarios_path.read_text()).get("scenarios", [])

    print(f"Loaded {len(scenarios)} scenarios\n")

    # For Type B and C scenarios, run both engines and compare
    print(f"{'ID':<40} {'Type':<5} {'Dijkstra':>10} {'PPR Prob':>10} {'PPR Mag':>10} {'Match':>6}")
    print("-" * 95)

    for sc in scenarios:
        stype = sc.get("type", "")

        if stype == "B":
            trigger = sc["trigger_node"]
            targets = sc.get("target_nodes", [])
            threshold = sc.get("threshold", 0.05)
            direction = sc.get("direction", 1)

            # Dijkstra
            dijk_results = dijkstra_impact(G, trigger, event_direction=direction, threshold=threshold)
            dijk_nodes = {r["node"]: r["score"] for r in dijk_results}

            # PPR
            ppr_results = engine.evaluate_impact(trigger, event_direction=direction, prob_threshold=0.0001)
            ppr_nodes = {r["node"]: r for r in ppr_results}

            for target in targets:
                d_score = dijk_nodes.get(target, 0.0)
                p_prob = ppr_nodes[target]["probability"] if target in ppr_nodes else 0.0
                p_mag = ppr_nodes[target]["magnitude"] if target in ppr_nodes else 0.0
                match = "Y" if (d_score > 0) == (p_prob > 0) else "N"
                print(f"{sc['id']:<40} {'B':<5} {d_score:>10.4f} {p_prob:>10.6f} {p_mag:>10.6f} {match:>6}")

        elif stype == "C":
            trigger = sc["trigger_node"]
            target = sc["target_node"]
            min_score = sc.get("min_score", 0.1)
            direction = sc.get("direction", 1)

            # Dijkstra
            dijk_results = dijkstra_impact(G, trigger, event_direction=direction)
            dijk_hit = next((r for r in dijk_results if r["node"] == target), None)
            d_score = dijk_hit["score"] if dijk_hit else 0.0

            # PPR
            ppr_results = engine.evaluate_impact(trigger, event_direction=direction, prob_threshold=0.0001)
            ppr_hit = next((r for r in ppr_results if r["node"] == target), None)
            p_prob = ppr_hit["probability"] if ppr_hit else 0.0
            p_mag = ppr_hit["magnitude"] if ppr_hit else 0.0
            match = "Y" if (d_score >= min_score) == (p_prob > 0) else "N"
            print(f"{sc['id']:<40} {'C':<5} {d_score:>10.4f} {p_prob:>10.6f} {p_mag:>10.6f} {match:>6}")

    # Summary stats
    print("\n--- SUMMARY ---")

    # Run 5 reference triggers and compare reach counts
    ref_triggers = ["crude_oil", "rbi_repo_rate", "southwest_monsoon", "nifty_50", "usd_inr_exchange"]
    print(f"\n{'Trigger':<25} {'Dijk Reach':>12} {'PPR Reach':>12} {'PPR (>0.001)':>14}")
    print("-" * 65)

    for trigger in ref_triggers:
        if not G.has_node(trigger):
            # Try common alternatives
            continue
        dijk_results = dijkstra_impact(G, trigger, threshold=0.05)
        ppr_results = engine.evaluate_impact(trigger, prob_threshold=0.0001)
        ppr_above_001 = sum(1 for r in ppr_results if r["probability"] > 0.001)
        print(f"{trigger:<25} {len(dijk_results):>12} {len(ppr_results):>12} {ppr_above_001:>14}")


if __name__ == "__main__":
    main()
