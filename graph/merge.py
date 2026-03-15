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
    FLAT_FILES = [f"I{i}.yaml" for i in range(1, 12)] + [f"T{i}.yaml" for i in range(1, 6)] + ["bridge_edges.yaml"]
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

        # Per-L1 flat graphs
        for fname in self.FLAT_FILES:
            path = self.root / self.TAXONOMY_DIR / fname
            if path.exists():
                self._load_flat(G, path)
            else:
                log.warning("Flat file not found, skipping: %s", path)

        # Patches
        if apply_patches:
            for rel in self.PATCH_FILES:
                patch_path = self.root / rel
                if patch_path.exists():
                    self._apply_patches(G, patch_path)

        # Validate: report broken edge refs
        node_ids = set(G.nodes())
        broken = 0
        for src, dst in G.edges():
            if src not in node_ids or dst not in node_ids:
                broken += 1
                log.warning("Broken ref: %s -> %s", src, dst)
        if broken:
            log.warning("Total broken edge references: %d", broken)

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
                existing = G.nodes[nid]
                merged_aliases = list(dict.fromkeys(existing.get("aliases", []) + aliases))
                existing["aliases"] = merged_aliases
                if not existing.get("category") and category:
                    existing["category"] = category
                    existing["source_file"] = source
                # Update v4 fields if provided
                for field in ("status", "merged_into", "port", "portal", "level"):
                    val = node.get(field)
                    if val is not None:
                        existing[field] = val
                if node.get("secondary_tags"):
                    existing_tags = existing.get("secondary_tags", [])
                    existing["secondary_tags"] = list(dict.fromkeys(existing_tags + list(node["secondary_tags"])))
            else:
                G.add_node(
                    nid,
                    aliases=aliases,
                    category=category,
                    source_file=source,
                    status=node.get("status", "active"),
                    merged_into=node.get("merged_into"),
                    port=node.get("port", False),
                    portal=node.get("portal", False),
                    secondary_tags=list(node.get("secondary_tags") or []),
                    level=node.get("level"),
                    is_category=node.get("is_category", False),
                )

        for i, edge in enumerate(data.get("edges", []) or []):
            if "from" not in edge or "to" not in edge:
                log.warning("Skipping malformed edge #%d in %s: %s", i, source, edge)
                continue
            G.add_edge(
                edge["from"],
                edge["to"],
                type=edge.get("type", ""),
                description=edge.get("description", ""),
                weight=edge.get("weight", 1.0),
                polarity=edge.get("polarity", 0),
                delay=edge.get("delay", "SHORT_TERM"),
                source_file=source,
            )

    # -- patch applicator --------------------------------------------------

    def _apply_patches(self, G: nx.DiGraph, patch_path: Path) -> None:
        data = yaml.safe_load(patch_path.read_text())
        if data is None:
            return

        # 0. New nodes (must come before edges so patch edges can reference them)
        for node in data.get("new_nodes", []) or []:
            nid = node["id"]
            aliases = list(node.get("aliases") or [])
            category = node.get("category", "")
            if G.has_node(nid):
                existing = G.nodes[nid]
                merged_aliases = list(dict.fromkeys(existing.get("aliases", []) + aliases))
                existing["aliases"] = merged_aliases
                if not existing.get("category") and category:
                    existing["category"] = category
                    existing["source_file"] = patch_path.name
            else:
                G.add_node(nid, aliases=aliases, category=category, source_file=patch_path.name)

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
                weight=edge.get("weight", 1.0),
                polarity=edge.get("polarity", 0),
                delay=edge.get("delay", "SHORT_TERM"),
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
    """Write merged graph to YAML compatible with graph/graph.py (ImpactGraph)."""
    nodes = []
    for nid, attrs in sorted(G.nodes(data=True)):
        node_data: dict[str, Any] = {
            "id": nid,
            "aliases": attrs.get("aliases", []),
            "category": attrs.get("category", ""),
            "is_category": attrs.get("is_category", False),
        }
        # v4 fields — only include if non-default
        if attrs.get("status", "active") != "active":
            node_data["status"] = attrs["status"]
        if attrs.get("merged_into"):
            node_data["merged_into"] = attrs["merged_into"]
        if attrs.get("port"):
            node_data["port"] = True
        if attrs.get("portal"):
            node_data["portal"] = True
        if attrs.get("secondary_tags"):
            node_data["secondary_tags"] = attrs["secondary_tags"]
        if attrs.get("level") is not None:
            node_data["level"] = attrs["level"]
        nodes.append(node_data)

    edges = []
    for src, dst, attrs in sorted(G.edges(data=True)):
        edges.append(
            {
                "from": src,
                "to": dst,
                "type": attrs.get("type", ""),
                "description": attrs.get("description", ""),
                "weight": attrs.get("weight", 1.0),
                "polarity": attrs.get("polarity", 0),
                "delay": attrs.get("delay", "SHORT_TERM"),
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
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
    parser.add_argument("--no-export", action="store_true", help="Skip writing merged_graph.yaml")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    merger = TaxonomyMerger(root=args.root)
    G = merger.merge()
    print_stats(G)

    if not args.no_export:
        out = args.root / "data" / "merged_graph.yaml"
        export_graph(G, out)
        print(f"\nExported to {out}")



if __name__ == "__main__":
    main()
