"""Personalized PageRank impact scoring engine.

3-layer scoring system:
- Layer 1 (Probability): PPR steady-state distribution from trigger node
- Layer 2 (Magnitude): Hub-penalized causal strength along dominant path
- Layer 3 (Timing): Delay aggregation along dominant path
"""

from __future__ import annotations

import math
import logging

import networkx as nx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (shared across graph modules)
# ---------------------------------------------------------------------------

CAUSAL_TYPES = {"AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES", "DEPENDS_ON",
                "FUNDS", "COMPETES_WITH", "EMPLOYS", "MANAGES"}
TAXONOMY_TYPES = {"IS_A"}  # CONTAINS is followed for downward hierarchy propagation

DELAY_RANK = {"IMMEDIATE": 0, "SHORT_TERM": 1, "MEDIUM_TERM": 2, "LONG_TERM": 3}
DELAY_LABELS = {v: k for k, v in DELAY_RANK.items()}


# ---------------------------------------------------------------------------
# Graph utilities (shared across graph modules)
# ---------------------------------------------------------------------------


def get_causal_entry(g: nx.DiGraph, node_id: str) -> str:
    """Walk UP the hierarchy until finding a node with causal out-edges.

    Supports both IS_A (child→parent as successor) and CONTAINS (parent→child,
    so we walk up by checking predecessors with CONTAINS type).

    If node_id is not in the graph, returns node_id unchanged (caller should
    handle the missing-node case).
    """
    if node_id not in g:
        return node_id

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


def _has_causal_outedges(g: nx.DiGraph, node: str) -> bool:
    """Check if node has any outgoing causal (non-CONTAINS, non-IS_A) edges."""
    for _, _, data in g.out_edges(node, data=True):
        if data.get('type') in CAUSAL_TYPES:
            return True
    return False


def _get_contains_parent(g: nx.DiGraph, node: str) -> str | None:
    """Get the CONTAINS parent of a node (one level up)."""
    for pred in g.predecessors(node):
        if g[pred][node].get('type') == 'CONTAINS':
            return pred
    return None


def _aggregate_upward(
    g: nx.DiGraph,
    reached_scores: dict[str, float],
) -> dict[str, dict]:
    """Roll up leaf impact scores to parent category nodes.

    For each category node (is_category=True), computes:
    - score: mean score of hit children * coverage
    - coverage: fraction of direct children that were reached
    - diversity: fraction of distinct L3 branches hit (for L2 parents)
    - hit_children: list of reached child node IDs
    - total_children: total child count

    Returns dict: {parent_id: {score, coverage, diversity, hit_children, total_children}}
    """
    aggregated: dict[str, dict] = {}

    for node in g.nodes():
        node_data = g.nodes[node]
        if not node_data.get('is_category'):
            continue

        # Get direct CONTAINS children
        children = []
        for _, child, data in g.out_edges(node, data=True):
            if data.get('type') == 'CONTAINS':
                children.append(child)

        if not children:
            continue

        # Find which children were reached
        hit_children = [c for c in children if c in reached_scores]
        if not hit_children:
            continue

        coverage = len(hit_children) / len(children)
        mean_score = sum(reached_scores[c] for c in hit_children) / len(hit_children)

        # Diversity: for L2 parents, count distinct L3 branches hit
        # For L3 parents, diversity = 1 (they ARE the branch)
        node_level = node_data.get('level', 0)
        if node_level <= 2:
            category_children = [c for c in children if g.nodes.get(c, {}).get('is_category')]
            l3_branches_hit: set[str] = set()
            for child in hit_children:
                child_data = g.nodes.get(child, {})
                if child_data.get('is_category'):
                    l3_branches_hit.add(child)
                else:
                    # Walk up to find the L3 parent
                    for pred in g.predecessors(child):
                        if g[pred][child].get('type') == 'CONTAINS':
                            l3_branches_hit.add(pred)
                            break
            diversity = len(l3_branches_hit) / max(len(category_children), 1)
        else:
            diversity = 1.0

        aggregated[node] = {
            'score': mean_score * coverage,
            'coverage': coverage,
            'diversity': diversity,
            'hit_children': hit_children,
            'total_children': len(children),
        }

    return aggregated


