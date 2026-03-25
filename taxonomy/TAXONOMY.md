# Taxonomy v4 — Impact News Knowledge Graph

## Status: CONSTITUTION v4.1 (2026-03-18). L1s LOCKED. Rules updated per Gemini 3.1 Pro review.

---

## Graph Constitution

The rules below govern all graph construction. They are ordered by precedence — earlier rules override later ones in case of conflict.

---

### Rule 1: Entity Principle

Nodes are **entities** (things that exist), not events or changes.

- `crude_oil` is a node. `crude_oil_price_hike` is NOT — that's an edge property.
- `monsoon` is a node. `monsoon_deficit` is NOT.
- The graph captures what exists; edges capture what changed and how.

Because nodes are static entities, causal edges represent **covariation** — how changes in one entity relate to changes in another:
- Polarity **+1** = directly proportional (A increases → B increases)
- Polarity **-1** = inversely proportional (A increases → B decreases)

Every node has an implied **axis** — the dimension that "increases" or "decreases" means. Examples:
- `unemployment` — axis: unemployment rate (up = more unemployment)
- `auto_rickshaw_fare` — axis: cost in INR (up = more expensive)
- `retail_tomato` — axis: retail price (up = costlier)

Polarity describes the **entity's value**, not the edge verb. `monsoon` DISRUPTS `crop_yield` with polarity **-1** means: when monsoon strength increases, crop yield decreases. The verb `DISRUPTS` is semantic context for humans; the polarity is the math.

---

### Rule 2: Trigger/Impact Classification (Locus of Interface Test)

> Can a single citizen directly experience this entity in their body, wallet, schedule, or environment?

- **YES → Impact** (citizen-level entity)
- **NO → Trigger** (system-level entity)

Impacts can cause other Impacts. Triggers can cause other Triggers. The split is about the entity's **nature**, not its position in a causal chain.

---

### Rule 3: Dual-Nature Prevention

A node exists in **ONE world only** — Trigger OR Impact, never both.

If an entity has both a system-level and citizen-level face, it becomes **two nodes**:
- `crude_oil` (T3, the global commodity) — Trigger
- `retail_diesel` (I3, what you pay at the pump) — Impact

The bridge edge between them connects the two worlds. This is by design.

---

### Rule 4: One Node, One Home

Each node belongs to exactly **one L1 tree**. No duplicates across L1s or source files.

If a node has secondary relevance to another L1, it stays in its primary home and gets a `secondary_tags` field:

```yaml
digital_payments:
  category: I5   # Primary home: Finance
  secondary_tags: [I10]  # Also relevant to: Digital Life
```

Cross-L1 relevance is expressed through **portal edges**, not duplicate nodes.

---

### Rule 5: Leaf Node Test

A node is a valid **leaf** when it satisfies ALL three:

| Test | Question | Failure Mode |
|------|----------|-------------|
| **Matchable** | Could an LLM reading a news headline plausibly extract this as a tag? | Too abstract → go deeper |
| **Mappable** | Could a user's onboarding answer plausibly connect to this? | Too obscure → reconsider |
| **Edgeable** | Does it have at least one meaningful causal edge (not just IS_A/CONTAINS)? | Too granular → go up |

---

### Rule 6: Vertical Edge Semantics

Two vertical edge types. Never mix them.

| Edge | Meaning | Use | Example |
|------|---------|-----|---------|
| `CONTAINS` | Parent is a **group**, child is a **member** | Taxonomy levels: L1→L2→L3 | I1 Food CONTAINS Staples |
| `IS_A` | Child is a **subtype** of parent | Within-level specialization only | `atta` IS_A `staple_grain` |

---

### Rule 7: Three Types of Lateral Edges

The graph has three kinds of non-hierarchical connections:

| Type | Connects | Example | Built In |
|------|----------|---------|----------|
| **Intra-tree** | Nodes within same L1 | `retail_diesel` → `freight_cost` (both I3) | Phase 1b / 2b |
| **Portal** | Nodes across different L1s, same world | `freight_cost` (I3) → `retail_tomato` (I1) | Phase 1b / 2b |
| **Bridge** | Trigger node → Impact node (level per Rule 18) | `brent_crude` (T3-L4) → `lpg_cylinder` (I2-L4) | Phase 3 |

Portal edges can connect nodes at **any level** — an L3 in one tree can link to an L3 in another. In the Impact world, L2 nodes must not be targeted (Rule 20); in the Trigger world, L2 targets are permitted when homogeneous (Rule 18).

**No I→T feedback edges.** Earlier designs included feedback edges (Impact→Trigger) modeling how citizen outcomes influence system entities. These were removed because they create cycles and "everything affects everything" paths. If an I-world node is actually an aggregate metric (e.g., `urban_unemployment_rate`), it likely belongs in T-world — fix the classification rather than adding feedback edges.

