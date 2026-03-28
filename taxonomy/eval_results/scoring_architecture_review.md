Based on your detailed breakdown, you have correctly diagnosed the fundamental mathematical mismatch in your current architecture. **PPR is a "conservation of mass" model (a random walker can only be in one place at a time), but causal shocks are a "duplication of information" model (a shock propagates to all downstream nodes simultaneously).** 

Here is the expert advice on how to fix your scoring engine, directly addressing your questions.

---

### 1. The Verdict: Which Model is Best?
**Option C (Weighted Influence Propagation / Max-Product Path)** is theoretically and practically the best model for your use case. 

Specifically, you should implement a **Max-Product Dijkstra** algorithm. 
*   **Why not PPR?** PPR inherently penalizes hubs (fan-out penalty). In a causal graph, a node with high out-degree is a *systemic driver* (e.g., "Inflation"), not a router. It should pass its full force to all children.
*   **Why not Independent Cascade?** Monte Carlo simulations are stochastic, harder to debug, and computationally heavy for real-time APIs.
*   **Why Max-Product?** It finds the single strongest causal chain to every node. It completely eliminates the fan-out penalty, handles cycles gracefully, and provides 100% explainability (you can trace the exact path that resulted in the score).

### 2. The Recommended Algorithm: Causal Shock Propagation (CSP)

Here is the exact approach, using a modified Dijkstra algorithm to find the maximum impact path.

*   **Fan-out handling:** Node $u$ passes its score to *all* neighbors $v$, multiplied only by the edge weight. No division by out-degree.
*   **Hop decay:** We introduce a tunable `hop_friction` parameter (e.g., 0.85). This replaces PPR's restart probability.
*   **Ranking:** We explicitly separate T-world and I-world nodes at the ranking layer.

#### The Python / NetworkX Pseudocode

```python
import heapq
import networkx as nx

def calculate_causal_impact(G, trigger_node, hop_friction=0.85):
    """
    G: Directed NetworkX graph with 'weight' (0-1) on edges
    trigger_node: The T-world node triggered by the news
    hop_friction: Decay per hop (0.85 means 15% signal loss per hop)
    """
    # Dictionary to store the max impact score for each node
    impact_scores = {node: 0.0 for node in G.nodes()}
    impact_scores[trigger_node] = 1.0
    
    # Dictionary to store the best path for explainability
    predecessors = {trigger_node: None}
    
    # Priority queue: stores (-score, node) because Python has a min-heap
    pq = [(-1.0, trigger_node)]
    
    while pq:
        current_neg_score, u = heapq.heappop(pq)
        current_score = -current_neg_score
        
        # If we pulled a stale, lower score from the heap, ignore it
        if current_score < impact_scores[u]:
            continue
            
        # Propagate to all neighbors (NO FAN-OUT PENALTY)
        for v in G.successors(u):
            edge_weight = G[u][v].get('weight', 1.0)
            
            # Calculate new impact: u's score * edge weight * hop friction
            new_impact = current_score * edge_weight * hop_friction
            
            # If we found a stronger causal path to v, update it
            if new_impact > impact_scores[v]:
                impact_scores[v] = new_impact
                predecessors[v] = u
                heapq.heappush(pq, (-new_impact, v))
                
    return impact_scores, predecessors

def rank_citizen_impacts(G, impact_scores):
    """Filters and ranks only the I-world (citizen impact) nodes"""
    i_world_results = []
    
    for node, score in impact_scores.items():
        # Assuming nodes have a 'world' attribute
        if G.nodes[node].get('world') == 'I-world' and score > 0:
            i_world_results.append({
                'node': node,
                'score': score,
                'category': G.nodes[node].get('category')
            })
            
    # Sort descending by score
    return sorted(i_world_results, key=lambda x: x['score'], reverse=True)
```

#### Expected Computational Complexity
**$O(E \log V)$**. For 769 nodes and 1541 edges, Python's `heapq` will execute this in **< 5 milliseconds**. It is vastly faster than PPR and easily fits your 100ms constraint.

### 3. Would a simpler model outperform PPR?
**Yes, absolutely.** The algorithm above is simpler than PPR, deterministic, and directly models the physics of your problem. 

Your current issue where "1-hop infrastructure targets dominate 2-3 hop citizen impacts" is happening because PPR mixes T-world and I-world nodes in the same probability distribution. By using Max-Product and explicitly filtering for I-world nodes at the end, you guarantee that the final ranked list only contains citizen impacts, ranked by the strength of the causal chain that reached them.

### 4. Can PPR be fixed for causal propagation?
**No, not without breaking the math that makes PPR work.** 
To fix the fan-out penalty in PPR, you would have to stop row-normalizing the transition matrix (i.e., out-edges don't sum to 1). If you do that, it is no longer a Markov transition matrix, and standard PageRank solvers (like power iteration or algebraic solvers in NetworkX) will either fail to converge or explode to infinity if there are cycles. 

### 5. The Simplest Change to Move NDCG the Most
If you want to fix your 10 failing canaries by tomorrow, do these two things:

1.  **Rip out PPR and drop in the Max-Product Dijkstra algorithm above.** Set `hop_friction = 0.85`.
2.  **Implement strict World-Filtering.** Do not rank T-world nodes against I-world nodes. If the user wants to know "how this affects citizens," the final array returned to the UI/evaluator should *only* contain I-world nodes. T-world nodes are just the highways to get there.

**Bonus tweak for later:** If you find that an I-world node is hit by *multiple* strong paths (e.g., Inflation hits "Food Prices" via Transport AND via Fertilizer), and you want to reward that, you can change the score update logic from `Max` to a **Noisy-OR** formulation: 
`impact_scores[v] = 1.0 - (1.0 - impact_scores[v]) * (1.0 - new_impact)`. 
However, stick to Max-Product first—it is easier to debug and provides perfect 1-to-1 path explainability.