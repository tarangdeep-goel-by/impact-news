"""Canary smoke test runner for critical causal chains.

Validates that key trigger→impact paths survive graph edits by firing
each trigger through PPR and asserting specific nodes appear in top-N.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from graph.markov_engine import CausalMarkovEngine

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CANARIES = ROOT / "taxonomy" / "canary_queries.yaml"


# ---------------------------------------------------------------------------
# Load & validate
# ---------------------------------------------------------------------------


def load_canaries(path: Path | None = None) -> list[dict]:
    p = path or DEFAULT_CANARIES
    data = yaml.safe_load(p.read_text())
    return data.get("canaries", []) or []


def validate_canary_refs(
    canaries: list[dict], known_nodes: set[str]
) -> list[str]:
    errors: list[str] = []
    for c in canaries:
        cid = c.get("id", "?")
        trigger = c.get("trigger")
        if trigger and trigger not in known_nodes:
            errors.append(f"[{cid}] trigger '{trigger}' not in graph")
        for nid in c.get("must_include", []) or []:
            if nid not in known_nodes:
                errors.append(f"[{cid}] must_include '{nid}' not in graph")
    return errors


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_canary(engine: CausalMarkovEngine, canary: dict) -> dict:
    cid = canary["id"]
    trigger = canary["trigger"]
    direction = canary.get("direction", 1)
    top_n = canary.get("must_include_top", 10)
    must_include = canary.get("must_include", [])

    results = engine.evaluate_impact(trigger, event_direction=direction)
    result_map = {r["node"]: r for r in results}
    top_nodes = {r["node"] for r in results[:top_n]}

    found = [n for n in must_include if n in top_nodes]
    missing = [n for n in must_include if n not in top_nodes]
    ok = len(missing) == 0

    detail = f"{len(found)}/{len(must_include)} targets in top {top_n}"
    if missing:
        detail += f"; missing: {', '.join(missing)}"

    target_details = []
    for n in must_include:
        r = result_map.get(n)
        if r:
            rank = [x["node"] for x in results].index(n) + 1
            target_details.append({
                "node": n,
                "rank": rank,
                "probability": r["probability"],
                "magnitude": r["magnitude"],
                "cis": r["cis"],
                "path": r["path"],
                "delay": r["delay"],
                "via_contains": r.get("via_contains", False),
            })
        else:
            target_details.append({
                "node": n, "rank": None,
                "probability": 0.0, "magnitude": 0.0, "cis": 0.0,
                "path": [], "delay": "", "via_contains": False,
            })

    return {
        "id": cid,
        "status": "PASS" if ok else "FAIL",
        "detail": detail,
        "target_details": target_details,
    }


def run_all(engine: CausalMarkovEngine, canaries: list[dict]) -> list[dict]:
    results: list[dict] = []
    for c in canaries:
        try:
            results.append(run_canary(engine, c))
        except Exception as exc:
            results.append({
                "id": c.get("id", "?"),
                "status": "ERROR",
                "detail": str(exc),
                "target_details": [],
            })
    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def print_results(results: list[dict]) -> None:
    print(f"\n{'ID':<45} {'Status':<7} Detail")
    print("-" * 100)
    for r in results:
        print(f"{r['id']:<45} {r['status']:<7} {r['detail']}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    print(f"\nPASSED: {passed}  FAILED: {failed}  ERRORS: {errors}")


def print_verbose_results(results: list[dict]) -> None:
    for r in results:
        if r["status"] == "PASS" and not r.get("target_details"):
            continue

        print(f"\n{'─'*70}")
        print(f"  {r['id']} — {r['status']}")

        for td in r.get("target_details", []):
            path_str = " → ".join(td["path"][-4:]) if td["path"] else "—"
            contains = " [CONTAINS]" if td.get("via_contains") else ""
            if td["rank"]:
                print(f"    #{td['rank']:<4} {td['node']:<30} prob={td['probability']:.5f} mag={td['magnitude']:.5f} cis={td['cis']:.5f}{contains}")
                print(f"          path: {path_str}")
            else:
                print(f"    MISS {td['node']:<30}")


if __name__ == "__main__":
    import argparse
    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults

    parser = argparse.ArgumentParser(description="Canary smoke test runner")
    parser.add_argument("canary_id", nargs="?", help="Run specific canary by ID")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed path/scoring info")
    args = parser.parse_args()

    merger = TaxonomyMerger()
    G = merger.merge()
    apply_defaults(G)

    engine = CausalMarkovEngine(G)

    canaries = load_canaries()
    if args.canary_id:
        canaries = [c for c in canaries if c["id"] == args.canary_id]
        if not canaries:
            print(f"No canary found with id '{args.canary_id}'")
            raise SystemExit(1)

    errors = validate_canary_refs(canaries, set(G.nodes()))
    if errors:
        for e in errors:
            print(f"  WARNING: {e}")

    results = run_all(engine, canaries)
    print_results(results)
    if args.verbose:
        print_verbose_results(results)

    failing = sum(1 for r in results if r["status"] != "PASS")
    raise SystemExit(1 if failing else 0)