---

### Rule 8: Node Connector Tags

Nodes that participate in cross-tree connections get metadata tags:

| Tag | Meaning | Example |
|-----|---------|---------|
| `port: true` | Receives **bridge** edges (T→I) | `retail_diesel` — landing point from Trigger world |
| `portal: true` | Has **cross-L1** edges within same world | `freight_cost` — connects I3 Transport to I1 Food |

These tags are discovered naturally during edge construction phases. They exist to make bridge/portal wiring explicit and auditable.

---

### Rule 9: Sibling Distinctness

Nodes at the same level under the same parent should be **as mutually exclusive as practical**.

Test: "Can a news article affect node A without affecting node B?" If yes, they're distinct enough. If they always co-move, merge them.

Strict MECE is not required — socioeconomic entities overlap. Pragmatic distinctness is sufficient.

---

### Rule 10: Granularity Parity

Within each L1, leaf nodes should be at roughly the **same taxonomic depth**.

Don't place `retail_tomato` alongside `vegetables` — one is a leaf entity, the other is a category. If `vegetables` exists, `retail_tomato` goes under it, not beside it.

**Trees define structure. Weights define scale.** A tomato is taxonomically a vegetable — that relationship is expressed in the tree. Its outsized importance to Indian inflation is expressed through high **edge weights**, not by promoting it to a higher taxonomy level.

---

### Rule 11: India-First Scoping

Different scoping tests for each world:

- **Impact nodes:** "Would this plausibly appear in an Indian news headline in 2026?" We need `atta`, `dal`, `onion` — not `pizza_and_quiche`.
- **Trigger nodes:** "Does this entity have a demonstrable causal path (≤4 hops) to an Indian citizen Impact node?" This includes global/geopolitical entities (`us_federal_reserve`, `opec_crude_supply`, `global_shipping_routes`) that causally reach Indian citizens.

Geopolitical entities do not need special rules — they decompose into standard Trigger nodes if named correctly:
- Policies and institutions → T2 (e.g., `us_tariffs_on_chinese_goods`, `russian_sanctions_regime`)
- Market aggregates and supply volumes → T3 (e.g., `global_food_grain_supply`, `china_manufacturing_output`)
- Physical infrastructure → T4 (e.g., `global_shipping_routes`)

Events and relationships are NOT entities. `russia_ukraine_conflict` fails Rule 1 — split into the entities it affects. `us_china_trade` fails Rule 1 — split into the policies and volumes involved.

---

### Rule 12: Edge Completeness

Every **lateral** (non-hierarchical) edge must carry ALL of:

| Property | Values | Purpose |
|----------|--------|---------|
| `type` | One of 12 canonical types (see Rule 12b) | What kind of relationship |
| `weight` | 0.0–1.0 | Strength of causal link |
| `polarity` | +1 or -1 | Covariation direction (see Rule 1) |
| `delay` | IMMEDIATE / SHORT_TERM / MEDIUM_TERM / LONG_TERM | Temporal lag |
| `description` | Non-empty string | Human-readable explanation of mechanism |

---

### Rule 12b: Edge Type Semantics

When assigning an edge type, evaluate in this priority order. Pick the **first** that fits:

| Priority | Type | Test | Example |
|----------|------|------|---------|
| 1 | `PRODUCES` | Does A literally create or generate B? | `rooftop_solar` PRODUCES `household_electricity` |
| 2 | `SUPPLIES` | Does A provide physical goods, data, or labor to B? | `wholesale_market` SUPPLIES `retail_tomato` |
| 3 | `FUNDS` | Does A directly pay for or financially back B? | `personal_savings` FUNDS `mutual_fund_portfolio` |
| 4 | `DISRUPTS` | Does A physically or systematically block, break, or halt B? | `urban_flooding` DISRUPTS `daily_commute` |
| 5 | `DEPENDS_ON` | Is B structurally unable to function without A? | `upi_transactions` DEPENDS_ON `mobile_internet` |
| 6 | `REGULATES` | Does A set rules/constraints that B must operate within? (same-world only) | `gst_council` REGULATES `tax_framework` |
| 7 | `MANAGES` | Does A have administrative authority over B? (same-world only) | `ministry_of_finance` MANAGES `union_budget` |
| 8 | `EMPLOYS` | Does A hire/engage B as labor? | `it_company` EMPLOYS `software_engineers` |
| 9 | `COMPETES_WITH` | Does A take market share from B? (unidirectional, see Rule 14) | `swiggy` COMPETES_WITH `zomato` |
| 10 | `AFFECTS` | **Fallback.** A changes the price, frequency, or quality of B. | `retail_diesel` AFFECTS `freight_costs` |

