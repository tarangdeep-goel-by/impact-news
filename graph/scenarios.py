"""Scenario-based test runner for the impact knowledge graph.

Supports three scenario types:
  A (path_exists)     -- specific path src->dst exists
  B (reachability)    -- trigger reaches multiple targets
  C (score_threshold) -- target reachable with score >= X
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import networkx as nx
import yaml

from graph.traverse import analyze_impact, get_causal_entry, _has_causal_outedges, _get_contains_parent, TAXONOMY_TYPES

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIOS = ROOT / "taxonomy" / "scenarios.yaml"


# ---------------------------------------------------------------------------
# Load & validate
# ---------------------------------------------------------------------------


def load_scenarios(path: Path | None = None) -> list[dict]:
    """Load scenario definitions from YAML."""
    p = path or DEFAULT_SCENARIOS
    data = yaml.safe_load(p.read_text())
    return data.get("scenarios", []) or []


def validate_scenario_refs(
    scenarios: list[dict], known_nodes: set[str]
) -> list[str]:
    """Return error strings for any node IDs not present in the graph."""
    errors: list[str] = []
    for sc in scenarios:
        sid = sc.get("id", "?")
        for field in ("trigger_node", "target_node"):
            nid = sc.get(field)
            if nid and nid not in known_nodes:
                errors.append(f"[{sid}] {field} '{nid}' not in graph")
        for nid in sc.get("target_nodes", []) or []:
            if nid not in known_nodes:
                errors.append(f"[{sid}] target_nodes '{nid}' not in graph")
    return errors


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------


def _build_causal_subgraph(G: nx.DiGraph) -> nx.DiGraph:
    causal_edges = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get("type") not in TAXONOMY_TYPES
    ]
    return G.edge_subgraph(causal_edges).copy()


def _run_path_exists(G: nx.DiGraph, G_causal: nx.DiGraph, sc: dict) -> dict:
    src = sc["trigger_node"]
    dst = sc["target_node"]
    expected = sc.get("expected", "REACHABLE")
    cutoff = sc.get("max_hops", 6)

    # Scoped elevator: mirrors analyze_impact's scoped seeding.
    # Try from the node itself, its causal entry, and one parent up.
    sources = [src]
    if G.has_node(src):
        entry = get_causal_entry(G, src)
        if entry != src:
            sources.append(entry)
        parent = _get_contains_parent(G, entry)
        if parent and parent not in sources:
            sources.append(parent)

    paths: list[list[str]] = []
    for s in sources:
        if not G_causal.has_node(s) or not G_causal.has_node(dst):
            continue
        if nx.has_path(G_causal, s, dst):
            paths = list(nx.all_simple_paths(G_causal, s, dst, cutoff=cutoff))
            if paths:
                break

    found = len(paths) > 0
    shortest = min(len(p) - 1 for p in paths) if paths else 0

    if expected == "REACHABLE":
        ok = found
    else:
        ok = not found

    detail = f"{len(paths)} path(s)"
    if paths:
        detail += f", shortest {shortest} hop(s)"
    if entry != src:
        detail += f" (via elevator: {src}→{entry})"

    return {"id": sc["id"], "type": "A", "status": "PASS" if ok else "FAIL", "detail": detail}


def _run_reachability(G: nx.DiGraph, sc: dict) -> dict:
    trigger = sc["trigger_node"]
    targets = sc.get("target_nodes", [])
    direction = sc.get("direction", 1)
    threshold = sc.get("threshold", 0.05)

    results = analyze_impact(G, trigger, event_direction=direction, threshold=threshold)
    hit_nodes = {r["node"] for r in results}

    missing = [t for t in targets if t not in hit_nodes]
    ok = len(missing) == 0

    detail = f"{len(targets) - len(missing)}/{len(targets)} targets hit"
    if missing:
        detail += f"; missing: {', '.join(missing)}"

    return {"id": sc["id"], "type": "B", "status": "PASS" if ok else "FAIL", "detail": detail}


def _run_score_threshold(G: nx.DiGraph, sc: dict) -> dict:
    trigger = sc["trigger_node"]
    target = sc["target_node"]
    min_score = sc.get("min_score", 0.1)
    direction = sc.get("direction", 1)

    results = analyze_impact(G, trigger, event_direction=direction)
    hit = next((r for r in results if r["node"] == target), None)

    if hit is None:
        return {
            "id": sc["id"], "type": "C", "status": "FAIL",
            "detail": f"target '{target}' not reached",
        }

    ok = hit["score"] >= min_score
    detail = f"score {hit['score']:.3f} (need >= {min_score})"
    return {"id": sc["id"], "type": "C", "status": "PASS" if ok else "FAIL", "detail": detail}


def run_scenario(G: nx.DiGraph, scenario: dict) -> dict:
    """Run a single scenario and return result dict."""
    stype = scenario.get("type", "")

    if stype == "A":
        G_causal = _build_causal_subgraph(G)
        return _run_path_exists(G, G_causal, scenario)
    elif stype == "B":
        return _run_reachability(G, scenario)
    elif stype == "C":
        return _run_score_threshold(G, scenario)
    else:
        return {
            "id": scenario.get("id", "?"), "type": "?", "status": "ERROR",
            "detail": f"unknown scenario type '{stype}'",
        }


def run_all(G: nx.DiGraph, scenarios: list[dict]) -> list[dict]:
    """Run all scenarios, catching exceptions as ERROR status."""
    results: list[dict] = []
    for sc in scenarios:
        try:
            results.append(run_scenario(G, sc))
        except Exception as exc:
            results.append({
                "id": sc.get("id", "?"),
                "type": sc.get("type", "?"),
                "status": "ERROR",
                "detail": str(exc),
            })
    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def print_results(results: list[dict]) -> None:
    """Print formatted results table."""
    print(f"\n{'ID':<40} {'Type':<6} {'Status':<7} Detail")
    print("-" * 90)
    for r in results:
        print(f"{r['id']:<40} {r['type']:<6} {r['status']:<7} {r['detail']}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    print(f"\nPASSED: {passed}  FAILED: {failed}  ERRORS: {errors}")


def export_failures(results: list[dict], path: Path) -> None:
    """Export failed/error scenarios to JSON."""
    failures = [r for r in results if r["status"] in ("FAIL", "ERROR")]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(failures, indent=2))
    log.info("Exported %d failure(s) to %s", len(failures), path)
