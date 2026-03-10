"""
Diagnostic script for the Impact News taxonomy graph.

Loads all 5 YAML taxonomy files, builds a merged NetworkX DiGraph,
and reports summary stats, orphans, components, critical paths,
empty descriptions, cross-domain density, and potential duplicates.

Usage:
    cd /path/to/impact-news && python -m audit.analyze [--patched]
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import networkx as nx
import yaml

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

_USE_COLOR = sys.stdout.isatty()


def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m" if _USE_COLOR else s


def _red(s: str) -> str:
    return f"\033[31m{s}\033[0m" if _USE_COLOR else s


def _bold(s: str) -> str:
    return f"\033[1m{s}\033[0m" if _USE_COLOR else s


def _cyan(s: str) -> str:
    return f"\033[36m{s}\033[0m" if _USE_COLOR else s


def _yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m" if _USE_COLOR else s


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------

TAXONOMY_DIR = Path(__file__).resolve().parent.parent / "taxonomy"

FLAT_FILES = [
    "employment_domain_graph.yaml",
    "financial_system_domain_graph.yaml",
    "food_energy_graph.yaml",
    "local_governance_graph.yaml",
]

TREE_FILE = "universal_life_dependency_graph.yaml"

PATCH_FILES = [
    "edge_patches.yaml",
    "edge_patches_generated.yaml",
]


def _load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Flat-file parser
# ---------------------------------------------------------------------------


def _parse_flat(
    data: dict, source: str
) -> tuple[list[dict], list[dict]]:
    """Return (nodes, edges) from a flat nodes/edges YAML."""
    nodes = []
    for n in data.get("nodes", []):
        node = dict(n)
        node["_source"] = source
        nodes.append(node)

    edges = []
    for e in data.get("edges", []):
        edge = dict(e)
        edge["_source"] = source
        edges.append(edge)

    return nodes, edges


# ---------------------------------------------------------------------------
# Universal tree parser (recursive)
# ---------------------------------------------------------------------------


def _parse_tree_recursive(
    obj: Any,
    source: str,
    parent_id: str | None = None,
    nodes: list[dict] | None = None,
    edges: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Recursively walk the universal tree. Any dict with an 'id' field is a node."""
    if nodes is None:
        nodes = []
    if edges is None:
        edges = []

    if not isinstance(obj, dict):
        return nodes, edges

    # If this dict has an 'id', it's a node
    if "id" in obj:
        node_id = obj["id"]
        node: dict[str, Any] = {
            "id": node_id,
            "_source": source,
        }
        if "aliases" in obj:
            node["aliases"] = obj["aliases"]
        if "category" in obj:
            node["category"] = obj["category"]
        if "level" in obj:
            node["level"] = obj["level"]
        if "type" in obj:
            node["category"] = obj.get("category", obj.get("type", "universal"))
        if "description" in obj:
            node["description"] = obj["description"]
        if "universality" in obj:
            node["universality"] = obj["universality"]
        if "leaf" in obj:
            node["leaf"] = obj["leaf"]
        nodes.append(node)

        # Create CONTAINS edge from parent
        if parent_id is not None:
            edges.append(
                {
                    "from": parent_id,
                    "to": node_id,
                    "type": "CONTAINS",
                    "description": f"{parent_id} contains {node_id}",
                    "_source": source,
                }
            )

        # Recurse into children
        for key, val in obj.items():
            if key in (
                "id", "level", "type", "description", "aliases",
                "category", "leaf", "universality",
            ):
                continue
            if isinstance(val, dict):
                _parse_tree_recursive(val, source, parent_id=node_id, nodes=nodes, edges=edges)
    else:
        # No id — just recurse into all dict values
        for key, val in obj.items():
            if isinstance(val, dict):
                _parse_tree_recursive(val, source, parent_id=parent_id, nodes=nodes, edges=edges)

    return nodes, edges


def _parse_universal_tree(data: dict, source: str) -> tuple[list[dict], list[dict]]:
    """Parse the universal life dependency graph (hierarchical tree format)."""
    nodes: list[dict] = []
    edges: list[dict] = []
    for top_key, top_val in data.items():
        if top_key == "meta":
            continue
        if isinstance(top_val, dict):
            _parse_tree_recursive(top_val, source, parent_id=None, nodes=nodes, edges=edges)
    return nodes, edges


# ---------------------------------------------------------------------------
# Graph building
# ---------------------------------------------------------------------------


