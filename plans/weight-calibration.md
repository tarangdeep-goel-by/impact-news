# Weight Calibration Plan

## Problem

Weights are clustered at 0.7-0.8 (63% of all 755 causal edges). Every edge looks equally important. This causes:
- PPR score spread is 1-6x between #1 and #10 result (should be 10-50x)
- Wrong rankings: e.g., RBI rate hike shows forex_reserves as #1 impact instead of home_loan_emi
- Coal crisis shows school_fees at #2 instead of electricity_tariff
- Delhi AQI shows macro_indicators instead of hospital admissions

## Step 1: Structural Heuristics (mechanical, no Gemini)

Apply type-based weight defaults that differentiate edge strength by causal mechanism. These are priors — Gemini will refine in Step 2.

### Default weight bands by edge type

| Type | Default Range | Rationale |
|------|--------------|-----------|
| PRODUCES | 0.85-0.95 | Direct creation — almost 1:1 pass-through |
| SUPPLIES | 0.70-0.85 | Physical input — strong but supply chain absorbs some shock |
| FUNDS | 0.75-0.90 | Financial flow — strong, direct transfer |
| DISRUPTS | 0.50-0.75 | Negative shock — impact varies by severity and resilience |
| DEPENDS_ON | 0.80-0.95 | Structural reliance — binary (works or doesn't) |
| REGULATES | 0.50-0.70 | Regulatory constraint — effect is policy-dependent |
| AFFECTS | 0.30-0.60 | Generic covariation — the weakest, most indirect type |

### Adjustment factors (multiply on top of type default)

| Factor | Multiplier | When |
|--------|-----------|------|
| Same L1 | 1.0 | Intra-L1 edges (tight coupling) |
| Adjacent L1 | 0.9 | Cross-L1 within closely related domains |
| Distant L1 | 0.8 | Cross-L1 between unrelated domains |
| L4→L4 | 1.0 | Leaf-to-leaf (most specific) |
| L3→L3 | 0.95 | Category-to-category (slightly abstracted) |
| L2→L3 | 0.90 | Broad source to specific target |

### Implementation

```python
# audit/calibrate_weights.py
# Phase 1: Apply structural heuristic defaults

TYPE_DEFAULTS = {
    'PRODUCES':   0.90,
    'SUPPLIES':   0.78,
    'FUNDS':      0.82,
    'DISRUPTS':   0.62,
    'DEPENDS_ON': 0.88,
    'REGULATES':  0.60,
    'AFFECTS':    0.45,
}

# For each edge:
# 1. Look up type default
# 2. Apply cross-L1 multiplier
# 3. Apply level-based multiplier
# 4. Clamp to [0.2, 0.95]
```

### Expected outcome
- AFFECTS edges drop from mean 0.75 → ~0.45 (massive differentiation)
- PRODUCES/SUPPLIES stay high (0.78-0.90)
- Overall distribution spreads from [0.7-0.8] to [0.3-0.9]
- PPR rankings should shift: direct causal chains rank higher

### Verification
- Run scenarios: 58/58 must still pass (some C-type score thresholds may need adjustment)
- Run PPR for 5 triggers: check that rankings improve (e.g., RBI → home_loan_emi should rank higher)

---

## Step 2: Gemini Re-Rating (per-batch refinement)

After Step 1 establishes differentiated priors, ask Gemini to refine individual weights using concrete pass-through reasoning.

### Prompt design

For each batch of ~30 edges:

```
You are calibrating edge weights for a causal knowledge graph.
Weight = "causal pass-through rate" — if the source entity changes by 10%,
what percentage of that change reaches the target?

Examples:
- brent_crude → retail_diesel: If crude rises 10%, diesel rises ~8%. Weight = 0.80
- brent_crude → retail_tomato: If crude rises 10%, tomato rises ~2%. Weight = 0.20
- monetary_policy_committee → home_loan_emi: If repo rate changes 10%, EMI changes ~7%. Weight = 0.70
- southwest_monsoon → retail_rice: If monsoon deficit is 10%, rice price rises ~5%. Weight = 0.50

For each edge below, estimate the pass-through rate (0.1 to 1.0).
Think about: buffer mechanisms, time delays, alternative sources,
price stickiness, and government intervention.

Return YAML: [{from, to, weight, reasoning}]
```

### Batching strategy

| Batch | Edges | Focus |
|-------|-------|-------|
| 1 | T→T laterals in T1 (natural systems) | 55 edges |
| 2 | T→T laterals in T2 (institutional) | 79 edges |
| 3 | T→T laterals in T3 (macro) | 45 edges |
| 4 | T→T laterals in T4+T5 (infra + social) | 88 edges |
| 5 | T→I bridges batch 1 (energy + food) | ~80 edges |
| 6 | T→I bridges batch 2 (finance + health + other) | ~80 edges |
| 7 | T→I bridges batch 3 (remaining) | ~80 edges |
| 8 | I→I laterals batch 1 (I1-I5) | ~100 edges |
| 9 | I→I laterals batch 2 (I6-I11 + cross-L1) | ~120 edges |

~9 Gemini calls. Each ~20-30K tokens input, ~5-10K output.

### Post-processing

For each edge:
1. If Gemini weight differs from heuristic by >0.3 → flag for manual review
2. If Gemini weight < 0.15 → consider removing the edge (too weak for PPR)
3. Take Gemini weight as final (overrides heuristic)

### Verification
- Same as Step 1: scenarios + PPR rankings
- Compare before/after weight distributions per type
- Check that AFFECTS edges are now genuinely lower than SUPPLIES/PRODUCES

---

## Step 3: Historical Event Replay (validation)

Use real news events to validate that PPR rankings match reality.

### Events (5 chosen for coverage)

| # | Event | Date | Trigger node | Expected top citizen impacts |
|---|-------|------|-------------|----------------------------|
| 1 | Crude oil $120/barrel | Mar 2022 | brent_crude | retail_diesel, retail_petrol, lpg_cylinder, auto_rickshaw_fare, freight→tomato |
| 2 | RBI rate hike 250bps | 2022-23 | rbi | home_loan_emi, savings_deposit_rates, credit_card_interest, personal_loan_emi |
| 3 | Monsoon deficit 40% | Aug 2023 | southwest_monsoon | retail_tomato, retail_onion, dal prices, retail_rice, farm_labor_wages |
| 4 | Delhi AQI 500+ | Nov 2023 | meteorological_systems | hospital_beds (respiratory), school closures, outdoor_heat workers, air_purifier demand |
| 5 | IT layoff wave | Jan 2023 | us_federal_reserve | it_sector_salary, credit_card_dues, residential_rent, startup_layoffs |

### Ground truth construction

For each event:
1. Feed 5-10 real news articles from that period to Gemini
2. Ask: "List the top 10 citizen-level impacts mentioned, ranked by severity"
3. Map each impact to graph node IDs
4. Result: ordered list of (node_id, expected_rank)

### Scoring

```python
# For each event:
# 1. Run PPR with trigger
# 2. Get top 20 results ranked by probability
# 3. Compare with ground truth using NDCG@10
#    (Normalized Discounted Cumulative Gain — standard ranking metric)
# 4. NDCG > 0.7 = good, > 0.5 = acceptable, < 0.3 = weight problem

# If a ground truth node doesn't appear in PPR top 20:
#   → Missing edge or weight too low on the path
# If a PPR top-5 node doesn't appear in ground truth:
#   → Weight too high on that path (false positive)
```

### Implementation

```python
# audit/event_replay.py

EVENTS = [
    {
        "id": "crude_2022",
        "trigger": "brent_crude",
        "direction": 1,
        "ground_truth": [
            # (node_id, rank_1_is_best)
            ("retail_diesel", 1),
            ("retail_petrol", 2),
            ("lpg_cylinder", 3),
            ("auto_rickshaw_fare", 4),
            ("retail_tomato", 5),
            ("freight_cost", 6),  # may not exist
            ("savings_account_balance", 7),
        ],
    },
    # ... 4 more events
]

# For each event:
# 1. Run engine.evaluate_impact(trigger)
# 2. Compute NDCG@10 against ground truth
# 3. Report mismatches
```

### Iteration loop

```
Step 1 (heuristics) → run replay → identify worst event
  → Step 2 (Gemini re-rate edges on that event's path)
  → run replay again → check improvement
  → repeat for next worst event
```

### Expected outcome
- NDCG@10 > 0.5 for all 5 events after calibration
- PPR top-5 for each event matches common-sense news impacts
- No false positives in top-10 (e.g., school_fees from coal crisis)

---

## Execution Order

```
Session N (next):
  1. Build audit/calibrate_weights.py (Step 1)
  2. Apply structural heuristics to all 755 edges
  3. Run scenarios + PPR spot-check
  4. Build audit/gemini_rerate.py (Step 2)
  5. Run Gemini re-rating in 9 batches
  6. Apply Gemini weights, run scenarios
  7. Build audit/event_replay.py (Step 3)
  8. Construct ground truth for 5 events (Gemini-assisted)
  9. Run replay, compute NDCG@10
  10. Fix worst mismatches, iterate
```

Total Gemini calls: ~9 (re-rating) + 5 (ground truth construction) = ~14
Estimated tokens: ~300K input + ~100K output
