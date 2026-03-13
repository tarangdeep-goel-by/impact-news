"""Node Admin CLI for the impact graph.

CLI usage:
    python3 -m graph.admin add-node <file> <node_id> --aliases ... --category ... [--edges ...]
    python3 -m graph.admin remove-node <node_id>
    python3 -m graph.admin search <query>
    python3 -m graph.admin validate
    python3 -m graph.admin lint
"""

from __future__ import annotations

import argparse
import difflib
import logging
import re
import sys
from pathlib import Path
from typing import Any

import networkx as nx
import yaml

from graph.merge import TaxonomyMerger
from graph.quality import CANONICAL_CATEGORIES, CANONICAL_EDGE_TYPES

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NODE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

_FLAT_FILES = [f"I{i}.yaml" for i in range(1, 12)] + [f"T{i}.yaml" for i in range(1, 6)]

_PATCH_FILES = [
    "edge_patches.yaml",
    "edge_patches_generated.yaml",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _taxonomy_dir(root: Path) -> Path:
    return root / "taxonomy"


def _load_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text())


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )


def _all_flat_paths(root: Path) -> list[Path]:
    """Return paths to all flat YAML source files that exist."""
    tdir = _taxonomy_dir(root)
    return [tdir / f for f in _FLAT_FILES if (tdir / f).exists()]


def _all_patch_paths(root: Path) -> list[Path]:
    """Return paths to all patch YAML files that exist."""
    tdir = _taxonomy_dir(root)
    return [tdir / f for f in _PATCH_FILES if (tdir / f).exists()]


def _all_source_paths(root: Path) -> list[Path]:
    """All flat + patch files."""
    return _all_flat_paths(root) + _all_patch_paths(root)


def _collect_all_node_ids(root: Path) -> dict[str, str]:
    """Return {node_id: source_filename} across all flat files and patches."""
    result: dict[str, str] = {}
    for path in _all_flat_paths(root):
        data = _load_yaml(path)
        if not data:
            continue
        for node in data.get("nodes", []) or []:
            nid = node.get("id")
            if nid:
                result[nid] = path.name

    # Also scan patches for new_nodes
    for path in _all_patch_paths(root):
        data = _load_yaml(path)
        if not data:
            continue
        for node in data.get("new_nodes", []) or []:
            nid = node.get("id")
            if nid:
                result[nid] = path.name

    return result


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_add_node(args: argparse.Namespace) -> int:
    """Add a node (and optional edges) to a flat YAML file."""
    root: Path = args.root
    filename: str = args.file
    node_id: str = args.node_id
    aliases: list[str] = args.aliases or []
    category: str = args.category
    edge_specs: list[str] = args.edges or []

    # --- Validations ---

    if filename not in _FLAT_FILES:
        print(
            f"ERROR: '{filename}' is not a known flat file. "
            f"Valid: {', '.join(_FLAT_FILES)}",
            file=sys.stderr,
        )
        return 1

    target = _taxonomy_dir(root) / filename
    if not target.exists():
        print(f"ERROR: File not found: {target}", file=sys.stderr)
        return 1

    if not _NODE_ID_RE.match(node_id):
        print(
            f"ERROR: node_id '{node_id}' must match ^[a-z][a-z0-9_]*$",
            file=sys.stderr,
        )
        return 1

    if category not in CANONICAL_CATEGORIES:
        close = difflib.get_close_matches(category, CANONICAL_CATEGORIES, n=3)
        hint = f" Did you mean: {', '.join(close)}?" if close else ""
        print(f"ERROR: '{category}' is not a canonical category.{hint}", file=sys.stderr)
        return 1

    if len(aliases) < 2:
        print("ERROR: At least 2 aliases required (use --aliases).", file=sys.stderr)
        return 1

    # Check uniqueness across all source files
    existing = _collect_all_node_ids(root)
    if node_id in existing:
        print(
            f"ERROR: node_id '{node_id}' already exists in {existing[node_id]}",
            file=sys.stderr,
        )
        return 1

    # Parse edges
    parsed_edges: list[dict[str, Any]] = []
    for spec in edge_specs:
        parts = spec.split(":", 3)
        if len(parts) != 4:
            print(
                f"ERROR: Edge spec '{spec}' must be 'from:to:TYPE:description'",
                file=sys.stderr,
            )
            return 1
        e_from, e_to, e_type, e_desc = parts
        if e_type not in CANONICAL_EDGE_TYPES:
            close = difflib.get_close_matches(e_type, CANONICAL_EDGE_TYPES, n=3)
            hint = f" Did you mean: {', '.join(close)}?" if close else ""
            print(f"ERROR: Edge type '{e_type}' is not canonical.{hint}", file=sys.stderr)
            return 1
        parsed_edges.append({
            "from": e_from,
            "to": e_to,
            "type": e_type,
            "description": e_desc,
            "weight": 0.7,
            "polarity": 1,
            "delay": "SHORT_TERM",
        })

    # --- Mutation ---

    data = _load_yaml(target) or {"nodes": [], "edges": []}
    if data.get("nodes") is None:
        data["nodes"] = []
    if data.get("edges") is None:
        data["edges"] = []

    data["nodes"].append({
        "id": node_id,
        "aliases": aliases,
        "category": category,
    })

    for edge in parsed_edges:
        data["edges"].append(edge)

    _write_yaml(target, data)

    print(f"Added node '{node_id}' to {filename}")
    if parsed_edges:
        print(f"Added {len(parsed_edges)} edge(s)")

    # Auto-validate
    print("\n--- auto-validate ---")
    return cmd_validate(args)