**`AFFECTS` is the fallback, not the default.** If a more specific verb applies, use it. `AFFECTS` should be the minority type in a well-authored graph.

**Cross-world restriction:** `REGULATES` and `MANAGES` must NOT cross the T→I boundary. Administrative relationships across worlds (e.g., `rbi REGULATES credit_card_dues`) are stored as node metadata (`regulated_by`), not graph edges — they short-circuit causal chains.

---

### Rule 13: Edge Conditionality (Optional)

Lateral and bridge edges may include optional **scope conditions** when the causal relationship is not universal:

```yaml
- from: us_immigration_policy
  to: it_sector_jobs
  type: AFFECTS
  conditions:
    demographic: [it_professionals]
    geo_scope: [bangalore, hyderabad, pune]
```

If no conditions are specified, the edge is assumed to apply universally.

---

### Rule 14: Acyclicity Within Layers

Lateral edges within the same world (I→I or T→T) must form a **Directed Acyclic Graph (DAG)**.

No cycles allowed: `healthcare_costs` → `personal_savings` → `mental_health` → `healthcare_costs` is forbidden.

**`COMPETES_WITH` exception:** Competition is inherently bidirectional, which would create 2-node cycles. To preserve DAG: `COMPETES_WITH` edges must be **unidirectional** — model only the dominant competitive direction (market share taker → market share loser). If both directions are equally valid, pick alphabetical order and document. `COMPETES_WITH` edges are excluded from cycle validation.

Validation: run `python -m graph.admin validate-dag` after every edge addition to detect cycles. If a real-world feedback loop exists, model it as two separate unidirectional paths with different delays, not a cycle.

---

### Rule 15: Causal Provenance

Every lateral or bridge edge must include a `description` field (see Rule 12) that explains **the causal mechanism**, not just restates the edge.

- Good: "Diesel price increases raise trucking freight rates, which are passed through to retail food costs"
- Bad: "diesel affects tomato"

This grounds the personalization LLM and prevents hallucinated explanations.

---

### Rule 16: Node Lifecycle

Every node carries a `status` field:

| Status | Meaning | Behavior |
|--------|---------|----------|
| `active` | Live in the graph, used by scoring pipeline | Default for all new nodes |
| `deprecated` | Marked for removal, still resolves in lookups but excluded from new scoring | Set when entity becomes irrelevant |
| `merged` | Subsumed into another node | Must include `merged_into: <target_node_id>`. Lookups redirect to target |

**Temporal conditions** that persist long enough to function as entities are allowed as nodes if they pass the Leaf Node Test (Rule 5). Name them as the **enduring condition**, not the event: `pandemic_movement_restrictions` (not `covid_19_lockdown`), `currency_demonetisation_regime` (not `demonetisation`). When the condition ceases to be relevant, set status to `deprecated`. The node remains in git history and can be reactivated if the condition recurs.

**Mergers** (e.g., `hdfc_ltd` merges into `hdfc_bank`): set the absorbed node to `merged`, update `merged_into`, and transfer all inbound/outbound edges to the target node.

---

### Rule 18: Bridge Targeting (Homogeneity Principle)

> **Rationale:** The original L2→L2 mandate was too coarse — many triggers affect only specific children of an Impact L2, producing false paths when CONTAINS propagation pushes the effect to all siblings. The homogeneity test below lets each bridge target the right level based on causal precision, not a blanket structural rule.

Bridge edges connect Trigger nodes to Impact nodes across worlds.
The target level is determined by the homogeneity of the causal effect:

**(a) HOMOGENEITY TEST:** "Does this trigger affect ALL L3 siblings under
the target L2 with the same mechanism, weight, polarity, and delay?"
- **YES** → target L3 (preferred)
- **NO** → target specific L3s (or L4s if L3 is also heterogeneous)

> **L2 incoming edges are permitted ONLY when ALL L3 children under
> that L2 would be affected by the same source with the same mechanism,
> weight, polarity, and delay.** "Majority" is NOT enough — Phase 3
> downward CONTAINS propagation pushes scores to 100% of children,
> so targeting L2 when only some children are affected creates false
> paths. When in doubt, target individual L3s or L4s.
> For I→I edges, L2 targeting is forbidden (Rule 20).

**(b) SOURCE LEVEL (STRICT):** Causal edges MUST originate from L3 or L4
nodes — the specific mechanism, not the category. L2 nodes are
classifications (groupings of mechanisms), not causal agents.

- `southwest_monsoon` (L4) causes crop disruption, NOT `meteorological_systems` (L2)
- `rbi` (L4) sets repo rates, NOT `financial_regulators` (L3) or `indian_regulatory_bodies` (L2)

**L2 outgoing edges are permitted ONLY when ALL L3/L4 children produce
the SAME effect with the SAME mechanism, weight, polarity, and delay.**
This is rare — most L2s contain children with different causal behaviors.
When in doubt, decompose to L3/L4 sources.

