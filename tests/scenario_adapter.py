"""Scenario adapter — run graph scenarios against the LLM engine."""

import argparse
import yaml
import logging
from pathlib import Path

from engine.taxonomy_context import TaxonomyContext
from engine.llm_engine import LLMImpactEngine
from engine.base import ImpactResult
from pipeline.gemini import GeminiClient

logger = logging.getLogger(__name__)

SCENARIO_PATH = Path("taxonomy/scenarios.yaml")


def trigger_to_article(trigger_node: str, taxonomy: TaxonomyContext) -> tuple[str, str]:
    """Convert a trigger node ID to a synthetic article title and summary."""
    label = taxonomy.get_node_label(trigger_node)
    title = f"{label} - significant change reported"
    summary = (
        f"A significant change in {label} ({trigger_node}) has been reported, "
        f"with potential widespread impacts across the Indian economy and citizens."
    )
    return title, summary


def node_in_results(
    target: str, results: list[ImpactResult], taxonomy: TaxonomyContext
) -> ImpactResult | None:
    """Check if target node appears in results (direct or via ancestor/descendant)."""
    for r in results:
        if r["node"] == target:
            return r
        # LLM might return a parent of the target
        if taxonomy.is_ancestor_of(r["node"], target):
            return r
        # LLM might return a child of the target
        if taxonomy.is_ancestor_of(target, r["node"]):
            return r
    return None


def run_scenario(
    scenario: dict,
    engine: LLMImpactEngine,
    taxonomy: TaxonomyContext,
) -> dict:
    """Run one scenario against the LLM engine. Returns result dict."""
    sid = scenario["id"]
    stype = scenario.get("type", "A")
    trigger = scenario["trigger_node"]
    target = scenario.get("target_node", "")
    expected = scenario.get("expected", "REACHABLE")

    title, summary = trigger_to_article(trigger, taxonomy)

    # Call LLM engine
    try:
        impacts = engine.evaluate_article(title, summary)
    except Exception as e:
        logger.error("Engine failed on %s: %s", sid, e)
        return {"id": sid, "type": stype, "status": "ERROR", "detail": str(e)}

    hit = node_in_results(target, impacts, taxonomy) if target else None

    if stype == "E":
        # Isolation: target should NOT be reached
        if hit is None:
            return {"id": sid, "type": stype, "status": "PASS", "detail": "Correctly isolated"}
        else:
            return {
                "id": sid, "type": stype, "status": "FAIL",
                "detail": f"False positive: {target} found with prob={hit['probability']:.2f}",
            }
    elif stype == "D":
        # Polarity check
        if hit is None:
            return {"id": sid, "type": stype, "status": "FAIL", "detail": f"{target} not reached"}
        expected_pol = scenario.get("expected_polarity", 1)
        if hit["polarity"] == expected_pol:
            return {"id": sid, "type": stype, "status": "PASS", "detail": f"Polarity correct ({hit['polarity']})"}
        else:
            return {
                "id": sid, "type": stype, "status": "FAIL",
                "detail": f"Wrong polarity: expected {expected_pol}, got {hit['polarity']}",
            }
    else:
        # Type A/B/C: target should be reachable
        if expected == "REACHABLE":
            if hit is not None:
                return {"id": sid, "type": stype, "status": "PASS", "detail": f"Reached via {hit['node']}"}
            else:
                return {"id": sid, "type": stype, "status": "FAIL", "detail": f"{target} not reached"}
        else:
            # Expected NOT_REACHABLE
            if hit is None:
                return {"id": sid, "type": stype, "status": "PASS", "detail": "Correctly unreachable"}
            else:
                return {"id": sid, "type": stype, "status": "FAIL", "detail": f"Unexpectedly reached {target}"}


def main():
    parser = argparse.ArgumentParser(description="Run graph scenarios against LLM engine")
    parser.add_argument("--compare", action="store_true", help="Side-by-side with graph engine (not implemented yet)")
    parser.add_argument("--type", choices=["A", "B", "C", "D", "E", "all"], default="all", help="Filter by scenario type")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)

    # Load scenarios
    with open(SCENARIO_PATH) as f:
        data = yaml.safe_load(f)
    scenarios = data.get("scenarios", [])

    if args.type != "all":
        scenarios = [s for s in scenarios if s.get("type") == args.type]

    print("Loading taxonomy...")
    taxonomy = TaxonomyContext.from_merged_graph()

    print("Initializing LLM engine...")
    gemini = GeminiClient()
    engine = LLMImpactEngine(taxonomy, gemini)

    print(f"\nRunning {len(scenarios)} scenarios...\n")
    print(f"{'ID':<45} {'Type':>4} {'Status':>6}  Detail")
    print("-" * 100)

    results = []
    pass_count = 0
    fail_count = 0
    error_count = 0

    for s in scenarios:
        result = run_scenario(s, engine, taxonomy)
        results.append(result)

        status = result["status"]
        if status == "PASS":
            pass_count += 1
            marker = "+"
        elif status == "FAIL":
            fail_count += 1
            marker = "X"
        else:
            error_count += 1
            marker = "!"

        print(f"{result['id']:<45} {result['type']:>4} {marker:>6}  {result['detail']}")

    print(f"\n{'='*60}")
    print(f"PASS: {pass_count}  FAIL: {fail_count}  ERROR: {error_count}  TOTAL: {len(results)}")
    print(f"Pass rate: {pass_count / len(results) * 100:.1f}%" if results else "No scenarios")

    # Breakdown by type
    from collections import Counter
    type_pass = Counter()
    type_total = Counter()
    for r in results:
        type_total[r["type"]] += 1
        if r["status"] == "PASS":
            type_pass[r["type"]] += 1

    print("\nBy type:")
    for t in sorted(type_total.keys()):
        print(f"  {t}: {type_pass[t]}/{type_total[t]} ({type_pass[t]/type_total[t]*100:.0f}%)")


if __name__ == "__main__":
    main()
