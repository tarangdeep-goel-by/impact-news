# PPR/Markov Scoring Engine — Implementation Plan

**Status:** DRAFT — Pending review
**Date:** 2026-03-15
**Replaces:** Modified Dijkstra traversal (`graph/traverse.py`)
**Motivation:** Current Dijkstra floods 90% of the graph because weights cluster 0.6–0.9. A single crude oil trigger reaches nearly every node. The weight calibration plan (stretch, hop penalty, Gemini recalibration) is a 7-step band-aid. PPR solves this structurally.

---

## 1. Architecture Overview

### Current Pipeline
```
News → Gemini tags → FAISS match → Dijkstra (max-product) → user relevance (dot product)
```
Dijkstra returns ONE number per node: `score` (which conflates probability, magnitude, and relevance).

### New Pipeline
```
News → Gemini tags → FAISS match → PPR (probability) + Path (magnitude/timing) → user relevance
```
PPR separates three concerns that Dijkstra conflated:

| Output | Question | Method | What it means |
|--------|----------|--------|---------------|
| **Probability** | Will this reach me? | Personalized PageRank | Steady-state visit frequency from trigger |
| **Magnitude** | How hard? | Hub-penalized path multiplier | Causal strength along dominant path |
| **Timing** | When? | Delay sum along dominant path | Slowest path determines arrival |
| **Polarity** | Which direction? | Product along path | +1 or -1 |

### Why PPR over Absorbing Markov Chains

Gemini 3.1 Pro identified a critical flaw in absorbing chains: personal nodes become "black holes." If `it_sector_salary` is absorbing, a salary shock never cascades to `home_loan_emi`. PPR lets shocks flow *through* personal nodes — no artificial stopping.

PPR also handles cycles natively (feedback loops like I→T edges), whereas absorbing chains require all cycles to exclude absorbing states.

---

## 2. The Math

### 2.1 Transition Matrix P (row-normalized)

For each node `u` with outgoing causal edges:
```
P[u][v] = raw_weight(u→v) / Σ raw_weight(u→k) for all causal successors k
```

Only causal edge types enter the matrix:
`AFFECTS, PRODUCES, REGULATES, DISRUPTS, SUPPLIES, DEPENDS_ON, FUNDS, COMPETES_WITH, EMPLOYS, MANAGES`

CONTAINS and IS_A are excluded. They are structural (inheritance), not causal.

**Example:**
- `crude_oil` has edges to `petrol_price` (0.9), `plastics_mfg` (0.7), `aviation_fuel` (0.8), `fertilizer_cost` (0.6)
- Sum = 3.0
- P[crude_oil][petrol_price] = 0.9/3.0 = 0.30
- P[crude_oil][plastics_mfg] = 0.7/3.0 = 0.23

### 2.2 Personalized PageRank

```
π = α·x + (1-α)·Pᵀ·π
```

Where:
- `x` = restart vector (1.0 at trigger node, 0.0 elsewhere)
- `α` = restart probability (0.15–0.25, tunable)
- `π` = steady-state probability distribution

Higher α → shock stays closer to trigger (more conservative).
Lower α → shock spreads further (more sensitive).

**NetworkX implementation:** `nx.pagerank(G, alpha=1-restart_prob, personalization={trigger: 1.0}, weight='weight')` — handles normalization internally.

### 2.3 Hub-Penalized Magnitude

For the dominant path from trigger to target:
```
magnitude = Π (raw_weight[i] × hub_penalty[i]) for each edge i in path

hub_penalty(node) = 1.0 / log₂(causal_out_degree(node) + 1)
```

**Why this works:**
- Node with 2 causal out-edges: penalty = 1/log₂(3) = 0.63
- Node with 10 causal out-edges: penalty = 1/log₂(11) = 0.29
- Node with 25 causal out-edges: penalty = 1/log₂(26) = 0.21

A 3-hop path through specific nodes: 0.8×0.63 × 0.8×0.63 × 0.8×0.63 = **0.128**
A 3-hop path through hubs: 0.8×0.21 × 0.8×0.29 × 0.8×0.63 = **0.006**

This naturally stretches the 0.6–0.9 cluster into a meaningful range.

### 2.4 Timing

Map delays to integers: `IMMEDIATE=0, SHORT_TERM=1, MEDIUM_TERM=2, LONG_TERM=3`
Sum along dominant path. Map back:

| Sum | Term |
|-----|------|
| 0 | IMMEDIATE |
| 1 | SHORT_TERM |
| 2 | MEDIUM_TERM |
| 3+ | LONG_TERM |

### 2.5 Polarity Propagation

Product of edge polarities along path. Same as current system:
- (+1) × (+1) = +1 (both increase)
- (+1) × (-1) = -1 (inverse)
- Any × 0 = 0 (unknown)

---

## 3. Graph Preprocessing Decisions

### 3.1 CONTAINS Edges — Excluded from PPR Matrix

**Problem:** If CONTAINS enters the transition matrix, a shock to `agriculture` splits 50/50 between `staple_grains` and `cash_crops`. That's wrong — a drought hits *both* at full force. CONTAINS is inheritance, not causation.

**Solution:** Build a causal-only subgraph for PPR. CONTAINS edges handle hierarchy OUTSIDE the Markov walk.

### 3.2 Hierarchy Handling — The Elevator Pattern (kept)

The current elevator pattern (walk UP from leaf to find causal entry point) is still needed because:
- Many trigger nodes are leaves with only CONTAINS parent edges
- FAISS may match a leaf node that has no causal outgoing edges
- The elevator finds the nearest ancestor with causal edges

**Change:** The elevator runs BEFORE passing the node to PPR, same as now.

### 3.3 Downward CONTAINS Propagation (kept, but post-PPR)

Current system propagates CONTAINS edges downward AFTER Dijkstra. This is still needed:
- PPR tells us `agriculture` is hit with probability 0.05
- CONTAINS propagation tells us `staple_grains`, `cash_crops`, etc. inherit that hit
- This runs as a post-processing step, same as now

The propagation multiplies by CONTAINS edge weight (default 0.9):
- `agriculture` prob=0.05 → `staple_grains` prob=0.05×0.9=0.045

### 3.4 Dangling Nodes (no outgoing causal edges)

738 nodes, 45 have zero outgoing edges, 191 have only CONTAINS/IS_A outgoing.