class CausalMarkovEngine:
    """PPR-based impact scoring engine."""

    def __init__(self, base_graph: nx.DiGraph):
        self.base_G = base_graph
        self.causal_G = self._build_causal_graph()
        self._precompute_path_costs()

    def _build_causal_graph(self) -> nx.DiGraph:
        """Build a subgraph with only causal edges (no CONTAINS/IS_A).

        Strips hierarchy edges. Removes self-loops. Only causal edge types
        from CAUSAL_TYPES are included.
        """
        causal_G = nx.DiGraph()

        # Add all nodes (needed for PPR even if they have no causal edges)
        for node, data in self.base_G.nodes(data=True):
            causal_G.add_node(node, **data)

        for u, v, d in self.base_G.edges(data=True):
            if u == v:  # Skip self-loops
                continue
            if d.get("type") in CAUSAL_TYPES:
                causal_G.add_edge(u, v, **d)

        logger.info(
            "Causal subgraph: %d nodes, %d edges (from %d total)",
            causal_G.number_of_nodes(),
            causal_G.number_of_edges(),
            self.base_G.number_of_edges(),
        )
        return causal_G

    def _precompute_path_costs(self) -> None:
        """Precompute -log(P) edge costs for dominant path extraction.

        Row-normalizes outgoing causal weights per node, then sets
        cost = -log(normalized_prob) for shortest-path computation.
        """
        for u in self.causal_G.nodes():
            out_edges = list(self.causal_G.out_edges(u, data=True))
            if not out_edges:
                continue

            total_weight = sum(d.get("weight", 0.5) for _, _, d in out_edges)
            if total_weight <= 0:
                continue

            for _, v, d in out_edges:
                raw_w = d.get("weight", 0.5)
                prob = raw_w / total_weight
                # -log transform: shortest path = highest probability path
                d["cost"] = -math.log(prob) if prob > 0 else float("inf")
                d["norm_prob"] = prob

    def _compute_ppr(
        self, trigger: str, restart_prob: float = 0.20
    ) -> dict[str, float]:
        """Run Personalized PageRank from a trigger node.

        Args:
            trigger: The trigger node ID (must be in causal_G)
            restart_prob: Probability of restarting at trigger (α).
                Higher = shock stays closer to trigger.

        Returns:
            Dict mapping node_id → PPR probability score.
        """
        if trigger not in self.causal_G:
            logger.warning("Trigger '%s' not in causal graph", trigger)
            return {}

        personalization = {trigger: 1.0}
        dangling = {trigger: 1.0}  # Dangling nodes restart at trigger

        try:
            scores = nx.pagerank(
                self.causal_G,
                alpha=1.0 - restart_prob,  # nx alpha = probability of following edges
                personalization=personalization,
                dangling=dangling,
                weight="weight",
                max_iter=200,
                tol=1e-8,
            )
        except nx.PowerIterationFailedConvergence:
            logger.warning("PPR failed to converge for trigger '%s'", trigger)
            scores = nx.pagerank(
                self.causal_G,
                alpha=1.0 - restart_prob,
                personalization=personalization,
                dangling=dangling,
                weight="weight",
                max_iter=500,
                tol=1e-6,
            )

        return scores

    def _get_dominant_path(self, trigger: str, target: str) -> list[str] | None:
        """Find the highest-probability path from trigger to target.

        Uses shortest-path on -log(P) costs (shortest = most probable).
        """
        if not self.causal_G.has_node(trigger) or not self.causal_G.has_node(target):
            return None

        try:
            return nx.shortest_path(
                self.causal_G, trigger, target, weight="cost"
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def _compute_path_metrics(
        self, path: list[str]
    ) -> tuple[float, str, int]:
        """Compute magnitude, timing, and polarity along a path.

        Returns:
            (magnitude, delay_label, polarity)
        """
        total_delay = 0
        magnitude = 1.0
        polarity = 1

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if not self.causal_G.has_edge(u, v):
                continue

            edge = self.causal_G[u][v]

            # Timing: sum delay integers
            edge_delay = edge.get("delay", "SHORT_TERM")
            total_delay += DELAY_RANK.get(edge_delay, 1)

            # Polarity: multiply
            edge_pol = edge.get("polarity", 0)
            if edge_pol != 0:
                polarity *= edge_pol
            else:
                polarity = 0

            # Magnitude: raw weight × hub penalty
            raw_w = edge.get("weight", 0.5)
            out_degree = self.causal_G.out_degree(u)
            if out_degree > 1:
                hub_penalty = 1.0 / math.log2(out_degree + 1)
            else:
                hub_penalty = 1.0
            magnitude *= raw_w * hub_penalty

        # Map delay sum back to label (cap at LONG_TERM)
        delay_label = DELAY_LABELS.get(min(total_delay, 3), "LONG_TERM")

        return magnitude, delay_label, polarity

    def _propagate_contains_down(
        self,
        reached_scores: dict[str, dict],
        threshold: float = 0.001,
    ) -> dict[str, dict]:
        """Propagate scores downward through CONTAINS edges.

        If a category node (e.g. agriculture) is reached by PPR,
        its CONTAINS children inherit the score × CONTAINS weight.

        Uses the base graph (which has CONTAINS edges), not causal_G.
        """
        queue = list(reached_scores.keys())
        visited: set[str] = set()

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)

            parent_result = reached_scores.get(node)
            if not parent_result:
                continue

            for succ in self.base_G.successors(node):
                if self.base_G.edges[node, succ].get("type") != "CONTAINS":
                    continue

                edge_w = self.base_G.edges[node, succ].get("weight", 0.9)
                child_prob = parent_result["probability"] * edge_w
                child_mag = parent_result["magnitude"] * edge_w

                if child_prob < threshold:
                    continue

                child_score = child_prob * child_mag

                if succ not in reached_scores or reached_scores[succ]["probability"] < child_prob:
                    reached_scores[succ] = {
                        "node": succ,
                        "probability": child_prob,
                        "magnitude": child_mag,
                        "score": child_score,
                        "polarity": parent_result["polarity"],
                        "delay": parent_result["delay"],
                        "path": parent_result["path"] + [succ],
                    }
                    queue.append(succ)

        return reached_scores

    def evaluate_impact(
        self,
        trigger_node: str,
        event_direction: int = 1,
        restart_prob: float = 0.20,
        prob_threshold: float = 0.005,
        max_depth: int = 6,
        include_aggregation: bool = False,
    ) -> list[dict] | tuple[list[dict], dict[str, dict]]:
        """Evaluate impact of a trigger using PPR + path analysis.

        1. Elevator: walk trigger up to causal entry point
        2. PPR: compute probability distribution from trigger
        3. Paths: for each node above threshold, find dominant path
        4. Metrics: compute magnitude, timing, polarity along path
        5. CONTAINS: propagate scores to hierarchy children
        6. Aggregation: optional upward roll-up for category nodes

        Args:
            trigger_node: Node ID where the shock originates
            event_direction: +1 (increase) or -1 (decrease)
            restart_prob: PPR restart probability (α)
            prob_threshold: Min PPR probability to include a node
            max_depth: Max path length (for path filtering)
            include_aggregation: If True, return (results, aggregation) tuple

        Returns:
            List of dicts with keys: node, probability, magnitude, score, polarity, delay, path
            If include_aggregation: tuple of (results, aggregation_dict)
        """
        # Step 1: Elevator — find causal entry point
        entry = get_causal_entry(self.base_G, trigger_node)

        # Scoped elevator: also try one CONTAINS parent up
        trigger_for_ppr = entry
        if not any(self.causal_G.has_edge(entry, s) for s in self.causal_G.successors(entry)):
            parent = _get_contains_parent(self.base_G, entry)
            if parent and parent in self.causal_G:
                trigger_for_ppr = parent

        # Step 2: PPR
        ppr_scores = self._compute_ppr(trigger_for_ppr, restart_prob)
        if not ppr_scores:
            if include_aggregation:
                return [], {}
            return []

        # Step 3-4: For each node above threshold, get path + metrics
        reached_scores: dict[str, dict] = {}

        for node, prob in ppr_scores.items():
            if node == trigger_for_ppr:
                continue  # Skip the trigger itself
            if prob < prob_threshold:
                continue

            # Get dominant path
            path = self._get_dominant_path(trigger_for_ppr, node)
            if path is None:
                # Node reached by PPR but no direct path (dangling redistribution)
                continue

            if len(path) - 1 > max_depth:
                continue

            # Compute path metrics
            magnitude, delay, polarity = self._compute_path_metrics(path)

            # Apply event direction to polarity
            final_polarity = polarity * event_direction

            reached_scores[node] = {
                "node": node,
                "probability": prob,
                "magnitude": magnitude,
                "score": prob * magnitude,  # Combined score
                "polarity": final_polarity,
                "delay": delay,
                "path": path,
            }

        # Step 5: CONTAINS propagation (downward)
        reached_scores = self._propagate_contains_down(
            reached_scores, threshold=prob_threshold
        )

        # Build results list, sorted by probability descending
        results = list(reached_scores.values())
        results.sort(key=lambda x: x["probability"], reverse=True)

        if include_aggregation:
            score_map = {r["node"]: r["probability"] for r in results}
            aggregation = _aggregate_upward(self.base_G, score_map)
            return results, aggregation

        return results