**(c) LEAF BRIDGES:** Permitted when the causal link has unique specificity
not captured at L3 level (e.g., `monetary_policy_committee → home_loan_emi`).
Must not duplicate coverage already provided by an L3 bridge.

**(d) NO UPWARD BRIDGING:** Bridges must not target L1 categories.
If an entire L1 is affected, it should emerge from multiple L2/L3
bridges via upward aggregation, not from a single L1 bridge.

**(e) VALIDATION:** Every new bridge requires:
1. Homogeneity test documented in description
2. At least one positive scenario in `scenarios.yaml`
3. One negative scenario proving it doesn't create false paths

**(f) T→T LATERAL SOURCE LEVEL:** Same rule as (b) — T→T lateral edges
MUST originate from L3 or L4. L2→L2 laterals are forbidden unless ALL
children of the source L2 produce the same effect on ALL children of
the target L2. In practice, this means almost all T→T laterals should
be L3→L3, L3→L4, L4→L3, or L4→L4.

**(g) LLM GENERATION DIRECTIVE:** When generating edges, always default
to L3 or L4 sources and targets. Assume L2 categories are heterogeneous
unless explicitly proven otherwise. **Never use an L2 as a source or
target simply to group things.** If a macro event affects "agriculture",
do not link to the L2 `agriculture_and_allied` — link to the specific
L3s: `crop_yields`, `fertilizer_costs`, `farm_labor`, etc.

**Additional rules (unchanged from prior version):**
- **Cross-world REGULATES/MANAGES are metadata, not edges.** Administrative relationships that cross worlds (e.g., `rbi REGULATES credit_card_dues`) are stored as node properties (`regulated_by`, `managed_by`), not as graph edges. They short-circuit actual causal chains. Same-world REGULATES/MANAGES (e.g., `ministry_of_finance MANAGES union_budget_framework`, both T2) are fine as edges — they represent legitimate institutional relationships within a world.
- **No I→T edges.** The graph is forward-only: Trigger→Impact. See Rule 7.

---

### Rule 20: I→I Lateral Edge Targeting

Impact-to-Impact lateral edges follow the same "Highest Level of Universal Truth"
principle as bridges (Rule 18), with additional constraints:

**(a) NEVER TARGET L2.** Impact L2 nodes are organizational groupings, not causal
entities. An I→I edge to `fresh_produce` (L2) would falsely propagate to all
vegetables, fruits, and produce children. Instead, target the L3 or L4 where
the mechanism actually applies.

**(b) TARGET L3 BY DEFAULT.** Most citizen-level cascades operate at the L3 level.
CONTAINS propagation (Phase 3 of the PPR engine) handles L4 children automatically.

Example: `electricity_tariff` (I2-L4) → `electric_vehicle_charging` (I3-L3).
This correctly propagates to all EV charging children without false paths.

**(c) TARGET L4 ONLY FOR EXCEPTIONS.** When the causal mechanism affects only one
specific child under an L3, bypass the L3 and target the L4 directly.

Example: `monetary_policy_committee` (T2-L4) → `home_loan_emi` (I5-L4).
This is specific because MPC rate changes affect home loans differently than
education loans or gold loans.

**(d) HOMOGENEITY TEST (same as Rule 18a):** Before targeting an L3, verify:
"Does this source affect ALL L4 children under this L3 with the same mechanism,
weight, polarity, and delay?" YES → target L3. NO → decompose to specific L4s.

**(e) SOURCE LEVEL:** The source of an I→I edge follows the same precision rule.
Use the most specific node where the causal mechanism originates.

---

### Rule 21: Direct Causation Principle (No Bypassing)

Every causal edge (T→T, I→I, T→I) must represent a **direct causal mechanism**. You must not draw an edge from A to C if the causal signal must pass through an intermediate node B to get there.

**Trees define structure. Edges define immediate cause.**

#### The Bypassing Test

Before creating an edge A→B, articulate the exact physical, economic, or behavioral mechanism. If your explanation requires a third entity that exists (or should exist) in the taxonomy, your edge is invalid.

- **Invalid (Bypass):** `brent_crude` (T3) → `retail_tomato` (I1). *Mechanism: Crude raises fuel prices, which raises freight costs, which raises tomato prices. Bypasses `vehicle_fuel` and `road_freight_movement`.*
- **Valid (Direct):** `brent_crude` (T3) → `vehicle_fuel` (I3). *Crude price directly sets fuel price.*
- **Valid (Direct):** `vehicle_fuel` (I3) → `road_freight_movement` (T4). *Fuel cost is 40-60% of trucking cost.*
- **Valid (Direct):** `road_freight_movement` (T4) → `retail_tomato` (I1). *Freight cost directly passes to perishable produce.*

