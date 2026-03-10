"""Apply patches to the merged taxonomy graph and show before/after comparison.

Usage:
    python -m audit.apply_patches              # Apply and show comparison
    python -m audit.apply_patches --export      # Also export patched graph
"""

import argparse
import sys
from pathlib import Path

import networkx as nx

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph.merge import TaxonomyMerger


def graph_stats(G: nx.DiGraph) -> dict:
    """Compute key stats for a graph."""
    orphans = [n for n in G.nodes() if G.degree(n) == 0]
    components = list(nx.weakly_connected_components(G))
    empty_desc = sum(
        1 for _, _, d in G.edges(data=True)
        if not d.get("description")
    )
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "orphans": len(orphans),
        "components": len(components),
        "largest_component": max(len(c) for c in components) if components else 0,
        "empty_descriptions": empty_desc,
    }


def check_path(G: nx.DiGraph, src: str, dst: str) -> bool:
    """Check if there's a directed path from src to dst."""
    if src not in G or dst not in G:
        return False
    return nx.has_path(G, src, dst)


CRITICAL_PATHS = [
    ("crude_oil", "petrol"),
    ("crude_oil", "diesel"),
    ("repo_rate", "home_loan_emi"),
    ("monsoon", "food_inflation_india"),
    ("inr_usd", "crude_oil"),
]


def print_comparison(before: dict, after: dict):
    """Print before/after comparison table."""
    print("\n" + "=" * 60)
    print("BEFORE / AFTER COMPARISON")
    print("=" * 60)
    print(f"{'Metric':<25} {'Before':>10} {'After':>10} {'Delta':>10}")
    print("-" * 60)

    for key in ["nodes", "edges", "orphans", "components", "largest_component", "empty_descriptions"]:
        b, a = before[key], after[key]
        delta = a - b
        sign = "+" if delta > 0 else ""
        label = key.replace("_", " ").title()
        print(f"{label:<25} {b:>10} {a:>10} {sign}{delta:>9}")

    print("=" * 60)


def print_path_checks(G_before: nx.DiGraph, G_after: nx.DiGraph):
    """Print critical path check results."""
    is_tty = sys.stdout.isatty()
    green = "\033[92m" if is_tty else ""
    red = "\033[91m" if is_tty else ""
    reset = "\033[0m" if is_tty else ""

    print("\nCRITICAL PATH CHECKS")
    print("-" * 60)
    print(f"{'Path':<35} {'Before':>10} {'After':>10}")
    print("-" * 60)

    for src, dst in CRITICAL_PATHS:
        before_ok = check_path(G_before, src, dst)
        after_ok = check_path(G_after, src, dst)

        b_str = f"{green}PASS{reset}" if before_ok else f"{red}FAIL{reset}"
        a_str = f"{green}PASS{reset}" if after_ok else f"{red}FAIL{reset}"
        print(f"{src} → {dst:<22} {b_str:>18} {a_str:>18}")

    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="Apply patches and compare")
    parser.add_argument("--export", action="store_true", help="Export patched graph")
    args = parser.parse_args()

    merger = TaxonomyMerger()

    # Build unpatched graph
    print("Building unpatched graph...")
    G_before = merger.merge(apply_patches=False)
    stats_before = graph_stats(G_before)
    print(f"  Nodes: {stats_before['nodes']}, Edges: {stats_before['edges']}, "
          f"Orphans: {stats_before['orphans']}, Components: {stats_before['components']}")

    # Build patched graph
    print("\nBuilding patched graph...")
    G_after = merger.merge(apply_patches=True)
    stats_after = graph_stats(G_after)
    print(f"  Nodes: {stats_after['nodes']}, Edges: {stats_after['edges']}, "
          f"Orphans: {stats_after['orphans']}, Components: {stats_after['components']}")

    # Comparison
    print_comparison(stats_before, stats_after)
    print_path_checks(G_before, G_after)

    # Export if requested
    if args.export:
        import yaml

        export_path = Path("taxonomy/merged_graph.yaml")
        nodes_data = []
        for node_id, attrs in G_after.nodes(data=True):
            entry = {"id": node_id}
            if attrs.get("aliases"):
                entry["aliases"] = list(attrs["aliases"])
            if attrs.get("category"):
                entry["category"] = attrs["category"]
            if attrs.get("source_file"):
                entry["source_file"] = attrs["source_file"]
            nodes_data.append(entry)

        edges_data = []
        for u, v, attrs in G_after.edges(data=True):
            entry = {"from": u, "to": v}
            if attrs.get("type"):
                entry["type"] = attrs["type"]
            if attrs.get("description"):
                entry["description"] = attrs["description"]
            if attrs.get("source_file"):
                entry["source_file"] = attrs["source_file"]
            edges_data.append(entry)

        export = {"nodes": nodes_data, "edges": edges_data}
        with open(export_path, "w") as f:
            yaml.dump(export, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"\nExported patched graph to {export_path}")
        print(f"  {len(nodes_data)} nodes, {len(edges_data)} edges")


if __name__ == "__main__":
    main()
