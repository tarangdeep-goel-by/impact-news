"""Golden test runner — A/B comparison of impact engines.

Runs golden test cases against graph-direct, graph (full pipeline), and/or LLM engines.
Compares must_hit/must_miss assertions and shows top impacts side by side.

Usage:
    python -m tests.golden.runner                         # Both engines (LLM + graph-direct)
    python -m tests.golden.runner --engine llm             # LLM only
    python -m tests.golden.runner --engine graph-direct    # Graph direct only (fast, no Gemini)
    python -m tests.golden.runner --engine graph           # Full graph pipeline (Gemini tag extraction)
    python -m tests.golden.runner --case crude_oil_car_commuter  # Single case
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Protocol

import yaml

from engine.base import ImpactResult
from engine.taxonomy_context import TaxonomyContext
from graph.markov_engine import CausalMarkovEngine
from graph.merge import TaxonomyMerger
from graph.migrate_weights import apply_defaults
from config import settings

logger = logging.getLogger(__name__)

CASES_PATH = Path(__file__).parent / "cases.yaml"

# ---------------------------------------------------------------------------
# Engine wrappers
# ---------------------------------------------------------------------------


class EngineProtocol(Protocol):
    """Minimal protocol: evaluate a trigger node, return ImpactResults."""

    def evaluate_trigger(self, trigger_node: str) -> list[ImpactResult]: ...


class DirectGraphEngine:
    """Run CSP directly from trigger_node — no article processing."""

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

    def evaluate_trigger(self, trigger_node: str) -> list[ImpactResult]:
        results = self.engine.evaluate_impact(trigger_node)
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


class FullGraphEngine:
    """Run full graph pipeline: article -> Gemini tag extraction -> FAISS -> CSP."""

    def __init__(self, taxonomy: TaxonomyContext) -> None:
        from engine.graph_adapter import GraphImpactEngine

        self._engine = GraphImpactEngine()
        self.taxonomy = taxonomy

    def evaluate_trigger(self, trigger_node: str) -> list[ImpactResult]:
        title, summary = trigger_to_article(trigger_node, self.taxonomy)
        return self._engine.evaluate_article(title, summary)


class LLMEngine:
    """Run LLM engine: article -> Gemini with full taxonomy -> ImpactResults."""

    def __init__(self, taxonomy: TaxonomyContext) -> None:
        from engine.llm_engine import LLMImpactEngine

        self._engine = LLMImpactEngine(taxonomy=taxonomy)
        self.taxonomy = taxonomy

    def evaluate_trigger(self, trigger_node: str) -> list[ImpactResult]:
        title, summary = trigger_to_article(trigger_node, self.taxonomy)
        return self._engine.evaluate_article(title, summary)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def trigger_to_article(trigger_node: str, taxonomy: TaxonomyContext) -> tuple[str, str]:
    """Convert a trigger_node ID to a synthetic article title and summary."""
    label = taxonomy.get_node_label(trigger_node)
    title = f"{label} - significant change reported"
    summary = (
        f"A significant change in {label} ({trigger_node}) has been reported, "
        f"with potential widespread impacts across the Indian economy and citizens."
    )
    return title, summary


def load_cases(path: Path = CASES_PATH) -> dict:
    """Load golden test cases from YAML."""
    with open(path) as f:
        return yaml.safe_load(f)


def check_must_hit(
    results: list[ImpactResult],
    must_hit: list[str],
    taxonomy: TaxonomyContext,
) -> tuple[int, int, list[str]]:
    """Check must_hit nodes against results with ancestor matching.

    Returns (hits, total, list_of_missed_nodes).
    """
    if not must_hit:
        return 0, 0, []

    result_nodes = {r["node"] for r in results}
    hits = 0
    missed: list[str] = []

    for target in must_hit:
        # Direct match
        if target in result_nodes:
            hits += 1
            continue
        # Ancestor match: if any result node is an ancestor of target,
        # or target is an ancestor of any result node, count as hit
        found = False
        for rn in result_nodes:
            if taxonomy.is_ancestor_of(rn, target) or taxonomy.is_ancestor_of(target, rn):
                found = True
                break
        if found:
            hits += 1
        else:
            missed.append(target)

    return hits, len(must_hit), missed


def check_must_miss(
    results: list[ImpactResult],
    must_miss: list[str],
    taxonomy: TaxonomyContext,
) -> tuple[int, int, list[str]]:
    """Check must_miss nodes against results with ancestor matching.

    If the case says must_miss: [retail_petrol] and the engine returns an
    ancestor of retail_petrol, that counts as a violation.

    Returns (clean_count, total, list_of_violations).
    """
    if not must_miss:
        return 0, 0, []

    result_nodes = {r["node"] for r in results}
    clean = 0
    violations: list[str] = []

    for forbidden in must_miss:
        # Direct match = violation
        if forbidden in result_nodes:
            violations.append(forbidden)
            continue
        # Ancestor match: result node is ancestor of forbidden = violation
        found = False
        for rn in result_nodes:
            if taxonomy.is_ancestor_of(rn, forbidden):
                found = True
                break
        if found:
            violations.append(forbidden)
        else:
            clean += 1

    return clean, len(must_miss), violations


def format_top_impacts(results: list[ImpactResult], n: int = 5) -> str:
    """Format top-N impacts as a compact string."""
    top = results[:n]
    parts = []
    for r in top:
        score = r["probability"] * r["magnitude"]
        parts.append(f"{r['node']}({score:.2f})")
    return ", ".join(parts) if parts else "(none)"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_case(
    case: dict,
    engine: EngineProtocol,
    engine_name: str,
    taxonomy: TaxonomyContext,
) -> dict:
    """Run a single golden test case against an engine.

    Returns a result dict with pass/fail info and diagnostics.
    """
    trigger = case["trigger_node"]
    must_hit = case.get("must_hit", [])
    must_miss = case.get("must_miss", [])

    t0 = time.time()
    try:
        results = engine.evaluate_trigger(trigger)
    except Exception as e:
        logger.error("Engine %s failed on %s: %s", engine_name, case["id"], e)
        results = []
    elapsed = time.time() - t0

    hit_count, hit_total, hit_missed = check_must_hit(results, must_hit, taxonomy)
    miss_count, miss_total, miss_violations = check_must_miss(results, must_miss, taxonomy)

    hit_pass = hit_count == hit_total
    miss_pass = miss_count == miss_total

    return {
        "case_id": case["id"],
        "engine": engine_name,
        "results": results,
        "hit_count": hit_count,
        "hit_total": hit_total,
        "hit_pass": hit_pass,
        "hit_missed": hit_missed,
        "miss_count": miss_count,
        "miss_total": miss_total,
        "miss_pass": miss_pass,
        "miss_violations": miss_violations,
        "impact_count": len(results),
        "elapsed": elapsed,
    }


def print_results(all_results: list[dict]) -> None:
    """Print per-case table and summary."""
    # Header
    print()
    print(
        f"{'Case':<35} | {'Engine':<14} | {'must_hit':<10} | {'must_miss':<10} "
        f"| {'#Impacts':>8} | {'Time':>6} | Top impacts"
    )
    print("-" * 130)

    for r in all_results:
        case_id = r["case_id"]
        engine = r["engine"]

        # must_hit display
        if r["hit_total"] == 0:
            hit_str = "-"
        else:
            mark = "PASS" if r["hit_pass"] else "FAIL"
            hit_str = f"{r['hit_count']}/{r['hit_total']} {mark}"

        # must_miss display
        if r["miss_total"] == 0:
            miss_str = "-"
        else:
            mark = "PASS" if r["miss_pass"] else "FAIL"
            miss_str = f"{r['miss_count']}/{r['miss_total']} {mark}"

        top = format_top_impacts(r["results"], n=5)
        elapsed = f"{r['elapsed']:.1f}s"

        print(
            f"{case_id:<35} | {engine:<14} | {hit_str:<10} | {miss_str:<10} "
            f"| {r['impact_count']:>8} | {elapsed:>6} | {top}"
        )

        # Print missed/violated nodes if any
        if r["hit_missed"]:
            print(f"{'':>35}   {'':>14}   MISSED: {', '.join(r['hit_missed'])}")
        if r["miss_violations"]:
            print(f"{'':>35}   {'':>14}   VIOLATED: {', '.join(r['miss_violations'])}")

    # Summary per engine
    engines = sorted(set(r["engine"] for r in all_results))
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(
        f"{'Engine':<14} | {'Cases':>5} | {'must_hit recall':>15} | "
        f"{'must_miss prec':>14} | {'Avg impacts':>11} | {'Avg time':>8}"
    )
    print("-" * 80)

    for eng in engines:
        eng_results = [r for r in all_results if r["engine"] == eng]
        n_cases = len(eng_results)

        # must_hit recall: total hits / total expected (across cases with must_hit)
        total_hits = sum(r["hit_count"] for r in eng_results)
        total_expected = sum(r["hit_total"] for r in eng_results)
        hit_recall = (total_hits / total_expected * 100) if total_expected > 0 else 100.0

        # must_miss precision: total clean / total forbidden (across cases with must_miss)
        total_clean = sum(r["miss_count"] for r in eng_results)
        total_forbidden = sum(r["miss_total"] for r in eng_results)
        miss_prec = (total_clean / total_forbidden * 100) if total_forbidden > 0 else 100.0

        avg_impacts = sum(r["impact_count"] for r in eng_results) / max(n_cases, 1)
        avg_time = sum(r["elapsed"] for r in eng_results) / max(n_cases, 1)

        print(
            f"{eng:<14} | {n_cases:>5} | {hit_recall:>14.1f}% | "
            f"{miss_prec:>13.1f}% | {avg_impacts:>11.1f} | {avg_time:>7.1f}s"
        )

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Golden test runner — A/B comparison of impact engines",
    )
    parser.add_argument(
        "--engine",
        choices=["llm", "graph-direct", "graph", "all"],
        nargs="+",
        default=["graph-direct", "llm"],
        help="Engine(s) to run. Default: graph-direct + llm",
    )
    parser.add_argument(
        "--case",
        type=str,
        default=None,
        help="Run only this case ID (substring match)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of top impacts to show per case",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    # Resolve engine list
    engine_names: list[str] = []
    for e in args.engine:
        if e == "all":
            engine_names = ["graph-direct", "graph", "llm"]
            break
        engine_names.append(e)
    # Deduplicate while preserving order
    seen: set[str] = set()
    engine_names = [e for e in engine_names if not (e in seen or seen.add(e))]

    # Load taxonomy (shared across engines)
    print("Loading taxonomy...", end=" ", flush=True)
    taxonomy = TaxonomyContext.from_merged_graph(settings.graph_path)
    print("done.")

    # Load cases
    data = load_cases()
    cases = data.get("cases", [])
    if args.case:
        cases = [c for c in cases if args.case in c["id"]]
        if not cases:
            print(f"No cases matching '{args.case}'")
            sys.exit(1)

    print(f"Running {len(cases)} cases x {len(engine_names)} engines\n")

    # Initialize engines
    engines: dict[str, EngineProtocol] = {}
    for name in engine_names:
        print(f"Initializing {name} engine...", end=" ", flush=True)
        if name == "graph-direct":
            engines[name] = DirectGraphEngine(taxonomy)
        elif name == "graph":
            engines[name] = FullGraphEngine(taxonomy)
        elif name == "llm":
            engines[name] = LLMEngine(taxonomy)
        print("done.")

    # Run all cases
    all_results: list[dict] = []
    for case in cases:
        for name in engine_names:
            result = run_case(case, engines[name], name, taxonomy)
            all_results.append(result)

    # Print results
    print_results(all_results)


if __name__ == "__main__":
    main()
