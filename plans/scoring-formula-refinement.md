# Scoring Formula Refinement — Plan

## Problem Statement

PPR probability mass pools on **intermediate nodes** (T-world macro indicators, L2/L3 categories) instead of reaching **citizen-level I-world L4 leaf nodes** — the things that actually affect people.

### Evidence (from event replay, 2026-03-19)

| Trigger | T-world % of top-20 | I-category % | I-leaf L4 % | NDCG@10 |
|---------|--------------------:|-------------:|------------:|--------:|
| brent_crude | 16% | 25% | 59% | 0.37 |
| rbi | 27% | 29% | 44% | 0.18 |
| southwest_monsoon | 40% | 11% | 35% | 0.04 |
| meteorological_systems | 80% | 20% | 0% | 0.00 |
| us_federal_reserve | 61% | 8% | 31% | 0.12 |

### Root Causes

1. **T-world probability soak** — Triggers live in T-world. PPR random walk spends many steps in T-world before crossing a T→I bridge. By the time probability reaches I-world, it's diluted.
   - `meteorological_systems`: 80% of top-20 probability stays in T-world
   - `us_federal_reserve`: 61% stays in T-world (bouncing through treasury yields, dollar index, FII flows)

2. **Category node accumulation** — L2/L3 `is_category=true` nodes (like `savings_and_deposits`, `vehicle_fuel`, `staple_grains`) collect probability from multiple incoming edges, then rank high. They're organizational folders, not citizen impacts.
   - `rbi` top-20: `savings_and_deposits` (L2, is_cat) at #2 with prob=0.049
   - Their L4 children get probability only via CONTAINS propagation (multiplied by 0.9), landing lower

3. **CONTAINS propagation dilution** — When a category node is reached by PPR, its children inherit `prob × 0.9`. But category nodes often have 5-10 children, so the probability spreads thin. The children all get the same probability (no differentiation).

4. **Hub penalty insufficient** — The hub penalty (`1/log2(out_degree+1)`) only applies to *magnitude*, not probability. High-degree T-world nodes like `rbi` (out_degree=8) still accumulate PPR probability normally.

5. **No world-crossing incentive** — PPR treats T→T and T→I edges identically. There's no mechanism to prioritize the causal chain reaching I-world.

## Design Constraints

- **Must not break existing scenarios** — 58/58 must still pass
- **Must be backward-compatible** — `evaluate_impact()` API stays the same
- **Tunable** — New parameters go in `config.py` via Pydantic Settings
- **No LLM in scoring path** — Pure algorithmic, sub-second
- **Score must remain interpretable** — Higher = more impacted

## Solution: Citizen Impact Score (CIS)

Replace the current `score = probability × magnitude` with a 4-factor formula that explicitly rewards citizen-level nodes:

```
CIS = probability × magnitude × world_boost × leaf_boost
```

### Factor 1: `probability` (unchanged)
PPR steady-state distribution. No changes.

### Factor 2: `magnitude` (unchanged)
Hub-penalized path product along dominant path. No changes.

### Factor 3: `world_boost` — Reward I-world nodes
T-world nodes are infrastructure/system entities. I-world nodes are citizen impacts. Boost I-world.

```python
def world_boost(node_id, graph):
    cat = graph.nodes[node_id].get('category', '')
    if cat.startswith('I'):
        return config.i_world_boost  # default: 2.0
    return 1.0  # T-world stays at 1.0
```

**Why 2.0?** Currently I-world L4 leaves have ~0.3-0.6× the probability of T-world intermediates. A 2× boost brings them roughly even, letting magnitude differentiate.

**Config:** `i_world_boost` in `config.py`, default `2.0`.

### Factor 4: `leaf_boost` — Reward specificity (L4 non-category nodes)

Category nodes (L2, L3 with `is_category=true`) are organizational. L4 leaf nodes are the actual citizen touchpoints. Boost based on specificity.

```python
def leaf_boost(node_id, graph):
    nd = graph.nodes[node_id]
    level = nd.get('level', 3)
    is_cat = nd.get('is_category', False)

    if is_cat:
        # Childless category safeguard (Gemini review): if category has no
        # CONTAINS children, treat it as L3 non-category — don't bury the
        # only signal for that impact area.
        has_children = any(
            graph[node_id][s].get('type') == 'CONTAINS'
            for s in graph.successors(node_id)
        )
        if not has_children:
            return config.leaf_boost_l3   # default: 1.2
        return config.category_penalty    # default: 0.3
    if level == 4:
        return config.leaf_boost_l4       # default: 1.5
    if level == 3:
        return config.leaf_boost_l3       # default: 1.2
    return config.category_penalty        # L1, L2 without is_category flag
```

**Why these values?**
- Category nodes with children (L2/L3 `is_category=true`) get 0.3× — strong demotion since they're folders
- Childless category nodes get 1.2× — safeguard against burying the only signal (Gemini review)
- L4 leaves get 1.5× — they're the most specific citizen impacts
- L3 non-category gets 1.2× — slight boost, they're specific enough to be valuable (Gemini review: 1.0 was too close to T-world baseline)
- Combined with world_boost: an I-world L4 leaf gets `2.0 × 1.5 = 3.0×` total boost vs a T-world category node at `1.0 × 0.3 = 0.3×` — a 10× relative swing