def main():
    import argparse

    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults

    parser = argparse.ArgumentParser(description="PPR impact analysis")
    parser.add_argument("node", help="Trigger node ID")
    parser.add_argument("--direction", choices=["up", "down"], default="up")
    parser.add_argument("--restart", type=float, default=0.20, help="Restart probability (α)")
    parser.add_argument("--threshold", type=float, default=0.005)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--top", type=int, default=30, help="Show top N results")
    args = parser.parse_args()

    merger = TaxonomyMerger()
    G = merger.merge()
    apply_defaults(G)

    if args.node not in G:
        print(f"Error: node '{args.node}' not found in graph ({G.number_of_nodes()} nodes).")
        # Suggest close matches
        from difflib import get_close_matches
        matches = get_close_matches(args.node, list(G.nodes()), n=5, cutoff=0.4)
        if matches:
            print(f"Did you mean: {', '.join(matches)}")
        return

    engine = CausalMarkovEngine(G)

    direction = 1 if args.direction == "up" else -1

    entry = get_causal_entry(G, args.node)
    if entry != args.node:
        print(f"Elevator: {args.node} → {entry}")

    results = engine.evaluate_impact(
        args.node,
        event_direction=direction,
        restart_prob=args.restart,
        prob_threshold=args.threshold,
        max_depth=args.max_depth,
    )

    print(f"\nPPR Impact Analysis for '{args.node}' (α={args.restart}, direction={'↑' if direction == 1 else '↓'}):")
    print(f"{'Node':<35} {'Prob':>8} {'Mag':>8} {'Score':>8} {'Pol':>4} {'Delay':<12} Path")
    print("-" * 110)

    for imp in results[:args.top]:
        pol_sym = {1: "+", -1: "−", 0: "?"}[imp["polarity"]]
        path_str = " → ".join(imp["path"][-3:])
        print(
            f"{imp['node']:<35} {imp['probability']:>8.5f} {imp['magnitude']:>8.5f} "
            f"{imp['score']:>8.6f} {pol_sym:>4} {imp['delay']:<12} {path_str}"
        )

    print(f"\nTotal impacted nodes: {len(results)}")

    # Stats
    if results:
        probs = [r["probability"] for r in results]
        mags = [r["magnitude"] for r in results]
        print(f"Probability range: {min(probs):.6f} – {max(probs):.6f}")
        print(f"Magnitude range: {min(mags):.6f} – {max(mags):.6f}")


if __name__ == "__main__":
    main()