def build_graph(
    patched: bool = False,
) -> tuple[nx.DiGraph, dict[str, list[dict]], dict[str, list[dict]]]:
    """Build merged DiGraph. Returns (graph, nodes_by_source, edges_by_source)."""
    G = nx.DiGraph()
    nodes_by_source: dict[str, list[dict]] = {}
    edges_by_source: dict[str, list[dict]] = {}

    # Load flat files
    for fname in FLAT_FILES:
        path = TAXONOMY_DIR / fname
        data = _load_yaml(path)
        nodes, edges = _parse_flat(data, fname)
        nodes_by_source[fname] = nodes
        edges_by_source[fname] = edges

    # Load universal tree
    path = TAXONOMY_DIR / TREE_FILE
    data = _load_yaml(path)
    nodes, edges = _parse_universal_tree(data, TREE_FILE)
    nodes_by_source[TREE_FILE] = nodes
    edges_by_source[TREE_FILE] = edges

    # Add all nodes
    for source, nlist in nodes_by_source.items():
        for n in nlist:
            nid = n["id"]
            if nid not in G:
                G.add_node(nid, **{k: v for k, v in n.items() if k != "id"})
            else:
                # Merge: keep first source, add aliases
                existing = G.nodes[nid]
                if "aliases" in n:
                    prev = existing.get("aliases", [])
                    merged = list(set(prev + n["aliases"]))
                    existing["aliases"] = merged
                # Track all sources
                prev_sources = existing.get("_sources", [existing.get("_source", "")])
                if source not in prev_sources:
                    prev_sources.append(source)
                existing["_sources"] = prev_sources

    # Add all edges
    for source, elist in edges_by_source.items():
        for e in elist:
            if "from" not in e or "to" not in e:
                continue  # skip malformed entries (e.g. stray nodes in edges section)
            fr, to = e["from"], e["to"]
            # Ensure nodes exist (might be cross-domain references)
            if fr not in G:
                G.add_node(fr, _source=source, category="unknown")
            if to not in G:
                G.add_node(to, _source=source, category="unknown")
            G.add_edge(
                fr,
                to,
                type=e.get("type", "UNKNOWN"),
                description=e.get("description", ""),
                _source=source,
            )

    # Apply patches if requested
    if patched:
        _apply_patches(G, edges_by_source)

    return G, nodes_by_source, edges_by_source


def _apply_patches(G: nx.DiGraph, edges_by_source: dict[str, list[dict]]) -> None:
    """Load and apply edge patch files if they exist."""
    for pf in PATCH_FILES:
        path = TAXONOMY_DIR / pf
        if not path.exists():
            print(f"  [skip] {pf} not found")
            continue

        data = _load_yaml(path)
        if not data:
            continue

        patch_edges = data.get("edges", data.get("add_edges", []))
        merge_nodes = data.get("merge_nodes", [])
        fill_descriptions = data.get("fill_descriptions", data.get("descriptions", []))

        added = 0
        # Add edges
        if patch_edges:
            for e in patch_edges:
                fr, to = e["from"], e["to"]
                if fr not in G:
                    G.add_node(fr, _source=pf, category="patched")
                if to not in G:
                    G.add_node(to, _source=pf, category="patched")
                G.add_edge(
                    fr,
                    to,
                    type=e.get("type", "AFFECTS"),
                    description=e.get("description", ""),
                    _source=pf,
                )
                added += 1
            edges_by_source[pf] = patch_edges

        # Merge nodes
        merged = 0
        if merge_nodes:
            for m in merge_nodes:
                keep = m.get("keep") or m.get("target")
                remove = m.get("remove") or m.get("source") or m.get("merge")
                if not keep or not remove:
                    continue
                if remove in G and keep in G:
                    # Redirect all edges from/to `remove` to `keep`
                    for pred in list(G.predecessors(remove)):
                        edata = G.edges[pred, remove]
                        if not G.has_edge(pred, keep):
                            G.add_edge(pred, keep, **edata)
                    for succ in list(G.successors(remove)):
                        edata = G.edges[remove, succ]
                        if not G.has_edge(keep, succ):
                            G.add_edge(keep, succ, **edata)
                    G.remove_node(remove)
                    merged += 1

        # Fill descriptions
        filled = 0
        if fill_descriptions:
            for fd in fill_descriptions:
                fr = fd.get("from")
                to = fd.get("to")
                desc = fd.get("description", "")
                if fr and to and G.has_edge(fr, to) and desc:
                    G.edges[fr, to]["description"] = desc
                    filled += 1

        print(f"  [{pf}] +{added} edges, {merged} merges, {filled} descriptions filled")


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------


