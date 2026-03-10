"""Impact propagation engine with elevator logic."""

from __future__ import annotations

import heapq

import networkx as nx

CAUSAL_TYPES = {"AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES", "DEPENDS_ON"}
TAXONOMY_TYPES = {"IS_A", "CONTAINS"}

DELAY_RANK = {"IMMEDIATE": 0, "SHORT_TERM": 1, "MEDIUM_TERM": 2, "LONG_TERM": 3}
DELAY_LABELS = {v: k for k, v in DELAY_RANK.items()}


def get_causal_entry(g: nx.DiGraph, node_id: str) -> str:
    """Walk UP IS_A edges until finding a node with causal out-edges."""
    visited: set[str] = set()
    current = node_id

    while current not in visited:
        visited.add(current)

        # Check if current node has any outgoing causal edges
        has_causal = any(
            g.edges[current, succ].get("type") in CAUSAL_TYPES
            for succ in g.successors(current)
        )
        if has_causal:
            return current

        # Follow IS_A edges upward (successors where edge type == IS_A)
        parent = None
        for succ in g.successors(current):
            if g.edges[current, succ].get("type") == "IS_A":
                if succ not in visited:
                    parent = succ
                    break

        if parent is None:
            break
        current = parent

    return node_id


def analyze_impact(
    g: nx.DiGraph,
    trigger_node: str,
    event_direction: int = 1,
    threshold: float = 0.05,
    max_depth: int = 6,
) -> list[dict]:
    """Modified Dijkstra with max-product paths for impact propagation."""
    entry = get_causal_entry(g, trigger_node)

    # max-heap via negated weights
    # (neg_weight, node, polarity, path, delay_str)
    heap: list[tuple[float, str, int, list[str], str]] = []
    heapq.heappush(heap, (-1.0, entry, event_direction, [entry], "IMMEDIATE"))

    max_weight_seen: dict[str, float] = {entry: 1.0}
    results: list[dict] = []

    while heap:
        neg_w, node, polarity, path, delay_str = heapq.heappop(heap)
        current_weight = -neg_w

        if len(path) > max_depth + 1:
            continue

        # Record this node (skip the trigger itself)
        if node != entry:
            results.append({
                "node": node,
                "score": current_weight,
                "polarity": polarity,
                "delay": delay_str,
                "path": list(path),
            })

        current_delay_rank = DELAY_RANK.get(delay_str, 1)

        for succ in g.successors(node):
            edge_attrs = g.edges[node, succ]
            edge_type = edge_attrs.get("type", "")

            # Skip taxonomy edges
            if edge_type in TAXONOMY_TYPES:
                continue

            edge_weight = edge_attrs.get("weight", 1.0)
            edge_polarity = edge_attrs.get("polarity", 0)
            edge_delay = edge_attrs.get("delay", "SHORT_TERM")

            new_weight = current_weight * edge_weight

            if new_weight < threshold:
                continue

            new_polarity = polarity * edge_polarity if edge_polarity != 0 else 0

            edge_delay_rank = DELAY_RANK.get(edge_delay, 1)
            new_delay_rank = max(current_delay_rank, edge_delay_rank)
            new_delay = DELAY_LABELS.get(new_delay_rank, "SHORT_TERM")

            # Only push if better than previously seen
            if new_weight > max_weight_seen.get(succ, 0.0):
                max_weight_seen[succ] = new_weight
                heapq.heappush(heap, (-new_weight, succ, new_polarity, path + [succ], new_delay))

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def main():
    import argparse

    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults, apply_fan_out_penalty

    parser = argparse.ArgumentParser(description="Analyze impact propagation")
    parser.add_argument("node", help="Trigger node ID")
    parser.add_argument("--direction", choices=["up", "down"], default="up", help="Event direction")
    parser.add_argument("--threshold", type=float, default=0.05)
    parser.add_argument("--max-depth", type=int, default=6)
    args = parser.parse_args()

    merger = TaxonomyMerger()
    G = merger.merge()
    apply_defaults(G)
    apply_fan_out_penalty(G)

    direction = 1 if args.direction == "up" else -1

    entry = get_causal_entry(G, args.node)
    if entry != args.node:
        print(f"Elevator: {args.node} → {entry}")

    impacts = analyze_impact(G, args.node, direction, args.threshold, args.max_depth)

    print(f"\nImpact analysis for '{args.node}' (direction={'↑' if direction == 1 else '↓'}):")
    print(f"{'Node':<35} {'Score':>6} {'Pol':>4} {'Delay':<12} Path")
    print("-" * 100)
    for imp in impacts[:30]:
        pol_sym = {1: "+", -1: "−", 0: "?"}[imp["polarity"]]
        path_str = " → ".join(imp["path"][-3:])
        print(f"{imp['node']:<35} {imp['score']:>6.3f} {pol_sym:>4} {imp['delay']:<12} {path_str}")

    print(f"\nTotal impacted nodes: {len(impacts)}")


if __name__ == "__main__":
    main()