**Config:** `category_penalty`, `leaf_boost_l4`, `leaf_boost_l3` in `config.py`.

### Combined Formula

```python
cis = probability * magnitude * world_boost(node) * leaf_boost(node)
```

**Sorting changes to `cis` instead of `probability`.** The `probability` field stays in the result dict for debugging, but ranking uses `cis`.

### Expected Impact (back-of-envelope)

**brent_crude example:**

| Node | Current rank | prob | mag | world | leaf | CIS | New rank |
|------|:-----------:|-----:|----:|------:|-----:|----:|:--------:|
| india_trade_deficit | 1 | 0.069 | 0.32 | 1.0 | 1.5 | 0.034 | ~5 |
| vehicle_fuel (I3, cat) | 3 | 0.051 | 0.03 | 2.0 | 0.3 | 0.001 | ~20 |
| retail_petrol (I3, L4) | 4 | 0.051 | 0.03 | 2.0 | 1.5 | 0.005 | ~10 |
| household_energy (I2, cat) | 8 | 0.043 | 0.47 | 2.0 | 0.3 | 0.012 | ~6 |
| cooking_fuel (I2, L3 cat) | 10 | 0.038 | 0.43 | 2.0 | 0.3 | 0.010 | ~7 |
| lpg_cylinder (I2, L4) | 15 | 0.034 | 0.38 | 2.0 | 1.5 | 0.039 | ~1 |
| retail_tomato (I1, L4) | 20 | 0.028 | 0.13 | 2.0 | 1.5 | 0.011 | ~8 |

lpg_cylinder and retail_diesel should push to top 5 — much closer to ground truth.

**rbi example:**

| Node | Current rank | prob | world | leaf | Expected shift |
|------|:-----------:|-----:|------:|-----:|:-----:|
| india_forex_reserves (T3, L4) | 1 | 0.055 | 1.0 | 1.5 | → ~4 |
| savings_and_deposits (I5, L2 cat) | 2 | 0.049 | 2.0 | 0.3 | → ~12 |
| monetary_policy_committee (T2, L4) | 3 | 0.044 | 1.0 | 1.5 | → ~5 |
| fixed_deposits (I5, L4) | 7 | 0.040 | 2.0 | 1.5 | → ~1 |
| savings_account_balance (I5, L4) | 8 | 0.040 | 2.0 | 1.5 | → ~2 |
| home_loan_emi (I5, L4) | 25 | 0.010 | 2.0 | 1.5 | → ~8 |

home_loan_emi should rise from #25 to roughly #8. Still not #1, but dramatically better.

## Implementation

### Files to Modify

| File | Change |
|------|--------|
| `graph/markov_engine.py` | Add `_compute_cis()`, modify `evaluate_impact()` to sort by CIS |
| `config.py` | Add 4 new config params |
| `graph/scenarios.py` | C-type and D-type thresholds may need adjustment |
| `taxonomy/scenarios.yaml` | Threshold values may need updating |

### `config.py` Changes

```python
# Citizen Impact Score (CIS) factors
i_world_boost: float = 2.0           # Boost for I-world nodes
category_penalty: float = 0.3        # Penalty for is_category nodes (with children)
leaf_boost_l4: float = 1.5           # Boost for L4 leaf nodes
leaf_boost_l3: float = 1.2           # Slight boost for L3 non-category nodes
```

### `markov_engine.py` Changes

Add after `_compute_path_metrics()`:

```python
def _compute_cis(self, node: str, probability: float, magnitude: float) -> float:
    """Compute Citizen Impact Score: prob × mag × world_boost × leaf_boost."""
    nd = self.base_G.nodes.get(node, {})
    cat = nd.get('category', '')
    level = nd.get('level', 3)
    is_cat = nd.get('is_category', False)

    # World boost
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
```

Modify `evaluate_impact()`:
- Add `cis` field to each result dict
- Sort by `cis` descending instead of `probability`
- Keep `probability`, `magnitude`, `score` fields for backward compat

Modify `__init__()`:
- Accept CIS params (with defaults from config)

### Scenario Impact Assessment

**Type A (path_exists):** Unaffected — doesn't use scoring.

**Type B (reachability):** Unaffected — checks if nodes appear in results, not ranking.

**Type C (score_threshold):** Uses `probability > 0.001` check. May need adjustment if we change what the "score" field means. **Safe approach:** keep `probability` as the PPR value, add `cis` as a separate field. C-type checks `probability`, not `cis`.

**Type D (ranking):** Compares `probability` between two nodes. If we change the sort order to CIS, the ranking comparisons should still work since D-type reads from the result list position, not raw probability. **But** the D-type scenarios compare `higher_node` vs `lower_node` by probability — we need to check if CIS reordering breaks any D-type assertions.

**Type E (isolation):** Uses `probability < max_probability` — unaffected by CIS since we keep raw probability.

### D-Type Scenario Review

