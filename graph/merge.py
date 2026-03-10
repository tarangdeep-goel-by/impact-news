"""Merge 5 YAML taxonomy files into one unified graph."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from models import Edge, Node

logger = logging.getLogger(__name__)

TAXONOMY_DIR = Path(__file__).resolve().parent.parent / "taxonomy"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "merged_graph.yaml"

TREE_FILE = "universal_life_dependency_graph.yaml"
FLAT_FILES = [
    "food_energy_graph.yaml",
    "employment_domain_graph.yaml",
    "financial_system_domain_graph.yaml",
    "local_governance_graph.yaml",
]

# Keys in a tree node that are metadata, not children
_TREE_META_KEYS = {
    "id", "level", "type", "description", "aliases", "leaf",
    "universality", "children",
}


def _flatten_tree(
    data: dict,
    parent_id: str | None,
    nodes: dict[str, Node],
    edges: list[Edge],
    source_ids: set[str],
) -> None:
    """Recursively walk the tree YAML and extract nodes + CONTAINS edges."""
    node_id = data.get("id")
    is_leaf = data.get("leaf", False)

    if node_id:
        aliases = list(data.get("aliases", []))
        category = ""
        # Derive category from level-1 parent or keep empty
        node = Node(
            id=node_id,
            aliases=aliases,
            category=category,
            is_category=not is_leaf,
        )
        _merge_node(nodes, node)
        source_ids.add(node_id)

        if parent_id:
            edges.append(Edge(
                from_node=parent_id,
                to_node=node_id,
                type="CONTAINS",
                description="",
            ))

    current_id = node_id or parent_id

    # Process explicit children dict
    children = data.get("children")
    if isinstance(children, dict):
        for _key, child in children.items():
            if isinstance(child, dict):
                _flatten_tree(child, current_id, nodes, edges, source_ids)

    # Process implicit children (keys that aren't metadata)
    for key, value in data.items():
        if key in _TREE_META_KEYS:
            continue
        if isinstance(value, dict) and "id" in value:
            _flatten_tree(value, current_id, nodes, edges, source_ids)


def _merge_node(nodes: dict[str, Node], new: Node) -> None:
    """Merge a node into the nodes dict, combining aliases."""
    existing = nodes.get(new.id)
    if existing is None:
        nodes[new.id] = new
        return

    # Merge aliases (set union, preserve order)
    merged_aliases = list(dict.fromkeys(existing.aliases + new.aliases))
    existing.aliases = merged_aliases

    # Keep richest category
    if not existing.category and new.category:
        existing.category = new.category

    # is_category: true wins (more info)
    if new.is_category:
        existing.is_category = True


def _edge_key(e: Edge) -> tuple[str, str, str]:
    return (e.from_node, e.to_node, e.type)


def _load_flat_file(path: Path) -> tuple[list[Node], list[Edge]]:
    """Load a flat graph YAML (nodes + edges)."""
    with open(path) as f:
        data = yaml.safe_load(f)

    nodes: list[Node] = []
    for n in data.get("nodes", []):
        nodes.append(Node(
            id=n["id"],
            aliases=n.get("aliases", []),
            category=n.get("category", ""),
            is_category=n.get("is_category", False),
        ))

    edges: list[Edge] = []
    for e in data.get("edges", []):
        if "from" not in e or "to" not in e:
            # Malformed entry (e.g. node accidentally in edges section)
            if "id" in e:
                logger.warning("Skipping misplaced node in edges: %s", e["id"])
                nodes.append(Node(
                    id=e["id"],
                    aliases=e.get("aliases", []),
                    category=e.get("category", ""),
                ))
            else:
                logger.warning("Skipping malformed edge: %s", e)
            continue
        edges.append(Edge(
            from_node=e["from"],
            to_node=e["to"],
            type=e["type"],
            description=e.get("description", ""),
            weight=e.get("weight", 1.0),
        ))

    return nodes, edges


def merge() -> tuple[list[Node], list[Edge]]:
    """Merge all taxonomy files and return (nodes, edges)."""
    all_nodes: dict[str, Node] = {}
    all_edges: list[Edge] = []
    edge_set: dict[tuple[str, str, str], Edge] = {}
    source_stats: dict[str, int] = {}

    # --- 1. Flatten tree file ---
    tree_path = TAXONOMY_DIR / TREE_FILE
    logger.info("Loading tree: %s", tree_path.name)
    with open(tree_path) as f:
        tree_data = yaml.safe_load(f)

    tree_source_ids: set[str] = set()
    tree_edges: list[Edge] = []

    for key, value in tree_data.items():
        if key == "meta":
            continue
        if isinstance(value, dict):
            _flatten_tree(value, None, all_nodes, tree_edges, tree_source_ids)

    for e in tree_edges:
        k = _edge_key(e)
        if k not in edge_set:
            edge_set[k] = e

    source_stats[TREE_FILE] = len(tree_source_ids)
    logger.info("  Tree: %d nodes, %d edges", len(tree_source_ids), len(tree_edges))

    # --- 2. Load flat files ---
    for fname in FLAT_FILES:
        fpath = TAXONOMY_DIR / fname
        logger.info("Loading flat: %s", fpath.name)
        nodes, edges = _load_flat_file(fpath)

        file_ids: set[str] = set()
        for n in nodes:
            file_ids.add(n.id)
            _merge_node(all_nodes, n)

        for e in edges:
            k = _edge_key(e)
            existing = edge_set.get(k)
            if existing is None:
                edge_set[k] = e
            elif len(e.description) > len(existing.description):
                edge_set[k] = e

        source_stats[fname] = len(file_ids)
        logger.info("  %s: %d nodes, %d edges", fname, len(file_ids), len(edges))

    all_edges = list(edge_set.values())

    # --- 3. Validate: no broken edge refs ---
    node_ids = set(all_nodes.keys())
    broken = []
    for e in all_edges:
        if e.from_node not in node_ids:
            broken.append(f"Edge from unknown node: {e.from_node} -> {e.to_node}")
        if e.to_node not in node_ids:
            broken.append(f"Edge to unknown node: {e.from_node} -> {e.to_node}")

    if broken:
        logger.warning("Broken edge references (%d):", len(broken))
        for b in broken[:20]:
            logger.warning("  %s", b)

    # --- 4. Stats ---
    # Shared nodes: appear in >1 source
    all_source_ids: dict[str, list[str]] = {}
    # Re-scan for shared node tracking
    # Tree nodes
    for nid in tree_source_ids:
        all_source_ids.setdefault(nid, []).append(TREE_FILE)
    # Flat files
    for fname in FLAT_FILES:
        fpath = TAXONOMY_DIR / fname
        with open(fpath) as f:
            data = yaml.safe_load(f)
        for n in data.get("nodes", []):
            all_source_ids.setdefault(n["id"], []).append(fname)

    shared = sum(1 for sources in all_source_ids.values() if len(sources) > 1)

    print("\n=== Merge Stats ===")
    print(f"Total nodes: {len(all_nodes)}")
    print(f"Total edges: {len(all_edges)}")
    print(f"Broken refs: {len(broken)}")
    print(f"Shared nodes (in >1 file): {shared}")
    print("\nPer source:")
    for fname, count in source_stats.items():
        print(f"  {fname}: {count} nodes")
    print()

    return list(all_nodes.values()), all_edges


def export(nodes: list[Node], edges: list[Edge]) -> None:
    """Write merged graph to YAML."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_files = [TREE_FILE] + FLAT_FILES
    out = {
        "meta": {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_files": source_files,
        },
        "nodes": [
            {
                "id": n.id,
                "aliases": n.aliases,
                "category": n.category,
                "is_category": n.is_category,
            }
            for n in sorted(nodes, key=lambda x: x.id)
        ],
        "edges": [
            {
                "from": e.from_node,
                "to": e.to_node,
                "type": e.type,
                "description": e.description,
            }
            for e in sorted(edges, key=lambda x: (x.from_node, x.to_node, x.type))
        ],
    }

    with open(OUTPUT_FILE, "w") as f:
        yaml.dump(out, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"Written to {OUTPUT_FILE}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    nodes, edges = merge()
    export(nodes, edges)


if __name__ == "__main__":
    main()