def report_summary(
    G: nx.DiGraph,
    nodes_by_source: dict[str, list[dict]],
    edges_by_source: dict[str, list[dict]],
) -> None:
    print(_bold("\n=== SUMMARY STATS ==="))
    print(f"  Total nodes (merged): {G.number_of_nodes()}")
    print(f"  Total edges:          {G.number_of_edges()}")
    print()
    print("  Nodes per source file:")
    for src in sorted(nodes_by_source):
        print(f"    {src:50s} {len(nodes_by_source[src]):>5d}")
    print()
    print("  Edges per source file:")
    for src in sorted(edges_by_source):
        print(f"    {src:50s} {len(edges_by_source[src]):>5d}")


def report_orphans(G: nx.DiGraph) -> None:
    print(_bold("\n=== ORPHAN NODES (zero edges) ==="))
    orphans: list[str] = [n for n in G.nodes if G.degree(n) == 0]
    if not orphans:
        print("  None found.")
        return

    print(f"  Total orphans: {len(orphans)}")

    # Group by source, then category
    by_source: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for nid in orphans:
        src = G.nodes[nid].get("_source", "unknown")
        cat = G.nodes[nid].get("category", "uncategorized")
        by_source[src][cat].append(nid)

    for src in sorted(by_source):
        print(f"\n  [{src}]")
        for cat in sorted(by_source[src]):
            ids = sorted(by_source[src][cat])
            print(f"    {cat}: {', '.join(ids[:10])}", end="")
            if len(ids) > 10:
                print(f" ... (+{len(ids) - 10} more)", end="")
            print()


def report_components(G: nx.DiGraph) -> None:
    print(_bold("\n=== CONNECTED COMPONENTS (weakly connected) ==="))
    comps = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
    print(f"  Total components: {len(comps)}")
    print(f"  Largest 5:")
    for i, comp in enumerate(comps[:5]):
        sample = sorted(comp)[:5]
        print(f"    {i + 1}. size={len(comp):>5d}  sample: {', '.join(sample)}")
    if len(comps) > 5:
        sizes = [len(c) for c in comps[5:]]
        print(f"    ... {len(comps) - 5} more (sizes: {sorted(sizes, reverse=True)[:10]})")


def report_critical_paths(G: nx.DiGraph) -> None:
    print(_bold("\n=== CRITICAL PATH CHECKS ==="))

    checks: list[tuple[str, list[str], str, list[str]]] = [
        ("crude_oil", ["crude_oil"], "petrol_price", ["petrol_price", "petrol"]),
        ("crude_oil", ["crude_oil"], "diesel_price", ["diesel_price", "diesel"]),
        ("repo_rate", ["repo_rate", "rbi_repo_rate"], "home_loan_emi", ["home_loan_emi"]),
        ("monsoon", ["monsoon"], "food_inflation", ["food_inflation", "food_inflation_india", "food_prices"]),
        ("usd_inr", ["usd_inr", "inr_usd"], "crude_oil", ["crude_oil"]),
    ]

    for label_from, from_ids, label_to, to_ids in checks:
        found = False
        used_from = None
        used_to = None
        direction = None

        # Try forward
        for fid in from_ids:
            if fid not in G:
                continue
            for tid in to_ids:
                if tid not in G:
                    continue
                if nx.has_path(G, fid, tid):
                    found = True
                    used_from = fid
                    used_to = tid
                    direction = "->"
                    break
            if found:
                break

        # For usd_inr <-> crude_oil, also try reverse
        if not found and label_from == "usd_inr":
            for tid in to_ids:
                if tid not in G:
                    continue
                for fid in from_ids:
                    if fid not in G:
                        continue
                    if nx.has_path(G, tid, fid):
                        found = True
                        used_from = tid
                        used_to = fid
                        direction = "->"
                        break
                if found:
                    break

        if found:
            try:
                path = nx.shortest_path(G, used_from, used_to)
                path_str = " -> ".join(path)
                hops = len(path) - 1
                print(f"  {_green('PASS')}  {label_from} {direction} {label_to}  ({hops} hops: {path_str})")
            except nx.NetworkXNoPath:
                print(f"  {_green('PASS')}  {label_from} {direction} {label_to}")
        else:
            missing = []
            all_ids = set(from_ids + to_ids)
            for nid in all_ids:
                if nid not in G:
                    missing.append(nid)
            detail = ""
            if missing:
                detail = f"  (missing nodes: {', '.join(missing)})"
            print(f"  {_red('FAIL')}  {label_from} -> {label_to}{detail}")