This applies uniformly to all edge types:

- **T→I bridges** terminate at the **first point of impact** in I-world. A bridge is valid only if the trigger directly affects the I-world node without requiring signal to pass through any other I-world node first. Multiple bridges per trigger are fine (fan-out) — crude legitimately hits `vehicle_fuel`, `cooking_fuel`, and `lpg_cylinder` independently.
- **T→T laterals** follow the same test within trigger world. `rbi → monetary_policy_committee` is direct (institutional control). `rbi → nifty_50` is not (goes through `repo_rate → fii_fpi_flows`).
- **I→I laterals** follow the same test within impact world. `vehicle_fuel → auto_rickshaw_fare` is direct (cost pass-through). `vehicle_fuel → retail_tomato` is not (needs `road_freight_movement`).

#### The Administrative Exemption

"Direct" means **causally** direct, not **administratively** direct. If an intermediary is merely a passive conduit that cannot independently alter, veto, or scale the effect, skip it.

- **Valid:** `union_budget_framework` (T2) → `mgnrega_wages` (I4). *State governments and panchayats are administrative pass-throughs for this specific budget allocation — they cannot independently change the wage amount.*

#### The Multi-Mechanism Exception (Valid Triangles)

If A affects B, and B affects C, you may ONLY draw an edge from A to C if A has a **completely independent, parallel mechanism** for affecting C that does not involve B.

