"""Impact propagation engine with elevator logic."""

from __future__ import annotations

import heapq

import networkx as nx

from models import UserGraph

CAUSAL_TYPES = {"AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES", "DEPENDS_ON"}
TAXONOMY_TYPES = {"IS_A"}  # CONTAINS is followed for downward hierarchy propagation

DELAY_RANK = {"IMMEDIATE": 0, "SHORT_TERM": 1, "MEDIUM_TERM": 2, "LONG_TERM": 3}
DELAY_LABELS = {v: k for k, v in DELAY_RANK.items()}


def get_causal_entry(g: nx.DiGraph, node_id: str) -> str:
    """Walk UP the hierarchy until finding a node with causal out-edges.

    Supports both IS_A (child→parent as successor) and CONTAINS (parent→child,
    so we walk up by checking predecessors with CONTAINS type).
    """
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

        # Try IS_A upward (child → parent as successor)
        parent = None
        for succ in g.successors(current):
            if g.edges[current, succ].get("type") == "IS_A":
                if succ not in visited:
                    parent = succ
                    break

        # Try CONTAINS upward (parent → child, so parent is a predecessor)
        if parent is None:
            for pred in g.predecessors(current):
                if g.edges[pred, current].get("type") == "CONTAINS":
                    if pred not in visited:
                        parent = pred
                        break

        if parent is None:
            break
        current = parent

    return node_id


def _get_contains_ancestors(g: nx.DiGraph, node_id: str) -> list[tuple[str, float]]:
    """Walk UP the CONTAINS chain, returning (ancestor_id, cumulative_weight) pairs.

    Each step up multiplies by the CONTAINS edge weight (typically 0.9).
    Stops at L1 (level=1) or when no more CONTAINS parents exist.
    """
    ancestors: list[tuple[str, float]] = []
    current = node_id
    cumulative = 1.0
    visited: set[str] = {node_id}

    while True:
        parent = None
        for pred in g.predecessors(current):
            if pred not in visited and g.edges[pred, current].get("type") == "CONTAINS":
                parent = pred
                break
        if parent is None:
            break
        visited.add(parent)
        edge_w = g.edges[parent, current].get("weight", 0.9)
        cumulative *= edge_w
        level = g.nodes[parent].get("level", 0) if g.has_node(parent) else 0
        ancestors.append((parent, cumulative))
        if level <= 1:
            break
        current = parent

    return ancestors


def analyze_impact(
    g: nx.DiGraph,
    trigger_node: str,
    event_direction: int = 1,
    threshold: float = 0.05,
    max_depth: int = 6,
) -> list[dict]:
    """Modified Dijkstra with max-product paths for impact propagation.

    Seeds traversal from the trigger node AND all its CONTAINS ancestors.
    This enables L2 bridges to be reached from leaf trigger nodes.
    """
    entry = get_causal_entry(g, trigger_node)

    # max-heap via negated weights
    # (neg_weight, node, polarity, path, delay_str)
    heap: list[tuple[float, str, int, list[str], str]] = []
    heapq.heappush(heap, (-1.0, entry, event_direction, [entry], "IMMEDIATE"))

    max_weight_seen: dict[str, float] = {entry: 1.0}

    # Also seed from CONTAINS ancestors (for L2 bridge access)
    for ancestor, cum_weight in _get_contains_ancestors(g, entry):
        if cum_weight >= threshold:
            heapq.heappush(heap, (-cum_weight, ancestor, event_direction, [entry, ancestor], "IMMEDIATE"))
            max_weight_seen[ancestor] = cum_weight

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

    # Post-processing: propagate CONTAINS edges downward from all reached nodes.
    # This ensures L2 bridge targets propagate to ALL children regardless of
    # whether a longer path reached the L2 first (max_weight_seen issue).
    reached_scores = {r["node"]: r for r in results}
    reached_scores[entry] = {"node": entry, "score": 1.0, "polarity": event_direction, "delay": "IMMEDIATE", "path": [entry]}

    contains_queue = list(reached_scores.keys())
    visited_contains: set[str] = set()
    while contains_queue:
        node = contains_queue.pop(0)
        if node in visited_contains:
            continue
        visited_contains.add(node)

        parent_result = reached_scores.get(node)
        if not parent_result:
            continue

        for succ in g.successors(node):
            if g.edges[node, succ].get("type") != "CONTAINS":
                continue
            edge_w = g.edges[node, succ].get("weight", 0.9)
            child_score = parent_result["score"] * edge_w
            if child_score < threshold:
                continue
            if succ not in reached_scores or reached_scores[succ]["score"] < child_score:
                child_result = {
                    "node": succ,
                    "score": child_score,
                    "polarity": parent_result["polarity"],
                    "delay": parent_result["delay"],
                    "path": parent_result["path"] + [succ],
                }
                reached_scores[succ] = child_result
                contains_queue.append(succ)

    # Rebuild results from reached_scores (exclude entry node)
    results = [r for r in reached_scores.values() if r["node"] != entry]

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def compute_relevance(
    article_impacts: list[dict],
    user_graph: UserGraph,
) -> tuple[float, list[str]]:
    """Sparse dot product: article impact × user importance.

    Returns (relevance_score, overlapping_node_ids).

    Scoring:
      For direct UserEdge nodes: article_score × user_importance
      For reachable-only nodes:  article_score × 0.3 (indirect relevance)
    """
    article_vector = {impact["node"]: impact["score"] for impact in article_impacts}
    user_direct = {edge.node_id: edge.importance for edge in user_graph.edges}

    score = 0.0
    overlap: list[str] = []

    for node, article_score in article_vector.items():
        if node in user_direct:
            score += article_score * user_direct[node]
            overlap.append(node)
        elif node in user_graph.reachable_nodes:
            score += article_score * 0.3
            overlap.append(node)

    return score, overlap


def rank_articles(
    articles_with_impacts: list[tuple[str, list[dict]]],
    user_graph: UserGraph,
    min_relevance: float = 0.01,
) -> list[tuple[str, float, list[str]]]:
    """Rank articles by relevance. Returns [(article_id, score, overlap_nodes)]."""
    ranked: list[tuple[str, float, list[str]]] = []

    for article_id, impacts in articles_with_impacts:
        score, overlap = compute_relevance(impacts, user_graph)
        if score >= min_relevance:
            ranked.append((article_id, score, overlap))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


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
