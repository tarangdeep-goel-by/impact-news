# Bridge Architecture Redesign — v5 Plan

## Problem Statement

L2→L2 bridge mandate (Rule 18) creates false causal links. `global_commodity_markets` lumps energy, agriculture, and metals — a gold price article scores as affecting wheat flour. The elevator pattern + ancestor seeding amplifies this: ANY leaf under a source L2 reaches ALL leaves under ALL target L2s.

**Root cause:** Fixed bridge level ignores that L2s vary in homogeneity. Some L2s (like `household_energy`) are genuinely uniform; others (like `global_commodity_markets`) contain causally distinct L3 subcategories.

**Second gap:** No upward aggregation exists. If 3 of 4 fuel types are hit, the system doesn't recognize that `vehicle_fuel` (L3) is broadly affected, or that `private_vehicle_ownership` (L2) is under systemic pressure.

## Current State

| Metric | Count |
|--------|-------|
| Total bridge edges | 173 |
| L2→L2 bridges | 95 |
| Leaf-to-leaf (L4→L4, L3→L4, etc.) | 78 |
| Truly homogeneous L2 sources | 3 |
| Heterogeneous L2 sources (need decomposition) | 21 |
| Scenarios testing L2→L2 directly | 0 |
| Total scenarios | 47 |

Zero scenarios directly test L2→L2 paths — decomposition is safe.

## Design Decisions

### Decision 1: Homogeneity-Based Bridge Level

**Rule:** Bridge target level = natural homogeneity boundary of the impact.

Test: "Would this trigger affect ALL L3 siblings under the target L2 with the same mechanism, weight, polarity, and delay?"
- YES → L2 bridge is fine
- NO → decompose to L3

Examples:
- `energy_commodities` (T-L3) → `vehicle_fuel` (I-L3) — YES, oil affects all motor fuels
- `energy_commodities` (T-L3) → `private_vehicle_ownership` (I-L2) — NO, oil doesn't affect vehicle insurance
- `monsoon_systems` (T-L3) → `fresh_produce` (I-L2) — YES, monsoon affects all produce uniformly
- `monetary_policy_committee` (T-L4) → `home_loan_emi` (I-L4) — YES, narrow specific chain

### Decision 2: Upward Impact Aggregation

After traversal reaches impact leaves, roll up to parent nodes:

```
coverage(L3) = count(affected_children) / count(total_children)
diversity(L2) = count(affected_L3_branches) / count(total_L3_branches)
systemic_score(L2) = mean(child_scores) × diversity × coverage_factor
```

This enables richer user explanations:
- diversity=1.0, coverage=0.9 → "This affects your ENTIRE vehicle ownership"
- diversity=0.33, coverage=1.0 → "This affects your fuel costs specifically"

### Decision 3: Elevator Redesign

Current elevator seeds from ALL CONTAINS ancestors — this is the amplifier of false links. After bridge decomposition, the elevator should be **scoped**:

- Walk up only until finding a node with causal out-edges (current `get_causal_entry` behavior — this is fine)
- **Remove ancestor multi-seeding** from `_get_contains_ancestors` in `analyze_impact` — the entry point is sufficient
- Instead, if the entry point has no bridges, try ONE level up (not all ancestors)

This prevents `brent_crude` from seeding at `global_commodity_markets` when `energy_commodities` already has proper bridges.

## Taxonomy Homogeneity Map

### Homogeneous I-L2s (safe as bridge targets)

These L2s can remain as bridge targets — all L3 children respond uniformly to triggers:

| I-L2 | Category | Why Homogeneous |
|------|----------|----------------|
| household_energy | I2 | Both cooking_fuel + residential_electricity are energy-cost-driven |
| water_and_sanitation | I2 | Both municipal service-dependent |
| public_transit | I3 | Both public service fare-dependent |
| on_demand_transit | I3 | Both surge-pricing-dependent |
| borrowing_and_credit | I5 | Both EMI-structure-dependent (interest rate → all) |
| savings_and_deposits | I5 | Both savings-instrument-dependent |
| retirement_and_provident_funds | I5 | Both retirement-corpus-dependent |
| insurance_premiums | I5 | Both insurance-obligation-dependent |
| healthcare_services | I6 | All access/cost-dependent |
| education_economics | I7 | All fee-dependent |
| digital_and_cyber_security | I8 | All digital-threat-dependent |
| air_quality_environment | I9 | Both AQI-source-dependent |
| weather_and_thermal_environment | I9 | Both climate-dependent |
| urban_hydrology | I9 | Both water-system-dependent |
| civic_cleanliness | I9 | Both sanitation-dependent |
| sensory_environment | I9 | Both pollution-dependent |
| urban_ecology | I9 | Both biodiversity-dependent |
| telecom_and_internet_access | I10 | Both connectivity-dependent |
| digital_payments_interface | I10 | Both payment-adoption-dependent |
| digital_communication_platforms | I10 | All communication-access-dependent |
| digital_privacy_and_hygiene | I10 | All digital-threat-dependent |
| sports_and_recreation | I11 | Both leisure-dependent |
| community_and_civic_life | I11 | Both local-governance-dependent |
| travel_and_tourism | I11 | Both tourism-infrastructure-dependent |

### Heterogeneous I-L2s (MUST decompose to L3 targets)

| I-L2 | Category | Why Heterogeneous | L3 Targets |
|------|----------|-------------------|------------|
| private_vehicle_ownership | I3 | Fuel, acquisition, maintenance have independent triggers | vehicle_fuel, vehicle_acquisition, vehicle_maintenance_and_compliance |
| intercity_travel | I3 | Rail, air, bus have different cost structures | railway_travel, air_travel, highway_bus_travel |
| road_infrastructure_experience | I3 | Tolls vs congestion affect different users | highway_tolls, urban_road_conditions |
| shelter_and_accommodation | I2 | Rent vs construction vs EMI follow distinct paths | rental_housing, home_construction |
| residential_maintenance_and_services | I2 | RWA fees vs wages vs repair costs | rwa_fees, domestic_labor, home_upkeep |
| fresh_produce | I1 | Vegetables vs fruits have different supply chains | (assess: may actually be homogeneous for weather triggers) |
| protein_sources | I1 | Meat vs dairy vs seafood: distinct supply, cultural factors | meat_and_seafood, dairy_and_eggs |
| market_investments | I5 | Stocks vs MF tax treatment differs | equity_investments, mutual_funds |
| taxation_and_compliance | I5 | Income tax vs capital gains vs TDS: independent rates | personal_income_tax, capital_gains_tax |
| physical_and_alternative_assets | I5 | Gold vs property vs crypto: distinct dynamics | precious_metals, real_estate_investment, digital_alternatives |
| competitive_exams_and_coaching | I7 | JEE vs UPSC vs coaching: independent ecosystems | entrance_examinations, government_job_exams, test_prep_industry |
| entertainment_and_media | I11 | Cinema vs streaming vs live events: different economics | cinema_and_theatre, digital_entertainment, live_events |
| cultural_and_religious_life | I11 | Festivals vs weddings vs pilgrimage: different timing/spend | festivals_and_celebrations, weddings_and_milestones, religious_pilgrimage |

### Heterogeneous T-L2s (source side — bridge FROM L3, not L2)

| T-L2 | Category | Why | L3 Sources |
|------|----------|-----|------------|
| global_commodity_markets | T3 | Energy/agri/metals are independent domains | energy_commodities, agricultural_commodities, precious_and_industrial_metals |
| energy_and_power_infrastructure | T4 | Coal vs renewables vs nuclear: different policy | coal_power_plants, renewable_energy_parks, nuclear_power_plants, etc. |
| digital_and_telecom_infrastructure | T4 | Spectrum vs fiber vs cables: different bottlenecks | telecom_spectrum, optical_fibre_network, data_centers, etc. |
| social_movements_and_collectives | T5 | Labor vs farmers vs identity: separate constituencies | labor_and_trade_unions, agrarian_collectives, identity_and_rights_movements |

## Phases

### Phase 1: Bridge Decomposition (Data Work)

**Goal:** Replace 95 L2→L2 bridges with ~150 targeted bridges at natural homogeneity boundaries.

**Steps:**

1a. **Classify existing 95 L2→L2 bridges** using homogeneity map above
   - Tag each as KEEP_L2 (target is homogeneous) or DECOMPOSE (target is heterogeneous)
   - For DECOMPOSE: identify which L3 targets apply
   - For heterogeneous T-sources: split source to L3 too