```yaml
d_crude_trade_over_emi:     india_trade_deficit > home_loan_emi  # T4 vs I4 — CIS will boost home_loan_emi, may flip!
d_monsoon_food_over_emi:    staple_grains > home_loan_emi        # I2-cat vs I4 — staple_grains gets category_penalty, may flip!
d_mpc_emi_over_tomato:      home_loan_emi > retail_tomato         # Both I-L4 — should hold
d_fed_nifty_over_rice:      nifty_50 > retail_rice               # T-L4 vs I-L4 — CIS boosts rice, may flip!
```

**3 of 4 D-type scenarios will likely need updating** after CIS is applied. This is expected — the old assertions encoded "T-world dominates" which is exactly what we're fixing.

**Important (Gemini review):** Do NOT blindly flip D-type assertions to make CI pass. For each changed assertion, verify against domain knowledge that the new ranking is the correct ground truth. Document the reasoning.

## Verification Plan

1. Apply CIS changes
2. Run `python3 -m graph.scenarios` — expect D-type failures
3. For each D-type failure: verify the NEW ranking is correct with domain reasoning, then update assertion
4. Re-run scenarios: 58/58 must pass
5. Run `python3 -m audit.event_replay` — target: mean NDCG@10 > 0.35
6. PPR spot-check 5 triggers with `--top 10`
7. If NDCG still below target, run `audit/tune_cis.py` grid search

## Tuning Strategy

If initial defaults don't hit NDCG > 0.35:

1. **Grid search** over `i_world_boost ∈ [1.5, 2.0, 3.0]` × `category_penalty ∈ [0.2, 0.3, 0.5]` × `leaf_boost_l4 ∈ [1.0, 1.5, 2.0]`
2. For each combo, run event replay, record mean NDCG@10
3. Pick the combo that maximizes NDCG while keeping all scenarios passing
4. Script this as `audit/tune_cis.py`

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| D-type scenarios break | High (expected) | Update assertions — they were encoding the wrong behavior |
| C-type thresholds break | Low | C-types check raw probability, not CIS |
| Over-boosting I-world creates false positives | Medium | Category penalty keeps I-world L2/L3 folders low |
| T-world nodes that ARE citizen-relevant (e.g. brent_crude as investment) get buried | Low | T-world L4 nodes keep world_boost=1.0 but still have leaf_boost=1.5 |
| NDCG improvement insufficient | Medium | Tuning strategy + may need graph coverage fixes too |

## What This Won't Fix

- **Missing paths** — auto_rickshaw_fare, delivery_and_logistics not reachable from crude. Need bridge edges.
- **Wrong trigger granularity** — `meteorological_systems` is too broad for AQI. Need `air_quality_environment` as trigger or more specific bridges.
- **Missing graph nodes** — Some ground truth nodes had to be remapped (e.g., `respiratory_illness` → `respiratory_conditions`).

These are **graph coverage** issues, not scoring issues. They should be addressed separately after CIS is implemented.

## Execution Order

```
1. Add CIS params to config.py
2. Add _compute_cis() to markov_engine.py (with childless category safeguard)
3. Modify evaluate_impact() to compute and sort by CIS
4. Update CLI output to show CIS column
5. Build audit/tune_cis.py (grid search — mandatory per Gemini review)
6. Run scenarios — note D-type failures
7. Validate each D-type assertion change against domain knowledge
8. Update D-type scenario assertions with documented reasoning
9. Run scenarios — 58/58
10. Run event replay — check NDCG improvement
11. If NDCG < 0.35: run tune_cis.py, pick best params
12. Commit
```

## Config Summary

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `i_world_boost` | 2.0 | 1.0-5.0 | Multiply CIS for I-world nodes |
| `category_penalty` | 0.3 | 0.1-0.5 | Multiply CIS for is_category nodes |
| `leaf_boost_l4` | 1.5 | 1.0-3.0 | Multiply CIS for L4 leaf nodes |
| `leaf_boost_l3` | 1.2 | 0.5-2.0 | Multiply CIS for L3 non-category nodes |

## Gemini Review (2026-03-19)

**Verdict: APPROVE WITH CHANGES** (all incorporated above)

1. **Childless category safeguard** — Added to `leaf_boost()`: if `is_category=true` but node has no CONTAINS children, skip penalty and use `leaf_boost_l3` instead.
2. **`leaf_boost_l3` bumped to 1.2** — Non-category L3 nodes are valuable citizen impacts, 1.0 was too close to T-world baseline.
3. **D-type validation requirement** — Each changed assertion must be verified against domain knowledge, not just flipped to pass.
4. **`tune_cis.py` mandatory** — Grid search must be part of the implementation, not a follow-up.

### Alternative approaches noted (not pursued, higher complexity):
- **Biased random walk** — Weight T→I transition probabilities higher in the Markov matrix itself. More principled but changes PPR semantics.
- **Two-phase PPR** — T-world walk → I-world walk. Cleanest separation but requires restructuring the engine.
- **UI separation** — Return two ranked lists (Macro Drivers + Citizen Impacts) instead of one mixed list.

Full review saved at `taxonomy/eval_results/cis_review_gemini.md`.