def cmd_remove_node(args: argparse.Namespace) -> int:
    """Remove a node and all its edges from all flat files and patches."""
    root: Path = args.root
    node_id: str = args.node_id

    total_nodes_removed = 0
    total_edges_removed = 0

    # Scan flat files
    for path in _all_flat_paths(root):
        data = _load_yaml(path)
        if not data:
            continue

        nodes_before = len(data.get("nodes", []) or [])
        data["nodes"] = [n for n in (data.get("nodes") or []) if n.get("id") != node_id]
        nodes_removed = nodes_before - len(data["nodes"])

        edges_before = len(data.get("edges", []) or [])
        data["edges"] = [
            e
            for e in (data.get("edges") or [])
            if e.get("from") != node_id and e.get("to") != node_id
        ]
        edges_removed = edges_before - len(data["edges"])

        if nodes_removed or edges_removed:
            _write_yaml(path, data)
            print(f"{path.name}: removed {nodes_removed} node(s), {edges_removed} edge(s)")
            total_nodes_removed += nodes_removed
            total_edges_removed += edges_removed

    # Scan patch files
    for path in _all_patch_paths(root):
        data = _load_yaml(path)
        if not data:
            continue

        changed = False

        # new_nodes
        if data.get("new_nodes"):
            before = len(data["new_nodes"])
            data["new_nodes"] = [n for n in data["new_nodes"] if n.get("id") != node_id]
            removed = before - len(data["new_nodes"])
            if removed:
                total_nodes_removed += removed
                changed = True

        # edges
        if data.get("edges"):
            before = len(data["edges"])
            data["edges"] = [
                e
                for e in data["edges"]
                if e.get("from") != node_id and e.get("to") != node_id
            ]
            removed = before - len(data["edges"])
            if removed:
                total_edges_removed += removed
                changed = True

        # description_fills
        if data.get("description_fills"):
            before = len(data["description_fills"])
            data["description_fills"] = [
                f
                for f in data["description_fills"]
                if f.get("from") != node_id and f.get("to") != node_id
            ]
            removed = before - len(data["description_fills"])
            if removed:
                total_edges_removed += removed
                changed = True

        if changed:
            _write_yaml(path, data)
            print(f"{path.name}: patched")

    if total_nodes_removed == 0 and total_edges_removed == 0:
        print(f"Node '{node_id}' not found in any source file.")
        return 1

    print(f"\nTotal: removed {total_nodes_removed} node(s), {total_edges_removed} edge(s)")

    # Auto-validate
    print("\n--- auto-validate ---")
    return cmd_validate(args)


