# Graph V2: Taxonomy Separation + Edge Weights — Implementation Plan

## Context

The graph has 1,629 nodes, 2,585 edges. 29% of edges (729) are taxonomy (CONTAINS/LOCATED_IN), not causal. 558 leaf nodes have no causal edges. BFS without weights lights up the entire graph. This plan addresses all three problems.

---

## Architecture Decision: "Elevator and Train" Model

**Single graph, two traversal modes:**
- **Elevators** (IS_A edges) — move vertically between taxonomy levels for entity resolution
- **Trains** (AFFECTS/PRODUCES/etc.) — move horizontally across economy for impact propagation

When news mentions `basmati_rice` (taxonomy leaf, no causal edges):
1. NLP matches → `basmati_rice` node
2. Elevator UP via IS_A → `rice` (has causal edges)
3. Train ACROSS via causal edges → `food_inflation` → `cpi` → ...
4. Elevator DOWN (optional) → expand `public_transit` → "Delhi Metro, Mumbai Metro, ..."

---

## Edge Properties Schema

Every causal edge gets 3 new properties:

### `weight` (float)
- **Meaning:** Shock transfer strength — what % of a shock passes through
- **Tiers:** `0.9` (Critical), `0.7` (Strong), `0.4` (Moderate), `0.2` (Weak)
- **Never 1.0** — ensures mathematical decay
- **Path score:** multiply along path: W₁ × W₂ × W₃
- **Pruning threshold:** 0.05 (drop paths below this)

### `polarity` (int)
- **Meaning:** Directional correlation
- **Values:** `+1` (direct: A↑ → B↑), `-1` (inverse: A↑ → B↓), `0` (complex/volatility)
- **Path polarity:** multiply along path: P₁ × P₂ × P₃
- Example: crude_oil↑ → import_bill↑(+1) → rupee↓(-1) → IT_earnings↑(-1). Net: +1×-1×-1 = +1

### `delay` (string enum)
- **Values:** `IMMEDIATE` (days), `SHORT_TERM` (weeks), `MEDIUM_TERM` (months), `LONG_TERM` (years)
- **Path delay:** max(all delays in path) — bottleneck determines timeline
- Critical for UI: separate "today's impact" from "3-year structural shift"

### YAML format (after migration)
```yaml
- from: crude_oil
  to: petrol
  type: AFFECTS
  description: "India imports ~85% crude; refinery input costs set petrol pump prices"
  weight: 0.9
  polarity: 1
  delay: IMMEDIATE

- from: startup_layoffs
  to: rental_market
  type: AFFECTS
  description: "Tech layoffs reduce housing demand in IT hubs"
  weight: 0.2
  polarity: -1
  delay: MEDIUM_TERM
```

---

## Weight Assignment Pipeline (3 steps)

### Step 1: Rule-Based Defaults (automated, ~1,500 edges)

```python
STRUCTURAL_DEFAULTS = {
    "CONTAINS":   {"weight": 0.9, "polarity": 1, "delay": "IMMEDIATE"},  # Downward taxonomy
    "IS_A":       {"weight": 0.2, "polarity": 1, "delay": "IMMEDIATE"},  # Upward taxonomy (prevents fan-out)
    "PRODUCES":   {"weight": 0.9, "polarity": 1, "delay": "IMMEDIATE"},
    "SUPPLIES":   {"weight": 0.7, "polarity": 1, "delay": "SHORT_TERM"},
    "REGULATES":  {"weight": 0.8, "polarity": 1, "delay": "SHORT_TERM"},
    "DISRUPTS":   {"weight": 0.8, "polarity": -1, "delay": "IMMEDIATE"},
    "DEPENDS_ON": {"weight": 0.7, "polarity": 1, "delay": "SHORT_TERM"},
}
```

