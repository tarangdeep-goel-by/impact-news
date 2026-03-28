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

    def __init__(self, base_graph: nx.DiGraph, i_world_boost: float = 3.0,
                 category_penalty: float = 0.3, leaf_boost_l4: float = 2.0,
                 leaf_boost_l3: float = 1.2):
        self.base_G = base_graph
        self.i_world_boost = i_world_boost
        self.category_penalty = category_penalty
        self.leaf_boost_l4 = leaf_boost_l4
        self.leaf_boost_l3 = leaf_boost_l3
        self.causal_G = self._build_causal_graph()
        self._precompute_path_costs()

    def _build_causal_graph(self) -> nx.DiGraph:
        """Build a subgraph with only causal edges (no CONTAINS/IS_A).

        Strips hierarchy edges. Removes self-loops. Only causal edge types
        from CAUSAL_TYPES are included. Nodes with no causal edges are
        excluded to prevent dangling-node probability dilution in PPR.
        """
        causal_G = nx.DiGraph()

        # Collect causal edges first
        causal_edges = []
        for u, v, d in self.base_G.edges(data=True):
            if u == v:
                continue
            if d.get("type") in CAUSAL_TYPES:
                causal_edges.append((u, v, d))

        # Only add nodes that participate in at least one causal edge
        causal_nodes = set()
        for u, v, _ in causal_edges:
            causal_nodes.add(u)
            causal_nodes.add(v)

        for node in causal_nodes:
            causal_G.add_node(node, **self.base_G.nodes[node])

        for u, v, d in causal_edges:
            causal_G.add_edge(u, v, **d)

        logger.info(
            "Causal subgraph: %d nodes (%d excluded), %d edges (from %d total)",
            causal_G.number_of_nodes(),
            self.base_G.number_of_nodes() - causal_G.number_of_nodes(),
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

    def _build_seed_vector(self, trigger_node: str, decay: float = 0.5, max_levels: int = 3) -> dict[str, float]:
        """Walk UP CONTAINS hierarchy with exponential decay. Returns PPR seed dict.

        Only includes ancestors that have causal out-edges in self.causal_G.
        Normalizes values to sum to 1.0 (required by nx.pagerank personalization).
        """
        seeds: dict[str, float] = {}

        # Always include trigger if it has causal edges
        if trigger_node in self.causal_G and self.causal_G.out_degree(trigger_node) > 0:
            seeds[trigger_node] = 1.0

        # Walk up CONTAINS hierarchy
        current = trigger_node
        weight = 1.0
        for _ in range(max_levels):
            parent = _get_contains_parent(self.base_G, current)
            if parent is None:
                break
            weight *= decay
            # Only include if parent has causal out-edges in causal_G
            if parent in self.causal_G and self.causal_G.out_degree(parent) > 0:
                seeds[parent] = weight
            current = parent

        # If no seeds found (trigger has no causal edges and no ancestors do either),
        # fall back to just the trigger node with weight 1.0
        if not seeds:
            seeds[trigger_node] = 1.0

        # Normalize to sum to 1.0
        total = sum(seeds.values())
        if total > 0:
            seeds = {k: v / total for k, v in seeds.items()}

        return seeds

    def _compute_ppr(
        self, seed_vector: dict[str, float], restart_prob: float = 0.20
    ) -> dict[str, float]:
        """Run Personalized PageRank from a seed vector (multi-seed).

        Args:
            seed_vector: Dict mapping node_id → weight (must sum to 1.0).
                Represents the restart distribution for PPR.
            restart_prob: Probability of restarting at seed distribution (α).
                Higher = shock stays closer to seed nodes.

        Returns:
            Dict mapping node_id → PPR probability score.
        """
        # Filter seed vector to nodes that exist in causal_G
        valid_seeds = {k: v for k, v in seed_vector.items() if k in self.causal_G}
        if not valid_seeds:
            logger.warning("No seed nodes found in causal graph")
            return {}
        # Re-normalize
        total = sum(valid_seeds.values())
        valid_seeds = {k: v / total for k, v in valid_seeds.items()}

        personalization = valid_seeds
        dangling = valid_seeds  # Dangling nodes restart at seed distribution

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
            logger.warning("PPR failed to converge for seeds %s", list(seed_vector.keys())[:3])
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

        Magnitude uses bottleneck (min edge weight) — the weakest link in the
        causal chain determines overall strength. No hub penalty: PPR already
        distributes probability across outgoing edges.

        Returns:
            (magnitude, delay_label, polarity)
        """
        total_delay = 0
        edge_weights: list[float] = []
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

            # Collect edge weight (no hub penalty)
            edge_weights.append(edge.get("weight", 0.5))

        # Magnitude = bottleneck (weakest link in the chain)
        magnitude = min(edge_weights) if edge_weights else 0.0

        # Map delay sum back to label (cap at LONG_TERM)
        delay_label = DELAY_LABELS.get(min(total_delay, 3), "LONG_TERM")

        return magnitude, delay_label, polarity

    def _compute_cis(self, node: str, probability: float, magnitude: float) -> float:
        """Compute Citizen Impact Score for post-PPR reranking.

        CIS = probability × magnitude × world_boost × leaf_boost
        """
        nd = self.base_G.nodes.get(node, {})
        cat = nd.get('category', '')
        level = nd.get('level', 3)
        is_cat = nd.get('is_category', False)

        # World boost: I-world nodes get boosted
        w_boost = self.i_world_boost if cat.startswith('I') else 1.0

        # Leaf boost (with childless category safeguard)
        if is_cat:
            has_children = any(
                self.base_G[node][s].get('type') == 'CONTAINS'
                for s in self.base_G.successors(node)
            )
            l_boost = self.leaf_boost_l3 if not has_children else self.category_penalty
        elif level == 4:
            l_boost = self.leaf_boost_l4
        elif level == 3:
            l_boost = self.leaf_boost_l3
        else:
            l_boost = self.category_penalty

        return probability * magnitude * w_boost * l_boost

    def _propagate_contains_down(
        self,
        reached_scores: dict[str, dict],
        threshold: float = 0.001,
    ) -> dict[str, dict]:
        """Propagate scores downward through CONTAINS edges.

        If a category node (e.g. agriculture) is reached by PPR,
        its CONTAINS children inherit the score × CONTAINS weight.

        Uses a max-heap so higher-probability parents are processed first,
        ensuring children get the best possible inherited scores.
        Uses the base graph (which has CONTAINS edges), not causal_G.
        """
        import heapq

        # Max-heap: negate probability for max-first ordering
        heap = [(-reached_scores[n]["probability"], n) for n in reached_scores]
        heapq.heapify(heap)
        visited: set[str] = set()

        while heap:
            neg_prob, node = heapq.heappop(heap)
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
                    child_cis = self._compute_cis(succ, child_prob, child_mag)
                    reached_scores[succ] = {
                        "node": succ,
                        "probability": child_prob,
                        "magnitude": child_mag,
                        "score": child_score,
                        "cis": child_cis,
                        "polarity": parent_result["polarity"],
                        "delay": parent_result["delay"],
                        "path": parent_result["path"] + [succ],
                        "via_contains": True,
                    }
                    heapq.heappush(heap, (-child_prob, succ))

        return reached_scores

    def _run_causal_shock(
        self, trigger_node: str, hop_friction: float = 0.85,
        score_threshold: float = 0.001, max_depth: int = 8,
    ) -> dict[str, dict]:
        """Max-Product causal shock propagation from trigger.

        No fan-out penalty — trigger propagates full score × edge_weight × hop_friction
        to ALL neighbors simultaneously. Each node keeps only the strongest path.

        Returns dict of {node: {score, path, polarity, delay}}.
        """
        import heapq

        # Seed expansion: trigger + ancestors with decay
        seeds = self._build_seed_vector(trigger_node, decay=0.5, max_levels=3)
        seed_nodes = set(seeds.keys())

        # Impact scores and predecessor tracking
        scores: dict[str, float] = {}
        paths: dict[str, list[str]] = {}

        # Initialize seeds
        for seed, weight in seeds.items():
            if seed in self.causal_G:
                scores[seed] = weight
                paths[seed] = [seed]

        # Max-heap (negate for min-heap)
        pq: list[tuple[float, str]] = [(-s, n) for n, s in scores.items()]
        heapq.heapify(pq)

        while pq:
            neg_score, u = heapq.heappop(pq)
            current_score = -neg_score

            # Stale entry
            if current_score < scores.get(u, 0.0):
                continue

            # Depth limit
            if len(paths.get(u, [])) - 1 >= max_depth:
                continue

            for v in self.causal_G.successors(u):
                edge_weight = self.causal_G[u][v].get("weight", 0.5)
                new_score = current_score * edge_weight * hop_friction

                if new_score < score_threshold:
                    continue

                if new_score > scores.get(v, 0.0):
                    scores[v] = new_score
                    paths[v] = paths[u] + [v]
                    heapq.heappush(pq, (-new_score, v))

        # Build result dicts with path metrics
        reached: dict[str, dict] = {}
        for node, score in scores.items():
            if node in seed_nodes:
                continue

            path = paths.get(node, [])
            _, delay, polarity = self._compute_path_metrics(path)

            # Magnitude = bottleneck (min edge weight) along path
            edge_weights = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                if self.causal_G.has_edge(u, v):
                    edge_weights.append(self.causal_G[u][v].get("weight", 0.5))
            magnitude = min(edge_weights) if edge_weights else 0.0

            reached[node] = {
                "node": node,
                "probability": score,  # CSP score (compatible with existing interface)
                "magnitude": magnitude,
                "score": score,
                "polarity": polarity,
                "delay": delay,
                "path": path,
            }

        return reached

    def evaluate_impact(
        self,
        trigger_node: str,
        event_direction: int = 1,
        restart_prob: float = 0.20,
        prob_threshold: float = 0.005,
        max_depth: int = 6,
        include_aggregation: bool = False,
        method: str = "csp",
        hop_friction: float = 0.85,
    ) -> list[dict] | tuple[list[dict], dict[str, dict]]:
        """Evaluate impact of a trigger on the causal graph.

        Two methods available:
        - "csp" (default): Causal Shock Propagation via Max-Product Dijkstra.
          No fan-out penalty, edge weights determine signal strength.
        - "ppr": Legacy Personalized PageRank.

        Args:
            trigger_node: Node ID where the shock originates
            event_direction: +1 (increase) or -1 (decrease)
            restart_prob: PPR restart probability (α) [ppr method only]
            prob_threshold: Min score to include a node
            max_depth: Max path length
            include_aggregation: If True, return (results, aggregation) tuple
            method: "csp" or "ppr"
            hop_friction: Per-hop decay for CSP (0.85 = 15% loss per hop)

        Returns:
            List of dicts with keys: node, probability, magnitude, score, polarity, delay, path
        """
        if method == "csp":
            reached_scores = self._run_causal_shock(
                trigger_node, hop_friction=hop_friction,
                score_threshold=prob_threshold, max_depth=max_depth,
            )
        else:
            # Legacy PPR method
            seed_vector = self._build_seed_vector(trigger_node, decay=0.5, max_levels=3)
            seed_nodes = set(seed_vector.keys())

            ppr_scores = self._compute_ppr(seed_vector, restart_prob)
            if not ppr_scores:
                if include_aggregation:
                    return [], {}
                return []

            reached_scores: dict[str, dict] = {}
            for node, prob in ppr_scores.items():
                if node in seed_nodes or prob < prob_threshold:
                    continue
                best_path = None
                best_mag = -1.0
                best_delay = "LONG_TERM"
                best_polarity = 0
                for seed_node in seed_vector:
                    candidate = self._get_dominant_path(seed_node, node)
                    if candidate is None or len(candidate) - 1 > max_depth:
                        continue
                    mag, dly, pol = self._compute_path_metrics(candidate)
                    if mag > best_mag:
                        best_path, best_mag, best_delay, best_polarity = candidate, mag, dly, pol
                if best_path is None:
                    continue
                final_polarity = best_polarity * event_direction
                cis = self._compute_cis(node, prob, best_mag)
                reached_scores[node] = {
                    "node": node, "probability": prob, "magnitude": best_mag,
                    "score": prob * best_mag, "cis": cis,
                    "polarity": final_polarity, "delay": best_delay, "path": best_path,
                }

        # Apply event direction to polarity
        for r in reached_scores.values():
            if "polarity" in r:
                r["polarity"] = r["polarity"] * event_direction if method == "csp" else r["polarity"]

        # CONTAINS propagation (downward)
        reached_scores = self._propagate_contains_down(
            reached_scores, threshold=prob_threshold
        )

        # CIS scoring for ranking
        for r in reached_scores.values():
            r["cis"] = self._compute_cis(r["node"], r["probability"], r["magnitude"])

        # Sort by CIS descending
        results = list(reached_scores.values())
        results.sort(key=lambda x: x["cis"], reverse=True)

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

    from config import settings
    engine = CausalMarkovEngine(
        G,
        i_world_boost=settings.i_world_boost,
        category_penalty=settings.category_penalty,
        leaf_boost_l4=settings.leaf_boost_l4,
        leaf_boost_l3=settings.leaf_boost_l3,
    )

    direction = 1 if args.direction == "up" else -1

    seed_vector = engine._build_seed_vector(args.node)
    if len(seed_vector) > 1:
        seed_str = ", ".join(f"{k}:{v:.2f}" for k, v in sorted(seed_vector.items(), key=lambda x: -x[1]))
        print(f"Seed vector: {seed_str}")

    results = engine.evaluate_impact(
        args.node,
        event_direction=direction,
        restart_prob=args.restart,
        prob_threshold=args.threshold,
        max_depth=args.max_depth,
    )

    print(f"\nPPR Impact Analysis for '{args.node}' (α={args.restart}, direction={'↑' if direction == 1 else '↓'}):")
    print(f"{'Node':<35} {'Prob':>8} {'Mag':>8} {'CIS':>8} {'Pol':>4} {'Delay':<12} Path")
    print("-" * 110)

    for imp in results[:args.top]:
        pol_sym = {1: "+", -1: "−", 0: "?"}[imp["polarity"]]
        path_str = " → ".join(imp["path"][-3:])
        print(
            f"{imp['node']:<35} {imp['probability']:>8.5f} {imp['magnitude']:>8.5f} "
            f"{imp['cis']:>8.6f} {pol_sym:>4} {imp['delay']:<12} {path_str}"
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