def cmd_search(args: argparse.Namespace) -> int:
    """Fuzzy search for nodes by ID and aliases."""
    root: Path = args.root
    query: str = args.query.lower()

    merger = TaxonomyMerger(root=root)
    G = merger.merge()

    # Build searchable index: (node_id, source_file, category, aliases)
    entries: list[tuple[str, str, str, list[str]]] = []
    for nid, attrs in G.nodes(data=True):
        entries.append((
            nid,
            attrs.get("source_file", "?"),
            attrs.get("category", ""),
            attrs.get("aliases", []),
        ))

    all_ids = [e[0] for e in entries]

    # Fuzzy match on node IDs
    fuzzy_ids = set(difflib.get_close_matches(query, all_ids, n=20, cutoff=0.4))

    # Substring match on IDs and aliases
    hits: list[tuple[str, str, str, list[str]]] = []
    for nid, source, cat, aliases in entries:
        if nid in fuzzy_ids or query in nid:
            hits.append((nid, source, cat, aliases))
            continue
        for alias in aliases:
            if query in alias.lower():
                hits.append((nid, source, cat, aliases))
                break

    if not hits:
        print(f"No matches for '{query}'")
        return 0

    hits.sort(key=lambda h: h[0])
    print(f"Found {len(hits)} match(es):\n")
    for nid, source, cat, aliases in hits:
        alias_str = ", ".join(aliases[:5])
        if len(aliases) > 5:
            alias_str += f" (+{len(aliases) - 5} more)"
        print(f"  {nid} ({source}) cat={cat} aliases=[{alias_str}]")

    return 0


def cmd_validate_dag(args: argparse.Namespace) -> int:
    """Check for cycles within same-world lateral edges (Rule 14)."""
    root: Path = args.root
    merger = TaxonomyMerger(root=root)
    G = merger.merge()

    from graph.traverse import TAXONOMY_TYPES

    # Build subgraph of only lateral edges (exclude CONTAINS, IS_A)
    lateral = nx.DiGraph()
    for src, dst, attrs in G.edges(data=True):
        if attrs.get("type") not in TAXONOMY_TYPES:
            lateral.add_edge(src, dst)

    cycles = list(nx.simple_cycles(lateral))
    if cycles:
        print(f"DAG violation: {len(cycles)} cycle(s) found:")
        for i, cycle in enumerate(cycles[:10]):
            print(f"  {i+1}. {' -> '.join(cycle)} -> {cycle[0]}")
        if len(cycles) > 10:
            print(f"  ... and {len(cycles) - 10} more")
        return 1

    print("DAG check: no cycles found in lateral edges.")
    return 0


def cmd_validate_orphans(args: argparse.Namespace) -> int:
    """Flag leaf nodes with no lateral edges (Rule 17: 1a→1b gate)."""
    root: Path = args.root
    merger = TaxonomyMerger(root=root)
    G = merger.merge()

    from graph.traverse import TAXONOMY_TYPES

    orphan_leaves: list[str] = []
    for node in G.nodes():
        # Only check leaf nodes (no CONTAINS outgoing)
        has_children = any(
            G.edges[node, s].get("type") == "CONTAINS"
            for s in G.successors(node)
        )
        if has_children:
            continue

        # Check for any lateral (non-taxonomy) edges
        has_lateral = False
        for s in G.successors(node):
            if G.edges[node, s].get("type") not in TAXONOMY_TYPES:
                has_lateral = True
                break
        if not has_lateral:
            for p in G.predecessors(node):
                if G.edges[p, node].get("type") not in TAXONOMY_TYPES:
                    has_lateral = True
                    break

        if not has_lateral:
            orphan_leaves.append(node)

    if orphan_leaves:
        print(f"Orphan leaves ({len(orphan_leaves)} nodes with no lateral edges):")
        for nid in sorted(orphan_leaves)[:30]:
            cat = G.nodes[nid].get("category", "?")
            print(f"  {nid} ({cat})")
        if len(orphan_leaves) > 30:
            print(f"  ... and {len(orphan_leaves) - 30} more")
        return 1

    print("Orphan check: all leaf nodes have lateral edges.")
    return 0


