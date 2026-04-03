"""Load taxonomy from merged graph and format as structured text for LLM prompts."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml


class TaxonomyContext:
    """Loads taxonomy from merged graph and formats for LLM prompts."""

    def __init__(
        self,
        nodes: dict[str, dict],
        children: dict[str, list[str]],
        parent: dict[str, str],
    ) -> None:
        self._nodes = nodes          # node_id -> {aliases, category, level, is_category, ...}
        self._children = children    # parent_id -> [child_id, ...] (CONTAINS)
        self._parent = parent        # child_id -> parent_id (CONTAINS)

        # Cache: category string -> node_id for L1 roots (e.g., "I3" -> "i3", "T1" -> "t1")
        self._cat_to_node: dict[str, str] = {
            info.get("category", ""): nid
            for nid, info in nodes.items()
            if info.get("level") == 1
        }

    # -- factory -----------------------------------------------------------

    @classmethod
    def from_merged_graph(
        cls, graph_path: str = "data/merged_graph.yaml"
    ) -> "TaxonomyContext":
        """Load from the merged graph YAML file."""
        path = Path(graph_path)
        with open(path) as f:
            data = yaml.safe_load(f)

        # Index nodes
        nodes: dict[str, dict] = {}
        for n in data.get("nodes", []):
            nodes[n["id"]] = n

        # Build parent/child maps from CONTAINS edges
        children: dict[str, list[str]] = defaultdict(list)
        parent: dict[str, str] = {}
        for e in data.get("edges", []):
            if e.get("type") == "CONTAINS":
                src, tgt = e["from"], e["to"]
                children[src].append(tgt)
                parent[tgt] = src

        # Sort children by level then alphabetically for stable output
        for pid in children:
            children[pid].sort(key=lambda nid: (nodes.get(nid, {}).get("level", 99), nid))

        return cls(nodes, dict(children), parent)

    # -- formatting --------------------------------------------------------

    def format_t_trees(self) -> str:
        """Format full T-tree hierarchy as indented text.

        Example output:
        T1: Natural & Planetary Systems
          meteorological_systems: Meteorological Systems, Weather & Climate Systems
            southwest_monsoon: Southwest Monsoon, Indian Monsoon
        """
        roots = self._l1_roots("T")
        return self._format_trees(roots)

    def format_i_trees(self) -> str:
        """Format full I-tree hierarchy as indented text. Same format as T-trees."""
        roots = self._l1_roots("I")
        return self._format_trees(roots)

    def format_i_trees_excluding(self, exclude_l1s: list[str]) -> str:
        """Format I-tree hierarchy excluding specified L1 categories.

        Args:
            exclude_l1s: L1 category codes to exclude, e.g. ["I7", "I11"].
                If empty, returns the full I-tree.
        """
        if not exclude_l1s:
            return self.format_i_trees()

        exclude_set = set(exclude_l1s)
        roots = [
            nid for nid in self._l1_roots("I")
            if self._nodes.get(nid, {}).get("category", "") not in exclude_set
        ]
        return self._format_trees(roots)

    # -- queries -----------------------------------------------------------

    def get_all_i_leaf_ids(self) -> set[str]:
        """Return all I-world leaf node IDs (nodes with no CONTAINS children)."""
        return {
            nid
            for nid, info in self._nodes.items()
            if info.get("category", "").startswith("I") and nid not in self._children
        }

    def get_all_i_node_ids(self) -> set[str]:
        """Return all I-world node IDs."""
        return {
            nid
            for nid, info in self._nodes.items()
            if info.get("category", "").startswith("I")
        }

    def get_all_t_node_ids(self) -> set[str]:
        """Return all T-world node IDs."""
        return {
            nid
            for nid, info in self._nodes.items()
            if info.get("category", "").startswith("T")
        }

    def node_to_l1(self, node_id: str) -> str | None:
        """Reverse lookup: node -> L1 category label (e.g. 'T1: Natural & Planetary Systems')."""
        info = self._nodes.get(node_id)
        if not info:
            return None
        cat = info.get("category", "")
        # Walk up CONTAINS chain to find L1 root
        cur = node_id
        while cur in self._parent:
            cur = self._parent[cur]
        root_info = self._nodes.get(cur)
        if root_info:
            label = self.get_node_label(cur)
            return f"{root_info.get('category', cat)}: {label}"
        return cat

    def is_ancestor_of(self, ancestor: str, descendant: str) -> bool:
        """Check if ancestor contains descendant via CONTAINS chain."""
        cur = descendant
        while cur in self._parent:
            cur = self._parent[cur]
            if cur == ancestor:
                return True
        return False

    def get_node_label(self, node_id: str) -> str:
        """Get first alias (human-readable label) for a node."""
        info = self._nodes.get(node_id)
        if not info:
            return node_id
        aliases = info.get("aliases", [])
        return aliases[0] if aliases else node_id

    # -- internals ---------------------------------------------------------

    def _l1_roots(self, prefix: str) -> list[str]:
        """Return L1 root node IDs for a world prefix ('T' or 'I'), sorted by category."""
        roots = [
            nid
            for nid, info in self._nodes.items()
            if info.get("level") == 1 and info.get("category", "").startswith(prefix)
        ]
        roots.sort(key=lambda nid: self._nodes[nid].get("category", ""))
        return roots

    def _format_trees(self, roots: list[str]) -> str:
        """Render trees from a list of root node IDs."""
        lines: list[str] = []
        for root in roots:
            self._format_subtree(root, 0, lines)
        return "\n".join(lines)

    def _format_subtree(self, node_id: str, depth: int, lines: list[str]) -> None:
        """Recursively format a node and its CONTAINS children."""
        info = self._nodes.get(node_id, {})
        aliases = info.get("aliases", [])
        indent = "  " * depth

        if depth == 0:
            # L1 root: show "T1: First Alias"
            cat = info.get("category", "")
            label = aliases[0] if aliases else node_id
            lines.append(f"{cat}: {label}")
        else:
            # Deeper nodes: "node_id: Alias1, Alias2"
            alias_str = ", ".join(aliases) if aliases else node_id
            lines.append(f"{indent}{node_id}: {alias_str}")

        for child_id in self._children.get(node_id, []):
            self._format_subtree(child_id, depth + 1, lines)