**Fan-out penalty:** If a node has >15 outgoing AFFECTS edges, cap max weight at 0.4 (unless it's a known macro hub: crude_oil, repo_rate, monsoon, etc.)

### Step 2: LLM Classifier (for ~700 AFFECTS edges)

Send batches of 50 edges to Gemini with descriptions. Ask for TIER classification, not float values.

**Prompt:**
```
You are an expert Indian macroeconomist. For each causal edge, assign:
1. "weight": Shock transfer strength. STRICTLY choose: 0.9 (Critical), 0.7 (Strong), 0.4 (Moderate), 0.2 (Weak)
2. "polarity": 1 (A↑→B↑), -1 (A↑→B↓), 0 (complex)
3. "delay": IMMEDIATE / SHORT_TERM / MEDIUM_TERM / LONG_TERM

Context: Indian economy. Consider local mechanisms.
Output: JSON array with from, to, weight, polarity, delay
```

### Step 3: Manual Hub Calibration (top 20 nodes)

Find nodes with highest degree centrality. Manually verify outgoing edge weights. These are the nodes where LLM errors cause the most damage:
- `crude_oil`, `repo_rate`, `monsoon`, `nifty_50`, `inr_usd`
- `cpi_inflation`, `it_services_sector`, `agriculture_sector`
- `electricity_tariff`, `real_estate_prices`

---

## Taxonomy Migration: CONTAINS → IS_A

### What changes:
1. **Reverse direction:** `rice CONTAINS basmati_rice` → `basmati_rice IS_A rice`
2. **Different weights by direction:**
   - Downward (sector → company): weight 0.9 (macro lifts all boats)
   - Upward (company → sector): weight 0.2 (one company rarely moves whole sector)
3. **Remove pure container nodes** from causal traversal (energy_and_fuel, food_and_nutrition, etc.)
   - Keep them for UI filtering/dashboards only
   - Mark with `is_container: true` property

### The 558 leaf nodes:
- **Keep as-is:** They're "NLP catchers" — match news text to graph nodes
- **Inherit causal edges** from nearest ancestor via elevator logic
- **Decision framework per leaf:**
  - Same causal chain as parent? → Keep as taxonomy leaf (inherit)
  - Different downstream effects? → Promote: add specific causal edges
  - True synonym? → Collapse into alias

---

## Traversal Algorithm: Modified Dijkstra

```python
def analyze_impact(graph, trigger_node, event_direction=1, threshold=0.05, max_depth=6):
    """
    Input:  trigger_node, event_direction (+1=up, -1=down)
    Output: [(node, score, polarity, delay, path), ...] sorted by score desc
    """
    # Max-heap via negative weights (Python heapq is min-heap)
    pq = [(-1.0, trigger_node, event_direction, [trigger_node], "IMMEDIATE")]
    max_weight_seen = {trigger_node: 1.0}
    impacts = []

    DELAY_RANK = {"IMMEDIATE": 0, "SHORT_TERM": 1, "MEDIUM_TERM": 2, "LONG_TERM": 3}

    while pq:
        neg_w, node, polarity, path, delay = heapq.heappop(pq)
        weight = -neg_w

        if node != trigger_node:
            impacts.append({"node": node, "score": weight, "polarity": polarity,
                           "delay": delay, "path": path})

        if len(path) >= max_depth:
            continue

        for edge in graph.out_edges(node):
            new_w = weight * edge.weight
            new_p = polarity * edge.polarity if edge.polarity != 0 else 0
            new_d = edge.delay if DELAY_RANK[edge.delay] > DELAY_RANK[delay] else delay

            if new_w < threshold:
                continue
            if new_w > max_weight_seen.get(edge.target, 0.0):
                max_weight_seen[edge.target] = new_w
                heapq.heappush(pq, (-new_w, edge.target, new_p, path + [edge.target], new_d))

    return sorted(impacts, key=lambda x: x["score"], reverse=True)
```

### Elevator logic (for taxonomy leaves):
```python
def get_causal_entry(graph, node):
    """Walk UP IS_A edges until we find a node with causal out-edges."""
    causal_types = {"AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES", "DEPENDS_ON"}
    visited = set()
    current = node

    while current and current not in visited:
        visited.add(current)
        out_types = {graph.edges[current, s].get("type") for s in graph.successors(current)}
        if out_types & causal_types:
            return current  # Found a node with causal edges
        # Go up IS_A
        parents = [p for p in graph.successors(current)
                   if graph.edges[current, p].get("type") == "IS_A"]
        current = parents[0] if parents else None

    return node  # Fallback: return original
```

---

## Validation Strategy

### Macro validation (systemic bias check):
Fire 50 random trigger nodes. Measure avg nodes activated.
- Target: macro trigger (crude_oil) → 40-60 nodes
- Target: niche trigger (zoho) → 3-8 nodes
- If avg > 100: weights too high or threshold too low
- If avg < 3: weights too low or threshold too high

### 4 scenario tests:
1. **RBI repo rate +25bps:** home_loan_emi↑(>0.8), nifty_50↓(~0.7), fd_returns↑(>0.8)
2. **Monsoon -20%:** crop_yield↓(0.9), food_inflation↑(0.81), rural_demand↓(0.63)
3. **Crude oil $100:** petrol↑(0.9), transport↑(0.81), cpi↑(0.56), rupee↓(0.49)
4. **IT layoffs 10k:** bangalore_rent↓(0.49), personal_loan_npa↑(0.4), construction pruned

### Cycle death test:
Trigger inflation → repo_rate → growth → inflation loop. Verify termination via max_weight_seen decay.

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sibling fan-out (TCS→IT→Infosys) | False positives | Block IS_A→CONTAINS traversal if needed |
| LLM weight hallucination | Wrong pruning | Manual hub review covers 90% of blast radius |
| Polarity collision (2 paths, opposite polarity) | Confusing output | V1: strongest path wins. V2: sum weighted polarities |
| Cycles | Infinite loop | max_weight_seen + MAX_DEPTH=6 |
| Time delay mixing | Mix today vs 3-year effects | Group output by delay tier |

---

## Implementation Order (80/20)

| Phase | What | Hours | Value |
|-------|------|-------|-------|
| 1 | Core traversal engine (mock data, prove math works) | 3h | Foundation |
| 2 | Rule-based weight migration (CONTAINS/REGULATES/etc.) | 2h | ~60% edges covered |
| 3 | CONTAINS → IS_A reversal + container node marking | 2h | Clean taxonomy |
| 4 | LLM batch weight assignment (AFFECTS edges) | 3h | Remaining ~40% edges |
| 5 | Hub calibration (manual review top 20 nodes) | 2h | Accuracy for critical paths |
| 6 | Integration + 4 scenario CLI tests | 2h | Validation |
| **Total** | | **~14h** | |

### What to skip in V1:
- Dynamic weights / context multipliers (V2)
- UI presentation layer (V2)
- Polarity collision resolution (V2 — strongest path wins for now)
- Empirical calibration from real news data (V3)

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `graph/traverse.py` | CREATE | Impact propagation engine + elevator logic |
| `graph/migrate_weights.py` | CREATE | Rule-based + LLM batch weight assignment |
| `graph/merge.py` | MODIFY | Support weight/polarity/delay properties, IS_A reversal |
| `taxonomy/edge_patches.yaml` | MODIFY | Add weight/polarity/delay to all edges |
| `taxonomy/universal_life_dependency_graph.yaml` | MODIFY | Reverse CONTAINS → IS_A |
| `audit/test_scenarios.py` | CREATE | 4 scenario validation tests |