1b. **Audit the 78 leaf bridges**
   - Check if each leaf bridge is already covered by a new L3-level bridge
   - If covered → remove (redundant, CONTAINS propagation handles it)
   - If not covered → keep (specific causal link not captured at L3)
   - Goal: minimize leaf bridges to only those with unique causal specificity

1c. **Write new bridge_edges.yaml**
   - Replace L2→L2 with appropriate L3→L3, L3→L2, T-leaf→I-L3, etc.
   - Each edge needs: from, to, type, weight, polarity, delay, description
   - Validate: no edge creates a false causal link (homogeneity test per edge)

1d. **Update bridge_matrix.yaml and bridge_classification.yaml**
   - Reflect new structure
   - Add homogeneity annotations

**Estimated edges after decomposition:**

| Type | Before | After |
|------|--------|-------|
| L2→L2 (homogeneous targets) | 95 | ~30-40 |
| L3→L3 / L3→L2 (decomposed) | 0 | ~80-100 |
| Leaf-to-leaf (specific) | 78 | ~30-40 (pruned redundant) |
| **Total** | 173 | ~150-180 |

### Phase 2: Elevator & Traversal Redesign (Code Work)

**Goal:** Fix ancestor seeding to prevent false bridge access. Add upward aggregation.

2a. **Scope the elevator** (`traverse.py`)
   - `get_causal_entry()` — keep as-is (walk up to first causal hub)
   - `analyze_impact()` — **remove blanket ancestor seeding**:
     ```python
     # BEFORE (seeds from ALL ancestors):
     for ancestor, cum_weight in _get_contains_ancestors(G, entry):
         heapq.heappush(heap, (-cum_weight, ancestor, ...))

     # AFTER (only seed from entry point):
     # Entry point already found by get_causal_entry()
     # If entry has no causal out-edges, try ONE parent up
     # No blanket ancestor seeding
     ```
   - This is safe because bridges now exist at the right level — no need to climb to L2

2b. **Add upward impact aggregation** (`traverse.py`)

   After Dijkstra + downward CONTAINS propagation, add a roll-up phase:

   ```python
   def _aggregate_upward(G, reached_nodes, reached_scores):
       """Roll up leaf impacts to parent nodes."""
       aggregated = {}
       for parent in all_category_nodes:
           children = get_contains_children(G, parent)
           if not children:
               continue
           hit_children = [c for c in children if c in reached_scores]
           coverage = len(hit_children) / len(children)
           if coverage == 0:
               continue
           mean_score = mean([reached_scores[c] for c in hit_children])
           aggregated[parent] = {
               'score': mean_score * coverage,
               'coverage': coverage,
               'diversity': len(set(get_l3_branch(c) for c in hit_children)),
               'hit_children': hit_children,
               'total_children': len(children),
           }
       return aggregated
   ```

   This gives the scoring layer information to say:
   - "Crude oil spike affects 3/4 of your fuel costs (75% coverage)"
   - "This is a narrow fuel impact, not a systemic vehicle ownership issue"

2c. **Update `compute_relevance()`** (`traverse.py`)
   - Use aggregated parent scores when user tracks an L2/L3 node
   - If user tracks `private_vehicle_ownership` (L2), the relevance score should reflect
     how many L3 branches are hit, not just whether any child matched

### Phase 3: Scenario & Validation Rework

**Goal:** Test that decomposition preserves real paths and eliminates false ones.

3a. **Add negative scenarios** (new concept)
   - "gold prices should NOT reach wheat_flour" (was false-positive before)
   - "international_silver_prices should NOT reach retail_petrol"
   - Test that decomposition killed spurious paths

3b. **Update existing 47 scenarios**
   - Most should still pass (they test leaf→leaf paths, not L2→L2)
   - Update any that relied on L2→L2 bridge traversal
   - Add coverage/diversity assertions to scenario type C

3c. **Add aggregation scenarios** (new type D)
   ```yaml
   - id: crude_oil_vehicle_fuel_coverage
     type: D
     trigger_node: brent_crude
     parent_node: vehicle_fuel
     min_coverage: 0.5
     expected_hit_children: [retail_petrol, retail_diesel, cng_fuel]
   ```

3d. **Regression test: no score inflation**
   - Compare scores before/after for 10 representative articles
   - False positives should drop; true positives should stay or improve

