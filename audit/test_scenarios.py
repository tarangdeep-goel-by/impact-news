"""Validation tests for the impact traversal engine.

DEPRECATED: This file is superseded by graph/scenarios.py + taxonomy/scenarios.yaml.
Use `python3 scripts/graph_builder.py test` for scenario-based testing.
Kept for reference only.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph.merge import TaxonomyMerger
from graph.migrate_weights import apply_defaults, apply_fan_out_penalty
from graph.traverse import analyze_impact, get_causal_entry


def load_graph():
    root = Path(__file__).resolve().parent.parent
    merger = TaxonomyMerger(root=root)
    G = merger.merge()
    apply_defaults(G)
    apply_fan_out_penalty(G)
    return G


# ── helpers ──────────────────────────────────────────────────────────────

passed = 0
failed = 0
errors = 0
results_log: list[str] = []


def check(label: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        results_log.append(f"  PASS  {label}")
    else:
        failed += 1
        msg = f"  FAIL  {label}"
        if detail:
            msg += f"  -- {detail}"
        results_log.append(msg)


def find_node(impacts: list[dict], node_id: str) -> dict | None:
    for imp in impacts:
        if imp["node"] == node_id:
            return imp
    return None


# ── tests ────────────────────────────────────────────────────────────────

def test_crude_oil_shock(G):
    print("\n--- Test 1: Crude Oil Shock ---")
    impacts = analyze_impact(G, "crude_oil", event_direction=1)
    nodes_hit = {r["node"] for r in impacts}

    petrol = find_node(impacts, "petrol")
    diesel = find_node(impacts, "diesel")

    check("petrol appears", petrol is not None, f"nodes hit: {len(nodes_hit)}")
    if petrol:
        check("petrol score > 0.3", petrol["score"] > 0.3, f"score={petrol['score']:.3f}")
    else:
        check("petrol score > 0.3", False, "petrol not found")

    check("diesel appears", diesel is not None, f"nodes hit: {len(nodes_hit)}")
    if diesel:
        check("diesel score > 0.3", diesel["score"] > 0.3, f"score={diesel['score']:.3f}")
    else:
        check("diesel score > 0.3", False, "diesel not found")

    check(">=20 nodes impacted", len(impacts) >= 20, f"got {len(impacts)}")


def test_monsoon_impact(G):
    print("\n--- Test 2: Monsoon Impact ---")
    impacts = analyze_impact(G, "monsoon", event_direction=-1)
    nodes_hit = {r["node"] for r in impacts}

    # crop_yield doesn't exist as a node; graph uses rabi_crops / kharif_crops / crop_production
    crop_candidates = ["crop_production", "kharif_crops", "rabi_crops"]
    crop = None
    for c in crop_candidates:
        crop = find_node(impacts, c)
        if crop:
            break
    food_inf = find_node(impacts, "food_inflation_india")

    check("crop node appears (crop_production/kharif/rabi)", crop is not None,
          f"nodes hit: {sorted(nodes_hit)[:10]}")
    check("food_inflation_india appears", food_inf is not None, f"nodes hit: {sorted(nodes_hit)[:10]}")
    check(">=5 nodes impacted", len(impacts) >= 5, f"got {len(impacts)}")


def test_repo_rate_hike(G):
    print("\n--- Test 3: Repo Rate Hike ---")
    # Determine which node exists
    trigger = None
    for candidate in ("rbi_repo_rate", "repo_rate"):
        if G.has_node(candidate):
            trigger = candidate
            break
    if trigger is None:
        check("repo rate node exists", False, "neither rbi_repo_rate nor repo_rate in graph")
        return

    print(f"  Using trigger: {trigger}")
    impacts = analyze_impact(G, trigger, event_direction=1)
    nodes_hit = {r["node"] for r in impacts}

    emi = find_node(impacts, "home_loan_emi")
    check("home_loan_emi appears", emi is not None, f"nodes hit: {sorted(nodes_hit)[:10]}")
    check(">=10 nodes impacted", len(impacts) >= 10, f"got {len(impacts)}")


def test_elevator(G):
    print("\n--- Test 4: Elevator Test ---")
    entry = get_causal_entry(G, "basmati_rice")
    check("elevator basmati_rice -> rice", entry == "rice", f"got entry={entry}")

    impacts = analyze_impact(G, "basmati_rice", event_direction=1)
    check("basmati_rice produces impacts via elevator", len(impacts) > 0, f"got {len(impacts)}")


def test_cycle_death(G):
    print("\n--- Test 5: Cycle Death Test ---")
    t0 = time.time()
    impacts = analyze_impact(G, "cpi_inflation", threshold=0.01, max_depth=10)
    elapsed = time.time() - t0

    check("completes without hang", True, f"elapsed={elapsed:.2f}s")
    check("finite results", len(impacts) < 500, f"got {len(impacts)}")
    print(f"  (returned {len(impacts)} nodes in {elapsed:.2f}s)")


def test_macro_vs_niche(G):
    print("\n--- Test 6: Macro vs Niche Scale ---")
    macro_triggers = [
        "crude_oil", "monsoon", "nifty_50", "usd_inr", "gdp_growth",
        "cpi_inflation", "repo_rate", "agriculture_sector", "it_services_sector",
        "real_estate_prices",
    ]
    # Resolve repo_rate to actual node
    for i, t in enumerate(macro_triggers):
        if t == "repo_rate" and not G.has_node(t):
            if G.has_node("rbi_repo_rate"):
                macro_triggers[i] = "rbi_repo_rate"

    niche_triggers = [
        "basmati_rice", "zoho", "hdfc_bank", "tata_motors", "coal_india",
        "infosys", "reliance_jio", "air_india", "ola", "zomato",
    ]

    macro_counts = []
    for t in macro_triggers:
        if not G.has_node(t):
            print(f"  SKIP macro trigger {t} (not in graph)")
            continue
        impacts = analyze_impact(G, t, event_direction=1)
        macro_counts.append(len(impacts))
        print(f"  macro {t}: {len(impacts)} impacts")

    niche_counts = []
    for t in niche_triggers:
        if not G.has_node(t):
            # Can't even call get_causal_entry if node missing
            print(f"  SKIP niche trigger {t} (not in graph)")
            continue
        entry = get_causal_entry(G, t)
        impacts = analyze_impact(G, t, event_direction=1)
        niche_counts.append(len(impacts))
        print(f"  niche {t} (entry={entry}): {len(impacts)} impacts")

    macro_avg = sum(macro_counts) / len(macro_counts) if macro_counts else 0
    niche_avg = sum(niche_counts) / len(niche_counts) if niche_counts else 0

    print(f"  Macro avg: {macro_avg:.1f}  |  Niche avg: {niche_avg:.1f}")

    check("macro avg > 15", macro_avg > 15, f"macro_avg={macro_avg:.1f}")
    check("niche avg < macro avg", niche_avg < macro_avg,
          f"niche={niche_avg:.1f} macro={macro_avg:.1f}")


# ── main ─────────────────────────────────────────────────────────────────

def main():
    print("Loading graph...")
    G = load_graph()
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    tests = [
        ("Crude Oil Shock", test_crude_oil_shock),
        ("Monsoon Impact", test_monsoon_impact),
        ("Repo Rate Hike", test_repo_rate_hike),
        ("Elevator", test_elevator),
        ("Cycle Death", test_cycle_death),
        ("Macro vs Niche", test_macro_vs_niche),
    ]

    for name, fn in tests:
        try:
            fn(G)
        except Exception as e:
            global errors
            errors += 1
            results_log.append(f"  ERROR {name}: {e}")
            print(f"  ERROR: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for line in results_log:
        print(line)
    print("-" * 60)
    print(f"PASSED: {passed}  FAILED: {failed}  ERRORS: {errors}")
    total = passed + failed + errors
    if failed == 0 and errors == 0:
        print("ALL CHECKS PASSED")
    else:
        print(f"{failed + errors}/{total} checks need attention")
    print("=" * 60)

    sys.exit(1 if (failed or errors) else 0)


if __name__ == "__main__":
    main()