def report_empty_descriptions(G: nx.DiGraph, edges_by_source: dict[str, list[dict]]) -> None:
    print(_bold("\n=== EMPTY DESCRIPTIONS ==="))

    by_source: Counter[str] = Counter()
    total_by_source: Counter[str] = Counter()

    for u, v, data in G.edges(data=True):
        src = data.get("_source", "unknown")
        total_by_source[src] += 1
        desc = data.get("description", "")
        if not desc or not str(desc).strip():
            by_source[src] += 1

    total_empty = sum(by_source.values())
    total_edges = G.number_of_edges()
    print(f"  Total edges missing descriptions: {total_empty} / {total_edges}")
    print()

    for src in sorted(total_by_source):
        empty = by_source.get(src, 0)
        total = total_by_source[src]
        pct = (empty / total * 100) if total else 0
        bar = _red(f"{empty}/{total}") if empty > 0 else _green(f"{empty}/{total}")
        print(f"    {src:50s} {bar} ({pct:.0f}%)")


def report_cross_domain_density(G: nx.DiGraph) -> None:
    print(_bold("\n=== CROSS-DOMAIN EDGE DENSITY ==="))

    # Collect categories
    cats: set[str] = set()
    for n, data in G.nodes(data=True):
        cats.add(data.get("category", "uncategorized"))

    cats_sorted = sorted(cats)

    if len(cats_sorted) > 30:
        # Too many categories for a matrix, aggregate
        print(f"  ({len(cats_sorted)} categories found — showing top cross-domain pairs)")
        pair_counts: Counter[tuple[str, str]] = Counter()
        for u, v in G.edges():
            c1 = G.nodes[u].get("category", "uncategorized")
            c2 = G.nodes[v].get("category", "uncategorized")
            pair_counts[(c1, c2)] += 1

        # Show cross-domain only (c1 != c2)
        cross = {k: v for k, v in pair_counts.items() if k[0] != k[1]}
        for (c1, c2), count in sorted(cross.items(), key=lambda x: -x[1])[:25]:
            print(f"    {c1:30s} -> {c2:30s}  {count:>4d}")
        return

    # Build matrix
    matrix: dict[str, dict[str, int]] = {c: {c2: 0 for c2 in cats_sorted} for c in cats_sorted}
    for u, v in G.edges():
        c1 = G.nodes[u].get("category", "uncategorized")
        c2 = G.nodes[v].get("category", "uncategorized")
        matrix[c1][c2] += 1

    # Print header
    max_label = max(len(c) for c in cats_sorted)
    header = " " * (max_label + 2) + "  ".join(f"{c[:6]:>6s}" for c in cats_sorted)
    print(f"  {header}")

    for c1 in cats_sorted:
        row = f"  {c1:<{max_label}s}  " + "  ".join(
            f"{matrix[c1][c2]:>6d}" for c2 in cats_sorted
        )
        print(row)


def report_duplicates(G: nx.DiGraph) -> None:
    print(_bold("\n=== POTENTIAL DUPLICATE NODES ==="))

    all_ids = sorted(G.nodes)
    suffixes_to_strip = ["_price", "_prices", "_cost", "_costs", "_rate", "_rates"]
    plural_map: dict[str, str] = {}  # normalized -> original

    # Build normalized forms
    normalized: dict[str, list[str]] = defaultdict(list)
    for nid in all_ids:
        # Strip common suffixes
        base = nid
        for suf in suffixes_to_strip:
            if base.endswith(suf):
                base = base[: -len(suf)]
                break

        # Simple plural: strip trailing 's' if len > 4
        if base.endswith("s") and len(base) > 4 and not base.endswith("ss"):
            base_singular = base[:-1]
            # Only use singular if it produces a different key
            if base_singular != base:
                normalized[base_singular].append(nid)
                continue

        normalized[base].append(nid)

    # Find groups with more than one member
    dupes: list[list[str]] = []
    for base, ids in sorted(normalized.items()):
        if len(ids) > 1:
            dupes.append(ids)

    # Also check substring relationships for common patterns
    # e.g., "food_inflation" and "food_price_inflation"
    checked = set()
    for i, id1 in enumerate(all_ids):
        for j, id2 in enumerate(all_ids):
            if i >= j:
                continue
            key = (id1, id2)
            if key in checked:
                continue
            # Check if one is substring of other (with word boundary)
            parts1 = set(id1.split("_"))
            parts2 = set(id2.split("_"))
            # If they share 70%+ of words and differ by only suffix words
            common = parts1 & parts2
            total = parts1 | parts2
            suffix_words = {"price", "prices", "cost", "costs", "rate", "rates", "index"}
            diff = total - common
            if len(common) >= 2 and diff and diff.issubset(suffix_words):
                already_in_dupes = False
                for group in dupes:
                    if id1 in group and id2 in group:
                        already_in_dupes = True
                        break
                if not already_in_dupes:
                    # Check if either is already in a group
                    added = False
                    for group in dupes:
                        if id1 in group:
                            if id2 not in group:
                                group.append(id2)
                            added = True
                            break
                        if id2 in group:
                            if id1 not in group:
                                group.append(id1)
                            added = True
                            break
                    if not added:
                        dupes.append([id1, id2])
                checked.add(key)

    if not dupes:
        print("  No potential duplicates found.")
        return

    print(f"  Found {len(dupes)} potential duplicate groups:\n")
    for group in sorted(dupes, key=lambda g: g[0]):
        sources = set()
        for nid in group:
            if nid in G:
                src = G.nodes[nid].get("_source", "?")
                sources.add(src)
        src_str = ", ".join(sorted(sources))
        print(f"    {_yellow(' ~ '.join(sorted(group)))}")
        print(f"      sources: {src_str}")