def cmd_validate_bridges(args: argparse.Namespace) -> int:
    """Verify port nodes have bridge edges, feedback delay >= MEDIUM_TERM (Rule 17: 3→4 gate)."""
    root: Path = args.root
    merger = TaxonomyMerger(root=root)
    G = merger.merge()

    issues = 0

    # Check port nodes have at least one bridge edge (T→I inbound)
    port_nodes = [n for n, attrs in G.nodes(data=True) if attrs.get("port")]
    for nid in port_nodes:
        has_bridge = False
        for pred in G.predecessors(nid):
            pred_cat = G.nodes[pred].get("category", "")
            node_cat = G.nodes[nid].get("category", "")
            # Bridge = Trigger node -> Impact node
            if pred_cat.startswith("T") and node_cat.startswith("I"):
                has_bridge = True
                break
        if not has_bridge:
            print(f"  Port node '{nid}' has no bridge edge from Trigger world")
            issues += 1

    if not port_nodes:
        print("  Warning: no port nodes found in graph")

    # Check feedback edges (I→T) have delay >= MEDIUM_TERM
    from graph.traverse import DELAY_RANK
    for src, dst, attrs in G.edges(data=True):
        src_cat = G.nodes[src].get("category", "") if src in G.nodes else ""
        dst_cat = G.nodes[dst].get("category", "") if dst in G.nodes else ""
        if src_cat.startswith("I") and dst_cat.startswith("T"):
            delay = attrs.get("delay", "SHORT_TERM")
            if DELAY_RANK.get(delay, 0) < DELAY_RANK.get("MEDIUM_TERM", 2):
                print(f"  Feedback edge {src}->{dst} has delay '{delay}' (must be >= MEDIUM_TERM)")
                issues += 1

    if issues:
        print(f"\nBridge validation: {issues} issue(s) found.")
        return 1

    print("Bridge validation: all checks passed.")
    return 0


