"""Merge taxonomy YAML files into a single NetworkX DiGraph."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import networkx as nx
import yaml

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------


class TaxonomyMerger:
    TAXONOMY_DIR = Path("taxonomy")
    FLAT_FILES = [
        "employment_domain_graph.yaml",
        "financial_system_domain_graph.yaml",
        "food_energy_graph.yaml",
        "local_governance_graph.yaml",
    ]
    TREE_FILE = "universal_life_dependency_graph.yaml"
    PATCH_FILES = [
        "taxonomy/edge_patches.yaml",
        "taxonomy/edge_patches_generated.yaml",
    ]

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.cwd()

    # -- public ------------------------------------------------------------

    def merge(self, apply_patches: bool = True) -> nx.DiGraph:
        """Load all taxonomy sources, optionally apply patches, return merged graph."""
        G = nx.DiGraph()

        # Flat graphs
        for fname in self.FLAT_FILES:
            path = self.root / self.TAXONOMY_DIR / fname
            if path.exists():
                self._load_flat(G, path)
            else:
                log.warning("Flat file not found, skipping: %s", path)

        # Universal tree
        tree_path = self.root / self.TAXONOMY_DIR / self.TREE_FILE
        if tree_path.exists():
            self._load_tree(G, tree_path)
        else:
            log.warning("Tree file not found, skipping: %s", tree_path)

        # Patches
        if apply_patches:
            for rel in self.PATCH_FILES:
                patch_path = self.root / rel
                if patch_path.exists():
                    self._apply_patches(G, patch_path)

        return G

    # -- flat loader -------------------------------------------------------

    def _load_flat(self, G: nx.DiGraph, path: Path) -> None:
        data = yaml.safe_load(path.read_text())
        if data is None:
            return
        source = path.name

        for node in data.get("nodes", []) or []:
            nid = node["id"]
            aliases = list(node.get("aliases") or [])
            category = node.get("category", "")
            if G.has_node(nid):
                # Merge: union aliases, keep first category
                existing = G.nodes[nid]
                merged_aliases = list(dict.fromkeys(existing.get("aliases", []) + aliases))
                existing["aliases"] = merged_aliases
            else:
                G.add_node(nid, aliases=aliases, category=category, source_file=source)

        for i, edge in enumerate(data.get("edges", []) or []):
            if "from" not in edge or "to" not in edge:
                log.warning("Skipping malformed edge #%d in %s: %s", i, source, edge)
                continue
            G.add_edge(
                edge["from"],
                edge["to"],
                type=edge.get("type", ""),
                description=edge.get("description", ""),
                source_file=source,
            )

    # -- tree loader -------------------------------------------------------

    def _load_tree(self, G: nx.DiGraph, path: Path) -> None:
        data = yaml.safe_load(path.read_text())
        if data is None:
            return
        source = path.name

        for key, value in data.items():
            if key == "meta":
                continue
            if isinstance(value, dict) and "id" in value:
                self._walk_tree(G, value, parent_id=None, category=key, source=source)

    def _walk_tree(
        self,
        G: nx.DiGraph,
        node: dict[str, Any],
        parent_id: str | None,
        category: str,
        source: str,
    ) -> None:
        nid = node["id"]
        aliases = list(node.get("aliases") or [])

        if G.has_node(nid):
            existing = G.nodes[nid]
            merged_aliases = list(dict.fromkeys(existing.get("aliases", []) + aliases))
            existing["aliases"] = merged_aliases
        else:
            G.add_node(nid, aliases=aliases, category=category, source_file=source)

        if parent_id is not None:
            G.add_edge(parent_id, nid, type="CONTAINS", description="", source_file=source)

        # Recurse into child dicts
        for key, value in node.items():
            if key in ("id", "level", "type", "description", "aliases", "leaf", "universality"):
                continue
            if key == "children":
                # Explicit children dict
                for _child_key, child_val in value.items():
                    if isinstance(child_val, dict) and "id" in child_val:
                        self._walk_tree(G, child_val, parent_id=nid, category=category, source=source)
            elif isinstance(value, dict) and "id" in value:
                # Inline child
                self._walk_tree(G, value, parent_id=nid, category=category, source=source)

    # -- patch applicator --------------------------------------------------

    def _apply_patches(self, G: nx.DiGraph, patch_path: Path) -> None:
        data = yaml.safe_load(patch_path.read_text())
        if data is None:
            return

        # 0. New nodes (must come before edges so patch edges can reference them)
        for node in data.get("new_nodes", []) or []:
            nid = node["id"]
            if not G.has_node(nid):
                G.add_node(
                    nid,
                    aliases=list(node.get("aliases") or []),
                    category=node.get("category", ""),
                    source_file=patch_path.name,
                )

        # 1. Node merges
        for merge in data.get("node_merges", []) or []:
            keep = merge["keep"]
            targets = merge.get("merge")
            if not targets:
                continue
            if isinstance(targets, str):
                targets = [targets]
            for old in targets:
                if not G.has_node(old):
                    continue
                # Union aliases
                if G.has_node(keep):
                    keep_aliases = G.nodes[keep].get("aliases", [])
                    old_aliases = G.nodes[old].get("aliases", [])
                    G.nodes[keep]["aliases"] = list(dict.fromkeys(keep_aliases + old_aliases))
                # Redirect edges
                for pred in list(G.predecessors(old)):
                    edata = G.edges[pred, old]
                    if not G.has_edge(pred, keep):
                        G.add_edge(pred, keep, **edata)
                for succ in list(G.successors(old)):
                    edata = G.edges[old, succ]
                    if not G.has_edge(keep, succ):
                        G.add_edge(keep, succ, **edata)
                G.remove_node(old)

        # 2. New edges
        for edge in data.get("edges", []) or []:
            src, dst = edge["from"], edge["to"]
            if not G.has_node(src):
                log.warning("Patch edge source node missing: %s", src)
            if not G.has_node(dst):
                log.warning("Patch edge target node missing: %s", dst)
            G.add_edge(
                src,
                dst,
                type=edge.get("type", ""),
                description=edge.get("description", ""),
                source_file=patch_path.name,
            )

        # 3. Description fills
        for fill in data.get("description_fills", []) or []:
            src, dst = fill["from"], fill["to"]
            if G.has_edge(src, dst):
                existing = G.edges[src, dst].get("description")
                if not existing:
                    G.edges[src, dst]["description"] = fill["description"]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_graph(G: nx.DiGraph, path: Path) -> None:
    """Write merged graph to YAML."""
    nodes = []
    for nid, attrs in sorted(G.nodes(data=True)):
        nodes.append(
            {
                "id": nid,
                "aliases": attrs.get("aliases", []),
                "category": attrs.get("category", ""),
                "source_file": attrs.get("source_file", ""),
            }
        )

    edges = []
    for src, dst, attrs in sorted(G.edges(data=True)):
        edges.append(
            {
                "from": src,
                "to": dst,
                "type": attrs.get("type", ""),
                "description": attrs.get("description", ""),
                "source_file": attrs.get("source_file", ""),
            }
        )

    path.write_text(yaml.dump({"nodes": nodes, "edges": edges}, default_flow_style=False, sort_keys=False, allow_unicode=True))


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def print_stats(G: nx.DiGraph) -> None:
    orphans = sum(1 for n in G.nodes() if G.degree(n) == 0)
    wcc = nx.number_weakly_connected_components(G)
    print(f"Nodes:  {G.number_of_nodes()}")
    print(f"Edges:  {G.number_of_edges()}")
    print(f"Weakly connected components: {wcc}")
    print(f"Orphan nodes (degree 0):     {orphans}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge taxonomy graphs")
    parser.add_argument("--export", action="store_true", help="Write merged_graph.yaml")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    merger = TaxonomyMerger(root=args.root)
    G = merger.merge()
    print_stats(G)

    if args.export:
        out = args.root / "taxonomy" / "merged_graph.yaml"
        export_graph(G, out)
        print(f"\nExported to {out}")


if __name__ == "__main__":
    main()