- **Valid Triangle:** `urban_flooding` → `road_freight_movement` (trucks can't move) AND `urban_flooding` → `retail_tomato` (floodwater directly rots peri-urban crops on the vine). The crop-rot mechanism is independent of the freight mechanism.
- **Requirement:** If you create a triangle, the `description` field of the A→C edge MUST explicitly describe the parallel mechanism.

#### Handling Missing Intermediaries

If A affects C through B, but B does not exist in the taxonomy:

- **DO NOT** draw A→C as a temporary fix. This creates permanent technical debt.
- **DO** propose the addition of Node B (following Rule 5 and Rule 9), then draw A→B and B→C.

#### Automated Validation

- **Triangle Detection:** If the graph contains A→B, B→C, and A→C, flag A→C for manual review. It is only valid if its `description` describes a mechanism independent of B.
- **Cross-World Hop Check:** If a trigger has bridges to two I-world nodes X and Y, and X→Y also exists as a lateral, flag the deeper bridge for review.

Run: `python -m graph.admin validate-directness`

---

### Rule 19: Patch and Edge Addition Protocol

When adding new edges or bridges to the graph:

1. **Check if an existing bridge already covers the path.** Use `python -m graph.traverse <trigger_node>` to trace reachability. If the target is already reached via CONTAINS propagation from an existing bridge (at any level), no new edge is needed.
2. **Apply the Homogeneity Test (Rule 18a/20d) before choosing target level.** Prefer L3 targets. For T→I bridges, L2 is permitted only if the effect is truly universal across ALL descendants (100%) — "majority" is not enough because CONTAINS propagation pushes to all children. For I→I edges, L2 is forbidden (Rule 20). For sources, use L3/L4 per Rule 18(b). If only specific children are affected, target the relevant L3s or L4s.
3. **Same-world laterals: prefer the most specific shared level.** When adding I→I or T→T connections, target the level where the mechanism holds uniformly. For I→I edges, L2 targets are forbidden (Rule 20). L3→L3 or mixed-level laterals are the standard.
4. **No new nodes without justification.** The L2 taxonomy is MECE. Adding a new L2 requires demonstrating that no existing L2 covers the concept. New L3/L4 leaves are fine if they pass the Leaf Node Test (Rule 5).
5. **Every patch needs a scenario.** When adding a bridge to fix a gap, add a corresponding scenario to `taxonomy/scenarios.yaml` that validates the path. Include both a positive scenario (bridge reaches the right target) and a negative scenario (bridge does not create false paths). Patches without test coverage will regress silently.
6. **Run the full validation suite after every patch:**
   ```bash
   python3 -m graph.scenarios               # scenario suite must not regress
   python3 -m graph.admin validate-dag      # no cycles
   python3 -m graph.quality                 # scorecard must not regress
   ```

---

### Rule 17: Phase Transition Validation

At each phase boundary, run these checks before proceeding:

| Transition | Validation | Script |
|------------|-----------|--------|
| **1a → 1b** | No orphan leaves — every leaf has `degree >= 1` lateral edge potential | `graph.admin validate --orphans` |
| **1b → 2a** | Impact subgraph is connected DAG, no isolated components | `graph.admin validate --dag --components` |
| **2a → 2b** | Every Trigger node has a hypothetical path to at least one Impact node ("So What?" test) | Manual review |
| **2b → 3** | Trigger subgraph is connected DAG. **No causal orphans:** every T-world L4 leaf must have at least one causal out-edge, OR its L3 parent must have one. Dead-end triggers cannot propagate signal. | `graph.admin validate --dag --causal-orphans` |
| **3 → 4** | All port nodes have at least one bridge edge | `graph.admin validate --bridges` |
| **Phase 4** | Trace 15+ real scenarios end-to-end, verify traversal reaches expected Impact nodes | Manual + `graph.traverse` |

Do not proceed to the next phase until validation passes.

---

## L1 Categories (LOCKED)

### 5 Trigger L1s (The System Layer)

| ID | Name | Definition | Examples |
|---|---|---|---|
| T1 | Natural & Planetary Systems | Earth-scale biophysical, meteorological, and geological entities operating independently of human institutions | southwest_monsoon, el_nino, himalayan_tectonic_plates, global_surface_temperature |
| T2 | Institutional & Sovereign Entities | State, regulatory, and geopolitical bodies, plus the statutory frameworks and policies they enforce | rbi, gst_council, supreme_court, us_federal_reserve, ministry_of_road_transport |
| T3 | Macroeconomic & Global Markets | Aggregate economic variables, global commodity markets, and international supply chains | brent_crude, nifty_50, usd_inr_exchange, global_semiconductor_supply_chain, wpi |
| T4 | Technological & Physical Infrastructure | Underlying physical grids, foundational technologies, and national-scale infrastructure | national_power_grid, 5g_spectrum, dedicated_freight_corridors, submarine_internet_cables |
| T5 | Social, Demographic & Cultural Forces | Aggregate human populations, mass social movements, and macro-cultural shifts | india_working_age_population, organized_labor_unions, migration_corridors, major_religious_festivals |

#### Trigger Boundary Rules
- T1 vs T2: If created by nature → T1. If created by government → T2.
- T2 vs T3: If driven by legal fiat/state policy → T2. If driven by market forces → T3.
- T3 vs T4: If it's a price/index/supply chain → T3. If it's a physical grid/platform/network → T4.
- T4 vs T5: If it's man-made infrastructure → T4. If it's collective human behavior → T5.
- T1 vs T5: If it's physical earth → T1. If it's human population dynamics → T5.

### 11 Impact L1s (The Citizen Layer)

| ID | Name | Definition | ~Weight | Examples |
|---|---|---|---|---|
| I1 | Food & Nutrition | All consumable food and beverages for household or out-of-home consumption | ~18% | retail_tomato, atta, swiggy_delivery_fees, dairy_milk, poultry |
| I2 | Housing & Utilities | Physical shelter and the direct utilities required to maintain it | ~10% | residential_rent, municipal_water, electricity_tariff, lpg_cylinder, property_maintenance |
| I3 | Transport & Mobility | Entities related to physical movement of the citizen from A to B | ~10% | retail_petrol, metro_fare, road_potholes, ola_uber_pricing, two_wheeler |
| I4 | Livelihood & Employment | Jobs, wages, hiring, gig work — the citizen's earning capacity | ~12% | it_sector_jobs, tcs_salary, gig_worker_payouts, startup_layoffs, minimum_wage |
| I5 | Personal Finance & Wealth | Loans, EMIs, investments, savings, taxation — the citizen's balance sheet | ~12% | home_loan_emi, mutual_fund_portfolio, retail_gold, income_tax, fixed_deposits |
| I6 | Health & Physiology | Physical and mental wellbeing, plus healthcare services consumed | ~8% | dengue, hospital_beds, retail_insulin, therapy_consultation, generic_medicines |
| I7 | Education & Human Capital | Formal/informal learning, credentialing, and skill acquisition | ~6% | school_fees, neet_exam, edtech_subscription, anganwadi, engineering_cutoffs |
| I8 | Safety & Security | Protection against physical harm, crime, and legal jeopardy | ~4% | neighborhood_crime, traffic_accidents, cyber_fraud, police_response_time, fire_hazard |
| I9 | Local Environmental Quality | Immediate physical environment the citizen breathes, feels, and navigates | ~4% | delhi_aqi, ambient_temperature, noise_pollution, urban_flooding |
| I10 | Digital Life & Connectivity | Citizen's interface with the digital world — access, costs, identity | ~6% | upi_transactions, jio_5g_tariff, aadhaar_auth, whatsapp, data_privacy |
| I11 | Leisure, Culture & Community | Discretionary time/spending on entertainment, social connections, civic participation | ~8% | ipl_tickets, netflix_subscription, rwa_rules, cinema_halls, wedding_venue |

#### Impact Boundary Rules
- I1 vs I2: If you eat/drink it → I1. If you live in it → I2.
- I2 vs I3: If stationary (shelter/utilities) → I2. If movement → I3.
- I3 vs I4: Movement of citizen → I3. Earning money → I4.
- I4 vs I5: Earning/employment → I4. Storing/investing/borrowing money → I5.
- I5 vs I6: Balance sheet impact → I5. Acquiring skills/knowledge → I7.
- I6 vs I7: Health of body/mind → I6. Education/learning → I7.
- I7 vs I8: Physical harm/crime → I8. Acquiring skills → I7.
- I8 vs I9: Physical safety threats → I8. Air/water/noise quality → I9.
- I9 vs I10: Environmental quality → I9. Digital services → I10.
- I10 vs I11: Digital/connectivity → I10. Entertainment/social/community → I11.
- I1 vs I5: If it's food you pay for → both involved; the food entity is I1, the payment mechanism is I5.

---

## Stress Test Results

| Entity | Classification | L1 |
|---|---|---|
| crude_oil | Trigger | T3: Macro & Global Markets |
| diesel | Impact | I3: Transport & Mobility |
| delhi_air_quality | Impact | I9: Local Environmental Quality |
| southwest_monsoon | Trigger | T1: Natural & Planetary |
| rbi_repo_rate | Trigger | T2: Institutional & Sovereign |
| home_loan | Impact | I5: Personal Finance & Wealth |
| bmrcl_metro | Trigger | T4: Tech & Physical Infrastructure |
| tomato | Impact | I1: Food & Nutrition |
| indian_it_industry (sector aggregate) | Trigger | T3: Macro & Global Markets |
| it_sector_salary | Impact | I4: Livelihood & Employment |
| upi (protocol) | Trigger | T4: Tech & Physical Infrastructure |
| upi_transaction | Impact | I10: Digital Life & Connectivity |
| hospital_beds | Impact | I6: Health & Physiology |
| school_fees | Impact | I7: Education & Human Capital |
| gold | Impact | I5: Personal Finance & Wealth |
| bangalore_traffic | Impact | I3: Transport & Mobility |
| gst | Trigger | T2: Institutional & Sovereign |
| farmer_unions | Trigger | T5: Social, Demographic & Cultural |
| autumn_festive_season | Trigger | T5: Social, Demographic & Cultural |
| netflix_subscription | Impact | I11: Leisure, Culture & Community |

---

## Example Causal Chains

### Chain 1: Inflation Cascade (Macro → Plate)
```
[T3] brent_crude → [T2] oil_marketing_companies → [I3] retail_diesel →
[I3] freight_cost → [I1] retail_tomato → [I5] savings_account_balance
```

### Chain 2: Climate-Health Nexus (Planet → Lungs)
```
[T1] post_monsoon_wind_patterns → [T1] agricultural_stubble_biomass →
[I9] ambient_aqi → [I6] hospital_beds → [I6] generic_medicines
```

### Chain 3: Digital Infrastructure Shock (Regulation → Wallet)
```
[T2] rbi → [T4] paytm_payments_bank →
[I10] fastag_wallet → [I3] toll_plaza → [I4] gig_worker_payouts
```

---

## Personalization Model

User Profile: `city=bangalore, job=IT, diet=non_veg, loans=home_loan, investments=mutual_funds`

When "US Fed cuts rates by 50bps" happens:
- **I5 (Finance):** NIFTY rises → mutual fund portfolio up. "Your SIP likely sees 2-3% bump."
- **I4 (Livelihood):** US tech budgets expand → IT hiring improves. "Better appraisal conditions next quarter."
- **I5 (Finance):** RBI may follow → home loan EMI drops. "Your ₹50k EMI could decrease."
- **I1 (Food):** Global wheat prices dip slightly → suppressed, low relevance for this user.

---

## Scoring Algorithm: Multi-Phase Activation (PPR)

The scoring engine uses Personalized PageRank with a 3-phase activation model
to trace how a trigger event propagates through the graph to citizen-level impacts.

### Phase 1: Upward Seed Expansion (Pre-PPR)

When a trigger node fires (e.g., `brent_crude`), walk UP the CONTAINS hierarchy
with exponential decay to build a multi-seed vector:

```
{brent_crude: 0.67, energy_commodities: 0.33}  (normalized, decay=0.5)
```

- Only ancestors with causal out-edges in the causal subgraph are included
- Config: `upward_seed_decay=0.5`, `max_seed_levels=3`
- **Rationale:** If a news event triggers an L4 leaf (e.g., `hdfc_bank`),
  upward expansion ensures that category-level bridges attached to its
  L3 parent (`private_banks`) are still activated by the PPR walk

### Phase 2: Pure Causal Walk (PPR)

Run NetworkX `pagerank()` on the causal subgraph (CONTAINS/IS_A edges stripped):

- `personalization` = seed vector from Phase 1
- `dangling` = seed vector (dangling nodes restart at seed distribution)
- `alpha` = 1 - restart_prob (default restart_prob=0.20)
- Nodes below `prob_threshold` (default 0.005) are discarded

The causal subgraph only contains the 10 causal edge types:
AFFECTS, PRODUCES, REGULATES, DISRUPTS, SUPPLIES, DEPENDS_ON,
FUNDS, COMPETES_WITH, EMPLOYS, MANAGES.

### Phase 3: Downward CONTAINS Propagation (Post-PPR)

For each category node reached by PPR, propagate scores down through
CONTAINS edges to leaf children:

```
child_score = MAX(direct_ppr_score, parent_score × contains_weight)
```

MAX semantics ensure that if a leaf was directly reached by PPR with a
higher score than what propagation would give, the direct score wins.

### 3-Layer Scoring

Each reached node gets three scores computed along its dominant path
(shortest path on -log(P) costs):

| Layer | Metric | How | Range |
|-------|--------|-----|-------|
| **Probability** | PPR steady-state | PageRank output | 0.0–1.0 |
| **Magnitude** | Hub-penalized path product | ∏(weight × hub_penalty) along path | 0.0–1.0 |
| **Timing** | Delay sum | Σ(delay_rank) along path → label | IMMEDIATE–LONG_TERM |

Hub penalty: `1 / log2(out_degree + 1)` for nodes with out_degree > 1.
Polarity: ∏(edge_polarity) along path × event_direction.

**Polarity example:** News headline "Monsoon deficit this year" →
`southwest_monsoon` fires with event_direction = **-1** (decrease).
Edge: monsoon → crop_yield has polarity **+1** (more monsoon = more yield).
Final polarity on crop_yield: (-1) × (+1) = **-1** → crop yield decreases. Correct.

### Config Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `ppr_restart_prob` | 0.20 | PPR restart probability (α) |
| `ppr_prob_threshold` | 0.005 | Min probability to include a node |
| `upward_seed_decay` | 0.5 | Decay per CONTAINS level in seed expansion |
| `max_seed_levels` | 3 | Max levels to walk up for seeding |

---

## Research Context

### Frameworks Referenced
- **OECD Better Life Index** — 11 dimensions (Material + Quality of Life). Closest prior art.
- **COICOP 2018** — 13 divisions of household consumption. Pure spending taxonomy.
- **Social Progress Index** — 12 components across Basic Needs, Foundations, Opportunity.
- **UNDP MPI** — 3 dimensions: Health, Education, Living Standards.
- **EU Social Taxonomy** — Workers, Consumers, Communities stakeholder split.
- **FinCaKG** — Financial causality knowledge graph (academic). Causal chains from text.

### Key Finding
No existing product or framework combines causal chain modeling with citizen-centric impact taxonomy. This is genuinely novel.

---

## North Star Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| Impact leaf nodes | 400-500 | ~35-50 per L1 at L3/L4 depth |
| Trigger leaf nodes | 150-200 | Domestic institutions + geopolitical entities with ≤4 hop paths |
| Total nodes (incl. categories) | 700-850 | Leaves + L2/L3 categories + 16 L1s |
| Lateral edges per leaf | 3-5 avg | Meaningfully connected, not over-wired |
| Dead-end ratio | < 5% | Almost every node in a causal chain |
| Orphan nodes | 0 | No disconnected nodes |
| Connected components (after Phase 3) | 1 | Entire graph reachable |
| Edge description coverage | 100% | Rule 15 — provenance on every causal edge |
| Persona coverage | > 40% reachable | Each test persona reaches a meaningful graph portion |
| Cycles within layers | 0 | Rule 14 DAG enforcement |
| Port nodes with ≥1 bridge | 100% | No dead ports after Phase 3 |
| Duplicate nodes across files | 0 | Rule 4 enforcement |

---

## Build Phases

| Phase | What | Edge Types | Output |
|-------|------|------------|--------|
| **1a** | Impact vertical trees (L1→L2→L3) | CONTAINS, IS_A only | 11 Impact tree structures |
| **1b** | Impact lateral edges (intra-tree + portals) | AFFECTS, DISRUPTS, SUPPLIES, etc. | Connected Impact subgraph |
| **2a** | Trigger vertical trees | CONTAINS, IS_A only | 5 Trigger tree structures |
| **2b** | Trigger lateral edges (intra-tree + portals) | AFFECTS, DISRUPTS, SUPPLIES, etc. | Connected Trigger subgraph |
| **3** | Bridge edges (T→I only) | Any lateral type | Full connected graph |
| **4** | End-to-end validation | — | 15+ traced scenarios, gap-fill |

Within each phase: build nodes → tag ports/portals → add edges → validate (Rule 17 checks at each boundary).
