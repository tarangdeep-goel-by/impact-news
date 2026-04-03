"""Golden test runner — evaluate LLM engine on golden test cases.

Usage:
    python -m tests.golden.runner                          # Run all cases
    python -m tests.golden.runner --case crude_oil_car     # Single case
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import yaml

from engine.base import ImpactResult
from engine.llm_engine import LLMImpactEngine
from engine.taxonomy_context import TaxonomyContext
from config import settings

logger = logging.getLogger(__name__)

CASES_PATH = Path(__file__).parent / "cases.yaml"


def trigger_to_article(trigger_node: str, taxonomy: TaxonomyContext) -> tuple[str, str]:
    label = taxonomy.get_node_label(trigger_node)
    title = f"{label} - significant change reported"
    summary = (
        f"A significant change in {label} ({trigger_node}) has been reported, "
        f"with potential widespread impacts across the Indian economy and citizens."
    )
    return title, summary


def check_must_hit(
    results: list[ImpactResult], must_hit: list[str], taxonomy: TaxonomyContext,
) -> tuple[int, int, list[str]]:
    if not must_hit:
        return 0, 0, []
    result_nodes = {r["node"] for r in results}
    hits, missed = 0, []
    for target in must_hit:
        if target in result_nodes:
            hits += 1
            continue
        found = any(
            taxonomy.is_ancestor_of(rn, target) or taxonomy.is_ancestor_of(target, rn)
            for rn in result_nodes
        )
        if found:
            hits += 1
        else:
            missed.append(target)
    return hits, len(must_hit), missed


def check_must_miss(
    results: list[ImpactResult], must_miss: list[str], taxonomy: TaxonomyContext,
) -> tuple[int, int, list[str]]:
    if not must_miss:
        return 0, 0, []
    result_nodes = {r["node"] for r in results}
    clean, violations = 0, []
    for forbidden in must_miss:
        if forbidden in result_nodes:
            violations.append(forbidden)
            continue
        if any(taxonomy.is_ancestor_of(rn, forbidden) for rn in result_nodes):
            violations.append(forbidden)
        else:
            clean += 1
    return clean, len(must_miss), violations


def main() -> None:
    parser = argparse.ArgumentParser(description="Golden test runner")
    parser.add_argument("--case", type=str, default=None, help="Filter by case ID (substring)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    print("Loading taxonomy...", end=" ", flush=True)
    taxonomy = TaxonomyContext.from_merged_graph(settings.graph_path)
    print("done.")

    with open(CASES_PATH) as f:
        data = yaml.safe_load(f)
    cases = data.get("cases", [])
    if args.case:
        cases = [c for c in cases if args.case in c["id"]]

    print(f"Initializing LLM engine...", end=" ", flush=True)
    engine = LLMImpactEngine(taxonomy=taxonomy)
    print("done.")

    print(f"\nRunning {len(cases)} cases\n")
    print(f"{'Case':<35} | {'must_hit':<10} | {'must_miss':<10} | {'#Imp':>5} | {'Time':>6} | Top impacts")
    print("-" * 110)

    total_hits, total_expected, total_clean, total_forbidden = 0, 0, 0, 0

    for case in cases:
        trigger = case["trigger_node"]
        title, summary = trigger_to_article(trigger, taxonomy)

        t0 = time.time()
        results, _meta = engine.evaluate_article(title, summary)
        elapsed = time.time() - t0

        h_count, h_total, h_missed = check_must_hit(results, case.get("must_hit", []), taxonomy)
        m_count, m_total, m_violations = check_must_miss(results, case.get("must_miss", []), taxonomy)

        total_hits += h_count
        total_expected += h_total
        total_clean += m_count
        total_forbidden += m_total

        hit_str = f"{h_count}/{h_total} {'PASS' if h_count == h_total else 'FAIL'}" if h_total else "-"
        miss_str = f"{m_count}/{m_total} {'PASS' if m_count == m_total else 'FAIL'}" if m_total else "-"
        top = ", ".join(f"{r['node']}({r['probability']*r['magnitude']:.2f})" for r in results[:4])

        print(f"{case['id']:<35} | {hit_str:<10} | {miss_str:<10} | {len(results):>5} | {elapsed:>5.1f}s | {top or '(none)'}")
        if h_missed:
            print(f"{'':>35}   MISSED: {', '.join(h_missed)}")
        if m_violations:
            print(f"{'':>35}   VIOLATED: {', '.join(m_violations)}")

    recall = total_hits / total_expected * 100 if total_expected else 100
    prec = total_clean / total_forbidden * 100 if total_forbidden else 100
    print(f"\n{'='*60}")
    print(f"must_hit recall: {recall:.1f}%  |  must_miss precision: {prec:.1f}%")


if __name__ == "__main__":
    main()
