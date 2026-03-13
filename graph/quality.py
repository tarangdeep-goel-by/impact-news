"""Quality scorecard for the impact graph.

CLI usage:
    python3 -m graph.quality          # human-readable table
    python3 -m graph.quality --json   # JSON output
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
import yaml
from pydantic import BaseModel, Field

from graph.merge import TaxonomyMerger
from graph.migrate_weights import apply_defaults, apply_fan_out_penalty
from graph.traverse import CAUSAL_TYPES, TAXONOMY_TYPES

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical constants (importable by other modules)
# ---------------------------------------------------------------------------

CANONICAL_CATEGORIES: set[str] = {
    "T1", "T2", "T3", "T4", "T5",
    "I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "I9", "I10", "I11",
}  # 16 L1 categories (5 Trigger + 11 Impact)

CANONICAL_EDGE_TYPES: set[str] = {
    "AFFECTS",
    "PRODUCES",
    "REGULATES",
    "DISRUPTS",
    "SUPPLIES",
    "DEPENDS_ON",
    "CONTAINS",
    "IS_A",
    "FUNDS",
    "COMPETES_WITH",
    "EMPLOYS",
    "MANAGES",
}  # 12 types

# ---------------------------------------------------------------------------
# Persona definitions for coverage simulation
# ---------------------------------------------------------------------------

PERSONAS: dict[str, dict[str, Any]] = {
    "bangalore_it": {
        "city": "bangalore",
        "work_sector": "IT",
        "housing": "rent",
        "commute": ["metro", "auto_cab"],
        "loans": ["personal", "credit_card"],
        "investments": ["stocks", "mf"],
        "diet": "non_veg",
        "dependents": ["spouse"],
        "health": ["none"],
    },
    "delhi_govt": {
        "city": "delhi",
        "work_sector": "Government",
        "housing": "own_loan",
        "commute": ["car"],
        "loans": ["home"],
        "investments": ["fd", "ppf_nps"],
        "diet": "veg",
        "dependents": ["school_children", "parents"],
        "health": ["bp"],
    },
    "mumbai_freelancer": {
        "city": "mumbai",
        "work_sector": "Startups",
        "housing": "rent",
        "commute": ["wfh"],
        "loans": ["credit_card"],
        "investments": ["crypto", "stocks"],
        "diet": "non_veg",
        "dependents": ["none"],
        "health": ["mental_health"],
    },
    "patna_farmer": {
        "city": "patna",
        "work_sector": "Agriculture",
        "housing": "own_clear",
        "commute": ["bike"],
        "loans": ["none"],
        "investments": ["gold"],
        "diet": "veg",
        "dependents": ["spouse", "school_children", "parents"],
        "health": ["diabetes"],
    },
    "lucknow_student": {
        "city": "lucknow",
        "work_sector": "Other",
        "housing": "rent",
        "commute": ["bus"],
        "loans": ["education"],
        "investments": ["none"],
        "diet": "no_restriction",
        "dependents": ["none"],
        "health": ["none"],
    },
}

# ---------------------------------------------------------------------------
# Pydantic report models
# ---------------------------------------------------------------------------


class AliasReport(BaseModel):
    total_nodes: int = 0
    nodes_with_3plus: int = 0
    ratio: float = 0.0


class EdgeDescriptionReport(BaseModel):
    total_edges: int = 0
    edges_with_desc: int = 0
    ratio: float = 0.0
    worst_files: list[tuple[str, int, int]] = Field(
        default_factory=list,
        description="(source_file, missing_count, total_count) sorted by missing desc",
    )


class DeadEndReport(BaseModel):
    total_nodes: int = 0
    dead_end_count: int = 0
    ratio: float = 0.0
    examples: list[str] = Field(default_factory=list, description="First 20 dead-end node IDs")


class CategoryReport(BaseModel):
    canonical_count: int = 0
    non_canonical: dict[str, int] = Field(
        default_factory=dict,
        description="Non-canonical category -> node count",
    )


class EdgeTypeReport(BaseModel):
    canonical_count: int = 0
    non_canonical: dict[str, int] = Field(
        default_factory=dict,
        description="Non-canonical edge type -> edge count",
    )


class OverlapReport(BaseModel):
    total_overlapping: int = 0
    overlaps: dict[str, list[str]] = Field(
        default_factory=dict,
        description="node_id -> list of source files it appears in",
    )


class ConnectivityReport(BaseModel):
    orphan_count: int = 0
    weakly_connected_components: int = 0


class PersonaCoverage(BaseModel):
    name: str
    direct_edges: int = 0
    reachable_count: int = 0
    reachable_pct: float = 0.0


class UserCoverageReport(BaseModel):
    personas: list[PersonaCoverage] = Field(default_factory=list)
    avg_reachable_pct: float = 0.0


class InferenceValidation(BaseModel):
    total_refs: int = 0
    missing_count: int = 0
    missing_nodes: list[str] = Field(default_factory=list)


class QualityScorecard(BaseModel):
    timestamp: str = ""
    node_count: int = 0
    edge_count: int = 0
    aliases: AliasReport = Field(default_factory=AliasReport)
    edge_descriptions: EdgeDescriptionReport = Field(default_factory=EdgeDescriptionReport)
    dead_ends: DeadEndReport = Field(default_factory=DeadEndReport)
    categories: CategoryReport = Field(default_factory=CategoryReport)
    edge_types: EdgeTypeReport = Field(default_factory=EdgeTypeReport)
    overlap: OverlapReport = Field(default_factory=OverlapReport)
    connectivity: ConnectivityReport = Field(default_factory=ConnectivityReport)
    user_coverage: UserCoverageReport = Field(default_factory=UserCoverageReport)
    inference_refs: InferenceValidation = Field(default_factory=InferenceValidation)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class QualityAnalyzer:
    """Run all quality checks against the merged impact graph."""

    # Source YAML files to scan for overlap analysis
    _YAML_SOURCES = [
        f"taxonomy/I{i}.yaml" for i in range(1, 12)
    ] + [
        f"taxonomy/T{i}.yaml" for i in range(1, 6)
    ]

    def __init__(self, root: Path = Path.cwd()) -> None:
        self.root = root

    def run(self) -> QualityScorecard:
        """Build graph, run all checks, return scorecard."""
        merger = TaxonomyMerger(root=self.root)
        G = merger.merge()
        apply_defaults(G)
        apply_fan_out_penalty(G)

        sc = QualityScorecard(
            timestamp=datetime.now(timezone.utc).isoformat(),
            node_count=G.number_of_nodes(),
            edge_count=G.number_of_edges(),
            aliases=self._analyze_aliases(G),
            edge_descriptions=self._analyze_edge_descriptions(G),
            dead_ends=self._analyze_dead_ends(G),
            categories=self._analyze_categories(G),
            edge_types=self._analyze_edge_types(G),
            overlap=self._analyze_overlap(),
            connectivity=self._analyze_connectivity(G),
            user_coverage=self._simulate_personas(G),
            inference_refs=self._validate_inference_refs(G),
        )
        return sc

    # -- individual checks ---------------------------------------------------

    @staticmethod
    def _analyze_aliases(G: nx.DiGraph) -> AliasReport:
        """Count nodes with 3+ aliases."""
        total = G.number_of_nodes()
        count_3plus = sum(
            1 for _, attrs in G.nodes(data=True) if len(attrs.get("aliases", [])) >= 3
        )
        return AliasReport(
            total_nodes=total,
            nodes_with_3plus=count_3plus,
            ratio=round(count_3plus / total, 4) if total else 0.0,
        )

    @staticmethod
    def _analyze_edge_descriptions(G: nx.DiGraph) -> EdgeDescriptionReport:
        """Count edges with non-empty descriptions; report worst source files."""
        total = G.number_of_edges()
        with_desc = 0
        file_stats: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # [missing, total]

        for _, _, attrs in G.edges(data=True):
            source = attrs.get("source_file", "unknown")
            file_stats[source][1] += 1
            if attrs.get("description"):
                with_desc += 1
            else:
                file_stats[source][0] += 1

        worst = sorted(file_stats.items(), key=lambda kv: kv[1][0], reverse=True)
        worst_tuples = [(f, counts[0], counts[1]) for f, counts in worst if counts[0] > 0]

        return EdgeDescriptionReport(
            total_edges=total,
            edges_with_desc=with_desc,
            ratio=round(with_desc / total, 4) if total else 0.0,
            worst_files=worst_tuples,
        )

    @staticmethod
    def _analyze_dead_ends(G: nx.DiGraph) -> DeadEndReport:
        """Nodes with ONLY taxonomy edges (IS_A/CONTAINS), no causal edges."""
        total = G.number_of_nodes()
        dead_ends: list[str] = []

        for node in G.nodes():
            has_causal = False
            for succ in G.successors(node):
                if G.edges[node, succ].get("type") not in TAXONOMY_TYPES:
                    has_causal = True
                    break
            if not has_causal:
                for pred in G.predecessors(node):
                    if G.edges[pred, node].get("type") not in TAXONOMY_TYPES:
                        has_causal = True
                        break
            if not has_causal:
                dead_ends.append(node)

        return DeadEndReport(
            total_nodes=total,
            dead_end_count=len(dead_ends),
            ratio=round(len(dead_ends) / total, 4) if total else 0.0,
            examples=sorted(dead_ends)[:20],
        )

    @staticmethod
    def _analyze_categories(G: nx.DiGraph) -> CategoryReport:
        """Check node categories against CANONICAL_CATEGORIES."""
        canonical = 0
        non_canonical: Counter[str] = Counter()

        for _, attrs in G.nodes(data=True):
            cat = attrs.get("category", "")
            if not cat:
                non_canonical["(empty)"] += 1
            elif cat in CANONICAL_CATEGORIES:
                canonical += 1
            else:
                non_canonical[cat] += 1

        return CategoryReport(
            canonical_count=canonical,
            non_canonical=dict(non_canonical.most_common()),
        )

    @staticmethod
    def _analyze_edge_types(G: nx.DiGraph) -> EdgeTypeReport:
        """Check edge types against CANONICAL_EDGE_TYPES."""
        canonical = 0
        non_canonical: Counter[str] = Counter()

        for _, _, attrs in G.edges(data=True):
            etype = attrs.get("type", "")
            if not etype:
                non_canonical["(empty)"] += 1
            elif etype in CANONICAL_EDGE_TYPES:
                canonical += 1
            else:
                non_canonical[etype] += 1

        return EdgeTypeReport(
            canonical_count=canonical,
            non_canonical=dict(non_canonical.most_common()),
        )

    def _analyze_overlap(self) -> OverlapReport:
        """Read raw YAML files, find nodes appearing in multiple source files."""
        node_sources: dict[str, list[str]] = defaultdict(list)

        for rel_path in self._YAML_SOURCES:
            path = self.root / rel_path
            if not path.exists():
                continue
            data = yaml.safe_load(path.read_text())
            if data is None:
                continue

            fname = path.name
            seen_in_file: set[str] = set()

            # Flat files have a top-level "nodes" list
            for node in data.get("nodes", []) or []:
                nid = node.get("id")
                if nid:
                    seen_in_file.add(nid)

            # Tree file: walk recursively to extract IDs
            if not data.get("nodes"):
                self._walk_yaml_ids(data, seen_in_file)

            for nid in seen_in_file:
                node_sources[nid].append(fname)

        overlaps = {nid: srcs for nid, srcs in sorted(node_sources.items()) if len(srcs) > 1}

        return OverlapReport(
            total_overlapping=len(overlaps),
            overlaps=overlaps,
        )

    @staticmethod
    def _walk_yaml_ids(data: dict[str, Any], out: set[str]) -> None:
        """Recursively extract 'id' fields from a tree-structured YAML dict."""
        if not isinstance(data, dict):
            return
        if "id" in data:
            out.add(data["id"])
        for key, val in data.items():
            if key in ("id", "level", "type", "description", "aliases", "leaf", "universality"):
                continue
            if isinstance(val, dict):
                QualityAnalyzer._walk_yaml_ids(val, out)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        QualityAnalyzer._walk_yaml_ids(item, out)

    @staticmethod
    def _analyze_connectivity(G: nx.DiGraph) -> ConnectivityReport:
        """Orphan count and weakly connected components."""
        orphans = sum(1 for n in G.nodes() if G.degree(n) == 0)
        wcc = nx.number_weakly_connected_components(G)
        return ConnectivityReport(orphan_count=orphans, weakly_connected_components=wcc)

    @staticmethod
    def _simulate_personas(G: nx.DiGraph) -> UserCoverageReport:
        """Run connect_user_to_graph for each persona, report reachable %."""
        from graph.graph import ImpactGraph
        from user.inference import connect_user_to_graph

        # Build an ImpactGraph backed by the already-merged DiGraph
        ig = ImpactGraph.__new__(ImpactGraph)
        ig.g = G

        total_nodes = G.number_of_nodes()
        results: list[PersonaCoverage] = []

        for name, answers in PERSONAS.items():
            ug = connect_user_to_graph(answers, ig, user_id=name)
            reachable = len(ug.reachable_nodes)
            pct = round(reachable / total_nodes * 100, 2) if total_nodes else 0.0
            results.append(
                PersonaCoverage(
                    name=name,
                    direct_edges=len(ug.edges),
                    reachable_count=reachable,
                    reachable_pct=pct,
                )
            )

        avg = round(sum(p.reachable_pct for p in results) / len(results), 2) if results else 0.0
        return UserCoverageReport(personas=results, avg_reachable_pct=avg)

    @staticmethod
    def _validate_inference_refs(G: nx.DiGraph) -> InferenceValidation:
        """Check that every node_id referenced in inference maps exists in graph.

        Callable standalone — used by merge.py post-merge hook.
        """
        from user.inference import (
            CITY_GRAPH_MAP,
            COMMUTE_MAP,
            DEPENDENTS_MAP,
            DIET_MAP,
            HEALTH_MAP,
            HOUSING_MAP,
            INVESTMENTS_MAP,
            LOANS_MAP,
            WORK_SECTOR_MAP,
        )

        all_refs: set[str] = set()

        # City map: nested dict[str, dict[str, list[str]]]
        for _city, categories in CITY_GRAPH_MAP.items():
            for _cat, node_ids in categories.items():
                for nid in node_ids:
                    all_refs.add(nid)

        # Tuple maps: dict[str, list[tuple[str, str, float]]]
        tuple_maps = [
            WORK_SECTOR_MAP,
            HOUSING_MAP,
            COMMUTE_MAP,
            LOANS_MAP,
            INVESTMENTS_MAP,
            DIET_MAP,
            DEPENDENTS_MAP,
            HEALTH_MAP,
        ]
        for mapping in tuple_maps:
            for _key, tuples in mapping.items():
                for node_id, _rel, _imp in tuples:
                    all_refs.add(node_id)

        node_ids = set(G.nodes())
        missing = sorted(all_refs - node_ids)

        return InferenceValidation(
            total_refs=len(all_refs),
            missing_count=len(missing),
            missing_nodes=missing,
        )


# ---------------------------------------------------------------------------
# CLI display
# ---------------------------------------------------------------------------

_THRESHOLDS = {
    "alias_density": (0.80, 0.60),      # (good, warn) — ratio of nodes with 3+ aliases
    "edge_descriptions": (0.90, 0.70),   # ratio of edges with description
    "dead_end_ratio": (0.10, 0.25),      # inverted — lower is better
    "user_coverage": (30.0, 15.0),       # avg reachable %
}


def _status(value: float, good: float, warn: float, *, invert: bool = False) -> str:
    """Return a status indicator based on thresholds."""
    if invert:
        # Lower is better (e.g. dead-end ratio)
        if value <= good:
            return "ok"
        if value <= warn:
            return "!! below {:.0%}".format(good)
        return "!! below {:.0%}".format(warn)
    else:
        if value >= good:
            return "ok"
        if value >= warn:
            return "!! below {:.0%}".format(good)
        return "!! below {:.0%}".format(good)


def print_scorecard(sc: QualityScorecard) -> None:
    """Print human-readable quality report."""
    print("=== Impact Graph Quality Scorecard ===")
    print(
        f"Nodes: {sc.node_count:,} | Edges: {sc.edge_count:,} "
        f"| Components: {sc.connectivity.weakly_connected_components}"
    )
    print(f"Timestamp: {sc.timestamp}\n")

    rows: list[tuple[str, str, str]] = []

    # Alias density
    alias_pct = sc.aliases.ratio * 100
    rows.append((
        "Alias density (3+)",
        f"{alias_pct:.1f}%",
        _status(sc.aliases.ratio, *_THRESHOLDS["alias_density"]),
    ))

    # Edge descriptions
    desc_pct = sc.edge_descriptions.ratio * 100
    rows.append((
        "Edge descriptions",
        f"{desc_pct:.1f}%",
        _status(sc.edge_descriptions.ratio, *_THRESHOLDS["edge_descriptions"]),
    ))

    # Dead ends
    de_pct = sc.dead_ends.ratio * 100
    rows.append((
        "Dead-end ratio",
        f"{de_pct:.1f}%",
        _status(sc.dead_ends.ratio, *_THRESHOLDS["dead_end_ratio"], invert=True),
    ))

    # Connectivity
    rows.append(("Orphan nodes", str(sc.connectivity.orphan_count), ""))
    rows.append(("Weakly connected components", str(sc.connectivity.weakly_connected_components), ""))

    # Categories
    nc_cats = len(sc.categories.non_canonical)
    rows.append((
        "Non-canonical categories",
        str(nc_cats),
        "ok" if nc_cats == 0 else f"!! {nc_cats} non-canonical",
    ))

    # Edge types
    nc_types = len(sc.edge_types.non_canonical)
    rows.append((
        "Non-canonical edge types",
        str(nc_types),
        "ok" if nc_types == 0 else f"!! {nc_types} non-canonical",
    ))

    # Overlap
    rows.append(("Node overlaps (multi-file)", str(sc.overlap.total_overlapping), ""))

    # Inference refs
    rows.append((
        "Inference missing refs",
        str(sc.inference_refs.missing_count),
        "ok" if sc.inference_refs.missing_count == 0 else f"!! {sc.inference_refs.missing_count} missing",
    ))

    # User coverage
    rows.append((
        "Avg persona coverage",
        f"{sc.user_coverage.avg_reachable_pct:.1f}%",
        _status(sc.user_coverage.avg_reachable_pct, *_THRESHOLDS["user_coverage"]),
    ))

    # Print table
    col_w = max(len(r[0]) for r in rows) + 2
    print(f"{'Dimension':<{col_w}} {'Score':>8}    Status")
    print("-" * (col_w + 25))
    for label, score, status in rows:
        print(f"{label:<{col_w}} {score:>8}    {status}")

    # Detail: non-canonical categories
    if sc.categories.non_canonical:
        print(f"\nNon-canonical categories ({len(sc.categories.non_canonical)}):")
        for cat, count in sorted(sc.categories.non_canonical.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")

    # Detail: non-canonical edge types
    if sc.edge_types.non_canonical:
        print(f"\nNon-canonical edge types ({len(sc.edge_types.non_canonical)}):")
        for etype, count in sorted(sc.edge_types.non_canonical.items(), key=lambda x: -x[1]):
            print(f"  {etype}: {count}")

    # Detail: worst files for edge descriptions
    if sc.edge_descriptions.worst_files:
        print("\nWorst files for missing edge descriptions:")
        for fname, missing, total in sc.edge_descriptions.worst_files[:5]:
            print(f"  {fname}: {missing}/{total} missing")

    # Detail: dead-end examples
    if sc.dead_ends.examples:
        print(f"\nDead-end examples (first {len(sc.dead_ends.examples)}):")
        for nid in sc.dead_ends.examples:
            print(f"  {nid}")

    # Detail: missing inference refs
    if sc.inference_refs.missing_nodes:
        print(f"\nMissing inference refs ({sc.inference_refs.missing_count}):")
        for nid in sc.inference_refs.missing_nodes:
            print(f"  {nid}")

    # Detail: persona coverage
    print("\nPersona coverage breakdown:")
    for p in sc.user_coverage.personas:
        print(
            f"  {p.name:<20} edges={p.direct_edges:>3}  "
            f"reachable={p.reachable_count:>5}  ({p.reachable_pct:.1f}%)"
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Impact graph quality scorecard")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    analyzer = QualityAnalyzer(root=args.root)
    scorecard = analyzer.run()

    if args.json:
        print(scorecard.model_dump_json(indent=2))
    else:
        print_scorecard(scorecard)


if __name__ == "__main__":
    main()