### Phase 4: Rule 18 Rewrite (TAXONOMY.md)

**Goal:** Replace fixed L2 mandate with homogeneity-based rule.

New Rule 18:
```
Rule 18 — Bridge Targeting (Homogeneity Principle)

Bridge edges connect Trigger nodes to Impact nodes across worlds.
The target level is determined by the homogeneity of the causal effect:

(a) HOMOGENEITY TEST: "Does this trigger affect ALL L3 siblings under
    the target with the same mechanism, weight, polarity, and delay?"
    - YES → target the L2 (CONTAINS propagation handles children)
    - NO  → target specific L3s (or L4s if L3 is also heterogeneous)

(b) SOURCE LEVEL: Trigger sources should be the most specific node
    where the causal mechanism originates. Prefer L3/L4 leaves over
    L2 categories. Only use T-L2 as source when the entire subcategory
    acts as a unit (e.g., meteorological_systems as a whole).

(c) LEAF BRIDGES: Permitted when the causal link has unique specificity
    not captured at L3 level (e.g., monetary_policy_committee → home_loan_emi).
    Must not duplicate coverage already provided by an L3 bridge.

(d) NO UPWARD BRIDGING: Bridges must not target L1 categories.
    If an entire L1 is affected, it should emerge from multiple L2/L3
    bridges via upward aggregation, not from a single L1 bridge.

(e) VALIDATION: Every new bridge requires:
    1. Homogeneity test documented in description
    2. At least one scenario in scenarios.yaml
    3. One negative scenario proving it doesn't create false paths
```

### Phase 5: Tooling & Process

5a. **Bridge linter** (`graph/quality.py`)
   - Warn on any new L2→L2 bridge where target is in heterogeneous list
   - Flag L2→L2 bridges without homogeneity annotation
   - Report coverage gaps: "energy_commodities has no bridge to cooking_fuel"

5b. **Gemini bridge generator update** (`scripts/graph_builder.py`)
   - Update prompts to target L3 by default
   - Include homogeneity test in generation prompt
   - Generate negative scenarios alongside bridges

## Execution Order & Dependencies

```
Phase 1 (data) ─────────────────────────────────────────────►
  1a: Classify L2→L2 bridges
  1b: Audit leaf bridges           (blocked by 1a)
  1c: Write new bridge_edges.yaml  (blocked by 1a, 1b)
  1d: Update matrix/classification (blocked by 1c)

Phase 2 (code) ─────────────────────────────────── (parallel with late Phase 1)
  2a: Scope elevator               (independent)
  2b: Upward aggregation           (independent)
  2c: Update compute_relevance     (blocked by 2b)

Phase 3 (validation) ────────────────────────────── (blocked by Phase 1c + 2a/2b)
  3a: Negative scenarios
  3b: Update existing scenarios
  3c: Aggregation scenarios (type D)
  3d: Regression scoring test

Phase 4 (docs) ──────────────────────────────────── (parallel with Phase 3)
  4: Rewrite Rule 18

Phase 5 (tooling) ───────────────────────────────── (after Phase 3)
  5a: Bridge linter
  5b: Generator update
```

**Parallelizable:** Phase 2 (code) can run alongside Phase 1 (data). Phase 4 (docs) can run alongside Phase 3 (validation).

## Success Criteria

1. **No false causal paths:** `international_gold_prices` does NOT reach `wheat_flour`
2. **Real paths preserved:** `brent_crude` → `retail_petrol` still works with score ≥ 0.7
3. **Coverage ≥ current:** Every T-L3 with real citizen impact has at least one bridge
4. **Aggregation works:** `brent_crude` trigger shows coverage=0.75 for `vehicle_fuel`
5. **All scenarios pass:** 47 existing + new negative + new aggregation scenarios
6. **Edge count reasonable:** 150-180 total bridges (not an explosion)

## Risks

| Risk | Mitigation |
|------|-----------|
| Decomposition creates too many edges | Cap at L3; don't go L4 unless necessary |
| Elevator change breaks existing paths | Run full scenario suite after each change |
| Upward aggregation is slow | Only aggregate for nodes in user profile |
| Gemini generates poor L3 bridges | Human review + negative scenario tests |
| Some L2s are borderline homogeneous | Default to L3 targeting; L2 only with explicit justification |