In a Markov chain, dangling nodes need handling (they'd create a sink).
**For PPR:** NetworkX handles dangling nodes by redistributing their probability uniformly (default `dangling` parameter). We can override this to redistribute to the restart vector instead: `dangling={trigger: 1.0}`.

### 3.5 Bidirectional Edges

Edges A→B (0.8) and B→A (0.6) are independent entries in the transition matrix. No special handling needed. PPR converges regardless of cycles.

---

## 4. What Changes When the Graph Is Modified

This is critical. The graph is actively maintained — edges are added, removed, reweighted. Understanding the ripple effects of graph mutations under PPR is essential.

### 4.1 Adding an Edge

**Under Dijkstra (current):** New edge creates a new path. Score is independent of other edges.

**Under PPR:** Adding an edge from node X dilutes ALL existing edges from X.

Example: Node A has edges to B(0.8) and C(0.4). B gets 67%, C gets 33%.
Add edge to D(0.6) → B gets 44%, C gets 22%, D gets 33%.

**Implication:** Adding edges to high-importance nodes (like `rbi_repo_rate`) weakens existing connections. This is actually *correct behavior* — if the RBI affects more things, each individual thing is less dominant. But it means:
- **Always re-run scenario tests after adding edges to hub nodes**
- **Edge additions are not isolated changes — they affect all siblings**

### 4.2 Removing an Edge

Removing an edge from X concentrates probability on remaining edges. If A→B is removed, A→C gets 100%. This can create artificially strong paths.

**Implication:** Removing edges can cause score spikes on unrelated paths. Watch for this in scenario tests.

### 4.3 Changing a Weight

Under PPR, changing a weight changes the *ratio* within that node's outgoing distribution. The absolute value matters less than the relative value.

**Key insight:** Changing `crude_oil → petrol_price` from 0.8 to 0.9 doesn't change much if other edges also have similar weights. It only matters relative to siblings:
- If other edges are 0.8: petrol gets 0.9/3.5 = 0.26 (was 0.8/3.4 = 0.24) — tiny change
- If other edges are 0.3: petrol gets 0.9/1.5 = 0.60 (was 0.8/1.4 = 0.57) — still small

**This is why weight recalibration is unnecessary for PPR.** The normalization absorbs absolute weight differences. You only need to change weights when you want to change the *ratio* of influence.

### 4.4 Adding a Node

Adding a new node (e.g., adding `electric_vehicle_charging` under `transport`) requires:
1. CONTAINS edge from parent (structural)
2. Causal edges to/from other nodes (if any)

If the new node has causal edges, it enters the PPR matrix and dilutes its neighbors' transition probabilities (see 4.1). If it only has CONTAINS edges, it's invisible to PPR and only appears via downward propagation.

### 4.5 Merging Nodes

`TaxonomyMerger` supports `node_merges` (redirect edges from old→new, remove old). Under PPR:
- The new node inherits all edges, so its fan-out increases
- This dilutes per-edge probability
- Generally correct: merged nodes are broader concepts

### 4.6 Patch Application Order

Current patch system: `edge_patches.yaml` + `edge_patches_generated.yaml` applied after flat file merge. Under PPR, patch order doesn't matter for probability computation (matrix is built once from final graph state). But it matters for:
- Node ID validation (a patch referencing a not-yet-loaded node fails)
- Weight overrides (last write wins, same as now)

### 4.7 Re-computation After Changes

**What must be recomputed:**
- The causal subgraph (strip CONTAINS/IS_A) — cheap, ~10ms
- PPR for each active trigger — `nx.pagerank` on 738 nodes takes ~5ms per trigger
- Pre-computed path costs (`-log(P)` for Dijkstra pathfinding) — ~20ms

**What does NOT need recomputation:**
- FAISS embeddings (unless node aliases change)
- User profiles
- Article tag extractions

**Recommendation:** Build the causal subgraph + path costs at startup. Recompute on graph reload. PPR runs per-query (it's fast enough at 5ms).

---

## 5. Weight Semantics Under PPR

### 5.1 Current Weight Meaning

Weights currently mean "causal strength" — how much of an effect transmits through this edge. Range 0.0–1.0. Assigned by edge type defaults in `migrate_weights.py`:

| Edge Type | Default Weight | Meaning |
|-----------|---------------|---------|
| PRODUCES | 0.9 | Direct output relationship |
| REGULATES | 0.8 | Policy/regulatory control |
| DISRUPTS | 0.8 | Disruption/interference |
| SUPPLIES | 0.7 | Supply chain dependency |
| DEPENDS_ON | 0.7 | Operational dependency |
| AFFECTS | 0.4 | General causal influence |

Plus fan-out penalty: nodes with >15 AFFECTS edges capped at 0.4.

### 5.2 Weight Meaning Under PPR

Weights become **relative influence shares** after normalization. The absolute value matters only relative to sibling edges from the same source node.

This means:
- `PRODUCES` (0.9) vs `AFFECTS` (0.4) from the same node: PRODUCES gets 69%, AFFECTS gets 31% ✓
- `PRODUCES` (0.9) vs `PRODUCES` (0.9) from the same node: equal share (50%/50%) ✓
- All weights 0.8 from the same node: equal share (which is what we have now, and it's actually correct for undifferentiated links)

### 5.3 When to Change Weights (Post-PPR)

Recalibrate weights ONLY when you want to change the **ratio** of influence from a node:
- "Actually, 80% of crude oil's impact goes to petrol, not 30%"
- "Agriculture's effect on staple_grains is 3x stronger than on cash_crops"

You do NOT need to recalibrate for:
- Overall score inflation (PPR normalizes it away)
- "Everything is 0.8" problem (normalization fixes it)
- Hub dominance (normalization + hub penalty fixes it)

### 5.4 Fan-Out Penalty in `migrate_weights.py`

The current fan-out penalty (>15 AFFECTS edges → cap at 0.4) becomes **redundant** under PPR. Row normalization already dilutes high fan-out nodes. The hub penalty in magnitude computation handles it for the path score.

**Recommendation:** Remove the fan-out penalty from `migrate_weights.py` after migration. Keep the edge-type defaults (they encode domain knowledge about relative strength).

### 5.5 MACRO_HUBS Exemption

Currently `migrate_weights.py` exempts 11 macro hubs from the fan-out penalty. Under PPR, this distinction is unnecessary — all nodes are treated equally by row normalization.

**Recommendation:** Remove the MACRO_HUBS list after migration.

---

## 6. Detailed Implementation

### 6.1 New File: `graph/markov_engine.py`

```
class CausalMarkovEngine:
    __init__(base_graph: nx.DiGraph)
    _build_causal_graph() → nx.DiGraph           # Strip CONTAINS/IS_A
    _precompute_path_costs()                       # -log(P) for Dijkstra

    evaluate_impact(                               # Main entry point
        trigger_node: str,
        user_nodes: list[str] | None = None,       # For user-specific scoring
        restart_prob: float = 0.20,
        prob_threshold: float = 0.005,
        max_depth: int = 6
    ) → list[dict]

    _compute_ppr(trigger: str, α: float) → dict[str, float]
    _get_dominant_path(trigger: str, target: str) → list[str] | None
    _compute_path_metrics(path: list[str]) → (magnitude, term, polarity)
    _propagate_contains_down(reached: dict, threshold: float) → dict
    _aggregate_upward(reached: dict) → dict        # Keep existing logic
```

**Output format per node (superset of current):**
```python
{
    "node": str,
    "probability": float,       # PPR steady-state score (NEW)
    "magnitude": float,         # Hub-penalized path product (NEW)
    "score": float,             # Combined = probability × magnitude (REPLACES old score)
    "polarity": int,            # ±1 or 0
    "delay": str,               # IMMEDIATE / SHORT_TERM / MEDIUM_TERM / LONG_TERM
    "path": list[str],          # Dominant path
}
```

### 6.2 Changes to `graph/traverse.py`

**Keep** the existing `analyze_impact()` function, renamed to `analyze_impact_dijkstra()`.
**Keep** `get_causal_entry()`, `_get_contains_ancestors()`, `_aggregate_upward()`, `_has_causal_outedges()`, `_get_contains_parent()` — these are reused by the new engine.
**Add** a new `analyze_impact()` that delegates to `CausalMarkovEngine`.

### 6.3 Changes to `pipeline/matcher.py`

In `match_tags_to_graph()`:
- Currently calls `analyze_impact()` per matched tag → gets `impacts` list
- Finds best hit among user's direct edges by `impact["score"]`
- Combined score = `tag_match_score × graph_score × user_importance`

**Change:** Replace `analyze_impact()` call with `engine.evaluate_impact()`. The new output has `probability` and `magnitude` as separate fields. Scoring becomes:

```python
# Old: combined = tag_match × graph_score × user_importance
# New: combined = tag_match × probability × magnitude_weight × user_importance
#   where magnitude_weight = lerp(1.0, magnitude, 0.5) — magnitude modulates, doesn't dominate
```

In `compute_relevance()`:
- Currently: `article_score × user_importance` for direct edges, `article_score × 0.3` for reachable
- **Change:** Use `probability` as the article_score. The 0.3 multiplier for reachable nodes may need adjustment (reachable nodes now have real probability scores, not Dijkstra scores).

### 6.4 Changes to `graph/scenarios.py`

Scenario types B and C call `analyze_impact()`. These continue to work because `analyze_impact()` delegates to the new engine. But:
- Type B checks if `node in hit_nodes` → still works (PPR produces all reachable nodes)
- Type C checks `score >= min_score` → **thresholds may need adjustment** because PPR scores are probability distributions (sum to ~1.0), not max-product scores

**Recommendation:** Run scenarios with BOTH engines in parallel during migration. Log score comparisons. Adjust thresholds empirically.

### 6.5 Changes to `graph/migrate_weights.py`

- **Keep** `apply_defaults()` — edge-type defaults encode domain knowledge
- **Remove** `apply_fan_out_penalty()` — redundant under PPR
- **Remove** `MACRO_HUBS` exemption list — unnecessary

### 6.6 Changes to `graph/graph.py`

None. Graph loading stays the same.

### 6.7 Changes to `config.py`

Add new settings:
```python
# PPR
ppr_restart_prob: float = 0.20          # α — restart probability
ppr_prob_threshold: float = 0.005       # Min probability to consider
ppr_magnitude_blend: float = 0.5        # How much magnitude affects final score
```

---

## 7. The Restart Probability (α) — Tuning Guide

This is the most important tunable parameter. It controls how far the shock spreads.

| α value | Behavior | Use case |
|---------|----------|----------|
| 0.10 | Shock spreads far | Catch distant, indirect impacts |
| 0.15 | Default PageRank | Good starting point |
| 0.20 | Moderate spread | Recommended for impact news |
| 0.30 | Conservative | Only direct/near impacts |
| 0.50 | Very conservative | Essentially 1-2 hops only |

**How to tune:**
1. Pick 5 reference triggers: `crude_oil`, `rbi_repo_rate`, `monsoon`, `it_sector_jobs`, `usd_inr_exchange`
2. For each, count how many personal nodes are "hit" (prob > threshold) at different α values
3. Target: 3-8 personal nodes hit for a major trigger (not 0, not 20)

**The α value can be per-user or per-trigger in future versions** (more sensitive users get lower α, more specific triggers get higher α). But start with a single global value.

---

## 8. Scenario Test Adaptation

### 8.1 Type A (path_exists) — No Change

These check structural reachability (BFS on causal subgraph). Independent of scoring engine.

### 8.2 Type B (reachability) — Threshold Adjustment

Currently: `analyze_impact()` with threshold=0.05 (Dijkstra score).
Under PPR: probability scores are MUCH smaller (they're a distribution summing to ~1.0 over 738 nodes). A node with Dijkstra score 0.10 might have PPR probability 0.002.

**Approach:** Run both engines on all Type B scenarios. Compute the mapping:
```
ppr_threshold ≈ dijkstra_threshold × (1 / num_causal_nodes) × adjustment_factor
```

Empirically: start with `ppr_threshold = 0.001` for Type B scenarios.

### 8.3 Type C (score_threshold) — Score Recalibration

Same issue. Dijkstra `min_score=0.20` maps to a much smaller PPR probability.

**Approach:** For each Type C scenario, record both Dijkstra score and PPR probability. Define new thresholds based on PPR probability rankings (top-10 percentile = HIGH, top-30 = MEDIUM, etc.)

### 8.4 New Scenarios to Add

PPR enables new scenario types:
- **Type D (ranking):** Given trigger X, verify that node A ranks higher than node B in probability. This tests relative ordering, not absolute thresholds.
- **Type E (isolation):** Given trigger X, verify that node Y has probability < noise_threshold. This is the negative test (gold should NOT affect wheat).

### 8.5 Dual-Engine Validation Period

Run BOTH engines for 2 weeks. For every article processed:
```python
dijkstra_results = analyze_impact_dijkstra(G, trigger)
ppr_results = engine.evaluate_impact(trigger)
log_comparison(trigger, dijkstra_results, ppr_results)
```

Compare:
- Do both engines agree on the TOP-3 impacted nodes? (They should)
- Does PPR produce fewer false positives? (It should)
- Are the PPR magnitude scores more differentiated than Dijkstra? (They should be)

---

## 9. Edge Cases and Risks

### 9.1 Small Connected Components

If a trigger node is in a small weakly-connected component, PPR concentrates all probability there. This could create artificially high scores for nodes that are only reachable because they're in the same island.

**Mitigation:** Check component size. If < 20 nodes, flag results as low-confidence.

### 9.2 Self-Loops

If a node has an edge to itself (possible via patches), PPR handles it correctly (probability leaks to self). But magnitude computation on the dominant path must not include self-loops.

**Mitigation:** Skip self-loops in `_build_causal_graph()`.

### 9.3 Zero-Weight Edges

If an edge has weight 0.0, it contributes nothing to the transition matrix. This effectively removes it.

**Mitigation:** Validate that all causal edges have weight > 0.0 during graph loading.

### 9.4 The "Sum to 1.0" Property

PPR probabilities sum to ~1.0 across ALL nodes. This means:
- Adding more nodes to the graph dilutes every individual probability
- Comparing PPR scores across different graph versions is invalid

**Mitigation:** Use RANKINGS (ordinal position) for cross-version comparisons, not raw probabilities. For thresholds, use percentile-based cutoffs.

### 9.5 Bridge Edges Under PPR

Bridge edges (T→I, I→T) are causal edges that enter the transition matrix. They compete with lateral edges for probability share. A trigger node with many lateral edges and few bridges → bridges get diluted.

**Risk:** If `crude_oil` has 15 lateral edges in T-world and only 2 bridges to I-world, the bridges get ~2/17 ≈ 12% of the probability. Is this correct?

**Analysis:** Yes. Most of crude oil's causal chains stay within the T-world (crude→petrol→transport→logistics). Bridges should be rare, high-weight transitions that capture the T→I jump. If bridges are weak, it correctly means the macro event doesn't directly affect citizens much — the effect takes many hops.

**However:** If scenario tests fail because bridges are too diluted, consider:
1. Increasing bridge edge weights relative to lateral edges
2. OR: Give bridge edges a type-based normalization bonus

### 9.6 The Elevator + PPR Interaction

Current elevator walks UP from leaf to find causal entry. Under PPR, the elevated node becomes the trigger for the PPR walk. But the original leaf is lost.

**Example:** FAISS matches "tomato prices" to `retail_tomato` (leaf). Elevator walks up to `fresh_produce` (has causal edges). PPR runs from `fresh_produce`.

**Issue:** The PPR result is for `fresh_produce`, not `retail_tomato`. All of fresh_produce's children (tomato, onion, potato) get the same probability via CONTAINS propagation. We lose specificity.

**Possible fix (future):** Run PPR from `fresh_produce`, then discount CONTAINS children that aren't the original match. But this adds complexity. For v1, accept the loss of specificity — it's the same behavior as current Dijkstra.

---

## 10. Implementation Phases

### Phase 1: MVP Engine (1 session)

1. Create `graph/markov_engine.py` with `CausalMarkovEngine` class
2. Implement `_build_causal_graph()`, `_compute_ppr()`, `_get_dominant_path()`, `_compute_path_metrics()`
3. Implement `_propagate_contains_down()` (port from traverse.py)
4. Write a CLI test: `python -m graph.markov_engine crude_oil` — prints probability/magnitude/timing for all reachable nodes
5. Run existing scenarios through new engine, log score comparisons

### Phase 2: Integration (1 session)

1. Add `ppr_*` settings to `config.py`
2. Wire `markov_engine` into `matcher.py` (replace `analyze_impact` calls)
3. Update `compute_relevance()` scoring formula
4. Add dual-engine logging in `process_articles()` for A/B comparison
5. Adapt scenario thresholds for PPR scores

### Phase 3: Cleanup (1 session)

1. Remove `apply_fan_out_penalty()` and `MACRO_HUBS` from `migrate_weights.py`
2. Add Type D (ranking) and Type E (isolation) scenarios
3. Remove dual-engine logging, make PPR the sole engine
4. Update `traverse.py` CLI to use PPR by default with `--legacy` flag for Dijkstra
5. Update CLAUDE.md with new architecture notes

### Phase 4: Tuning (ongoing)

1. Tune α (restart probability) based on real article processing
2. Adjust `ppr_prob_threshold` and `ppr_magnitude_blend` based on Telegram delivery quality
3. Consider per-trigger-type α values (financial triggers → higher α, weather → lower α)
4. Consider weight ratio recalibration for key bridges (only if scenario tests indicate)

---

## 11. Success Criteria

| Metric | Current (Dijkstra) | Target (PPR) |
|--------|-------------------|--------------|
| Nodes reached per trigger | ~90% of graph | 10-30% |
| Score differentiation | Mean 0.8, stdev 0.11 | Mean varies, stdev > 0.3 |
| False positives (gold→wheat) | May pass threshold | Below noise threshold |
| Scenario tests | 52/52 passing | 52/52 passing (adjusted thresholds) |
| Computation time per trigger | ~50ms (Dijkstra) | ~5ms (PPR) + ~5ms (paths) |
| Weight recalibration needed | Yes (7-step plan) | No |

---

## 12. What This Does NOT Solve

1. **AND gates (joint causality):** PPR assumes shocks route independently. If grocery_bill only spikes when BOTH monsoon AND diesel trigger simultaneously, this model can't capture that. Would need Bayesian networks.

2. **Statefulness:** The 5th RBI rate hike is treated identically to the 1st. No memory of accumulated stress on home_loan_emi. Would need stock-and-flow models.

3. **Exact price forecasting:** Output is "probability 0.12, magnitude 0.08" — not "your EMI goes up ₹1,450." Would need Leontief input-output models.

4. **Time-varying edge weights:** Edge weights are static. A crude oil shock during a war has different dynamics than during peacetime. Would need dynamic graph models.

None of these are blockers for an impact news system. The goal is personalized relevance ranking and narrative generation, not economic forecasting.

---

## 13. Open Questions for Review

1. **α value:** Start with 0.20? Or run a sweep first?
2. **Magnitude blend:** How much should magnitude affect the final relevance score? (prob × mag^0.5? prob + 0.3×mag? Pure prob?)
3. **CONTAINS propagation:** Should CONTAINS children inherit full PPR probability or decayed? (Currently decayed by CONTAINS edge weight 0.9)
4. **Bridge weight boost:** If bridges are too diluted by lateral edges, do we boost bridge weights globally or tune per-bridge?
5. **Scenario threshold migration:** Automated (compute ratio between engines) or manual (adjust each scenario)?