def cmd_validate_components(args: argparse.Namespace) -> int:
    """Check weakly connected components (Rule 17: 1b→2a gate)."""
    root: Path = args.root
    merger = TaxonomyMerger(root=root)
    G = merger.merge()

    wcc = list(nx.weakly_connected_components(G))
    print(f"Weakly connected components: {len(wcc)}")

    if len(wcc) > 1:
        # Sort by size descending
        wcc_sorted = sorted(wcc, key=len, reverse=True)
        for i, comp in enumerate(wcc_sorted[:5]):
            sample = sorted(comp)[:5]
            print(f"  Component {i+1} ({len(comp)} nodes): {', '.join(sample)}{'...' if len(comp) > 5 else ''}")
        return 1

    if len(wcc) == 1:
        print("Graph is fully connected.")
    else:
        print("Graph is empty.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate inference.py references against the merged graph."""
    root: Path = args.root

    merger = TaxonomyMerger(root=root)
    G = merger.merge()

    import user.inference as _inf

    node_ids = set(G.nodes())
    missing: list[tuple[str, str]] = []  # (node_id, source_context)
    total_refs = 0

    # City map
    city_map = getattr(_inf, "CITY_GRAPH_MAP", {})
    for city, categories in city_map.items():
        for cat, nids in categories.items():
            for nid in nids:
                total_refs += 1
                if nid not in node_ids:
                    missing.append((nid, f"CITY_GRAPH_MAP[{city}][{cat}]"))

    # Tuple maps
    _MAP_NAMES = [
        "WORK_SECTOR_MAP", "HOUSING_MAP", "COMMUTE_MAP",
        "LOANS_MAP", "INVESTMENTS_MAP", "DIET_MAP",
        "DEPENDENTS_MAP", "HEALTH_MAP",
    ]
    tuple_maps: list[tuple[str, dict]] = [
        (n, getattr(_inf, n)) for n in _MAP_NAMES if hasattr(_inf, n)
    ]
    for map_name, mapping in tuple_maps:
        for key, tuples in mapping.items():
            for node_id, _rel, _imp in tuples:
                total_refs += 1
                if node_id not in node_ids:
                    missing.append((node_id, f"{map_name}[{key}]"))

    # Edge validation: every edge from/to must exist as a node
    broken_edges: list[tuple[str, str, str]] = []
    for src, dst, attrs in G.edges(data=True):
        source_file = attrs.get("source_file", "?")
        if src not in node_ids:
            broken_edges.append((src, f"{src}->{dst}", source_file))
        if dst not in node_ids:
            broken_edges.append((dst, f"{src}->{dst}", source_file))

    # Report
    ok = True

    if missing:
        ok = False
        # Deduplicate by node_id, collect contexts
        by_node: dict[str, list[str]] = {}
        for nid, ctx in missing:
            by_node.setdefault(nid, []).append(ctx)
        print(f"Missing inference refs ({len(by_node)} nodes, {len(missing)} refs):")
        for nid in sorted(by_node):
            contexts = ", ".join(by_node[nid][:3])
            if len(by_node[nid]) > 3:
                contexts += f" (+{len(by_node[nid]) - 3} more)"
            print(f"  {nid} <- {contexts}")
    else:
        print(f"Inference refs: all {total_refs} OK")

    if broken_edges:
        ok = False
        print(f"\nBroken edge refs ({len(broken_edges)}):")
        for nid, edge_str, source in broken_edges[:20]:
            print(f"  {nid} in edge {edge_str} ({source})")
    else:
        print("Edge refs: all OK")

    return 0 if ok else 1


def cmd_lint(args: argparse.Namespace) -> int:
    """Lint all source YAML files for naming and quality conventions."""
    root: Path = args.root
    issues = 0

    for path in _all_flat_paths(root):
        data = _load_yaml(path)
        if not data:
            continue
        fname = path.name

        missing_desc_count = 0
        total_edge_count = 0

        # Lint nodes
        for node in data.get("nodes", []) or []:
            nid = node.get("id", "")
            if not _NODE_ID_RE.match(nid):
                print(f"  {fname}: bad node_id '{nid}' (must match ^[a-z][a-z0-9_]*$)")
                issues += 1

            cat = node.get("category", "")
            if cat and cat not in CANONICAL_CATEGORIES:
                close = difflib.get_close_matches(cat, CANONICAL_CATEGORIES, n=2)
                hint = f" -> did you mean: {', '.join(close)}?" if close else ""
                print(f"  {fname}: non-canonical category '{cat}' on node '{nid}'{hint}")
                issues += 1

        # Lint edges
        for edge in data.get("edges", []) or []:
            total_edge_count += 1
            etype = edge.get("type", "")
            if etype and etype not in CANONICAL_EDGE_TYPES:
                close = difflib.get_close_matches(etype, CANONICAL_EDGE_TYPES, n=2)
                hint = f" -> did you mean: {', '.join(close)}?" if close else ""
                e_from = edge.get("from", "?")
                e_to = edge.get("to", "?")
                print(f"  {fname}: non-canonical edge type '{etype}' on {e_from}->{e_to}{hint}")
                issues += 1
            if not edge.get("description"):
                missing_desc_count += 1

        if missing_desc_count:
            print(f"  {fname}: {missing_desc_count}/{total_edge_count} edges missing description")
            issues += missing_desc_count

    # Lint patch files
    for path in _all_patch_paths(root):
        data = _load_yaml(path)
        if not data:
            continue
        fname = path.name

        missing_desc_count = 0
        total_edge_count = 0

        for node in data.get("new_nodes", []) or []:
            nid = node.get("id", "")
            if not _NODE_ID_RE.match(nid):
                print(f"  {fname}: bad node_id '{nid}'")
                issues += 1
            cat = node.get("category", "")
            if cat and cat not in CANONICAL_CATEGORIES:
                close = difflib.get_close_matches(cat, CANONICAL_CATEGORIES, n=2)
                hint = f" -> did you mean: {', '.join(close)}?" if close else ""
                print(f"  {fname}: non-canonical category '{cat}' on node '{nid}'{hint}")
                issues += 1

        for edge in data.get("edges", []) or []:
            total_edge_count += 1
            etype = edge.get("type", "")
            if etype and etype not in CANONICAL_EDGE_TYPES:
                close = difflib.get_close_matches(etype, CANONICAL_EDGE_TYPES, n=2)
                hint = f" -> did you mean: {', '.join(close)}?" if close else ""
                print(f"  {fname}: non-canonical edge type '{etype}'{hint}")
                issues += 1
            if not edge.get("description"):
                missing_desc_count += 1

        if missing_desc_count:
            print(f"  {fname}: {missing_desc_count}/{total_edge_count} edges missing description")
            issues += missing_desc_count

    if issues:
        print(f"\n{issues} issue(s) found.")
        return 1
    else:
        print("Lint: all clean.")
        return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m graph.admin",
        description="Node Admin CLI for the impact graph",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root")
    sub = parser.add_subparsers(dest="command", required=True)

    # add-node
    p_add = sub.add_parser("add-node", help="Add a node to a flat YAML file")
    p_add.add_argument("file", help="Target YAML filename (e.g. employment_domain_graph.yaml)")
    p_add.add_argument("node_id", help="Node ID (lowercase, underscores)")
    p_add.add_argument("--aliases", nargs="+", required=True, help="At least 2 aliases")
    p_add.add_argument("--category", required=True, help="Canonical category")
    p_add.add_argument(
        "--edges",
        nargs="*",
        default=[],
        help="Edge specs: 'from:to:TYPE:description' (repeatable)",
    )

    # remove-node
    p_rm = sub.add_parser("remove-node", help="Remove a node and its edges from all files")
    p_rm.add_argument("node_id", help="Node ID to remove")

    # search
    p_search = sub.add_parser("search", help="Fuzzy search nodes by ID or alias")
    p_search.add_argument("query", help="Search query")

    # validate
    sub.add_parser("validate", help="Validate inference.py refs against merged graph")

    # lint
    sub.add_parser("lint", help="Lint YAML files for naming/quality conventions")

    # validate-dag
    sub.add_parser("validate-dag", help="Check for cycles in lateral edges (Rule 14)")

    # validate-orphans
    sub.add_parser("validate-orphans", help="Flag leaf nodes with no lateral edges")

    # validate-bridges
    sub.add_parser("validate-bridges", help="Verify port/bridge/feedback constraints")

    # validate-components
    sub.add_parser("validate-components", help="Check weakly connected components")

    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    dispatch = {
        "add-node": cmd_add_node,
        "remove-node": cmd_remove_node,
        "search": cmd_search,
        "validate": cmd_validate,
        "lint": cmd_lint,
        "validate-dag": cmd_validate_dag,
        "validate-orphans": cmd_validate_orphans,
        "validate-bridges": cmd_validate_bridges,
        "validate-components": cmd_validate_components,
    }

    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