# ---------------------------------------------------------------------------
# Comparison (--patched mode)
# ---------------------------------------------------------------------------


def report_comparison(
    G_base: nx.DiGraph,
    G_patched: nx.DiGraph,
) -> None:
    print(_bold("\n=== PATCH COMPARISON ==="))
    dn = G_patched.number_of_nodes() - G_base.number_of_nodes()
    de = G_patched.number_of_edges() - G_base.number_of_edges()
    print(f"  Nodes: {G_base.number_of_nodes()} -> {G_patched.number_of_nodes()} ({'+' if dn >= 0 else ''}{dn})")
    print(f"  Edges: {G_base.number_of_edges()} -> {G_patched.number_of_edges()} ({'+' if de >= 0 else ''}{de})")

    # Orphan comparison
    orphans_base = {n for n in G_base.nodes if G_base.degree(n) == 0}
    orphans_patched = {n for n in G_patched.nodes if G_patched.degree(n) == 0}
    print(f"  Orphans: {len(orphans_base)} -> {len(orphans_patched)} ({'+' if len(orphans_patched) - len(orphans_base) >= 0 else ''}{len(orphans_patched) - len(orphans_base)})")

    fixed = orphans_base - orphans_patched
    if fixed:
        print(f"  Orphans fixed: {', '.join(sorted(fixed)[:15])}")
        if len(fixed) > 15:
            print(f"    ... +{len(fixed) - 15} more")

    # Component comparison
    comps_base = list(nx.weakly_connected_components(G_base))
    comps_patched = list(nx.weakly_connected_components(G_patched))
    print(f"  Components: {len(comps_base)} -> {len(comps_patched)}")

    # Empty descriptions comparison
    empty_base = sum(1 for _, _, d in G_base.edges(data=True) if not d.get("description", "").strip())
    empty_patched = sum(1 for _, _, d in G_patched.edges(data=True) if not d.get("description", "").strip())
    print(f"  Empty descriptions: {empty_base} -> {empty_patched}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Taxonomy graph diagnostics")
    parser.add_argument(
        "--patched",
        action="store_true",
        help="Also load edge_patches.yaml and edge_patches_generated.yaml, show comparison",
    )
    args = parser.parse_args()

    print(_bold("Impact News — Taxonomy Graph Audit"))
    print("=" * 50)

    # Build base graph
    G, nodes_by_source, edges_by_source = build_graph(patched=False)

    report_summary(G, nodes_by_source, edges_by_source)
    report_orphans(G)
    report_components(G)
    report_critical_paths(G)
    report_empty_descriptions(G, edges_by_source)
    report_cross_domain_density(G)
    report_duplicates(G)

    # Patched comparison
    if args.patched:
        print("\n" + "=" * 50)
        print(_bold("Loading patches..."))
        G_patched, _, _ = build_graph(patched=True)
        report_comparison(G, G_patched)

        # Re-run critical paths on patched graph
        print(_bold("\n=== CRITICAL PATHS (patched) ==="))
        # Temporarily swap stdout reporting
        report_critical_paths(G_patched)

    print()


if __name__ == "__main__":
    main()
