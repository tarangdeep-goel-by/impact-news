# Taxonomy v4 — Impact News Knowledge Graph

## Status: CONSTITUTION LOCKED (2026-03-13). L1s LOCKED. L2s pending.

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
| **Bridge** | Trigger node → Impact node | `crude_oil` (T3) → `retail_diesel` (I3) | Phase 3 |
| **Feedback** | Impact node → Trigger node | `retail_inflation` (I5) → `rbi` (T2) | Phase 3 |

Portal edges can connect nodes at **any level** — an L3 in one tree can link to an L2 in another. Causal links don't respect taxonomy depth.

**Feedback edges** model how citizen-level outcomes influence system-level entities. Citizens are not purely passive receivers — widespread inflation triggers central bank action, unemployment triggers protest movements, health crises trigger regulatory responses. Feedback edges always carry a longer `delay` (typically MEDIUM_TERM or LONG_TERM) since systemic responses lag citizen impact.

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
| `type` | One of 12 canonical types | What kind of relationship |
| `weight` | 0.0–1.0 | Strength of causal link |
| `polarity` | +1 or -1 | Covariation direction (see Rule 1) |
| `delay` | IMMEDIATE / SHORT_TERM / MEDIUM_TERM / LONG_TERM | Temporal lag |
| `description` | Non-empty string | Human-readable explanation of mechanism |

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

Validation: run `python -m graph.admin validate` after every edge addition to detect cycles. If a real-world feedback loop exists, model it as two separate unidirectional paths with different delays, not a cycle.

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

**Temporal entities** (e.g., `covid_19_lockdown`, `demonetisation`) are allowed as nodes if they pass the Leaf Node Test (Rule 5). When the entity ceases to be relevant, set status to `deprecated`. The node remains in git history and can be reactivated if the entity recurs.

**Mergers** (e.g., `hdfc_ltd` merges into `hdfc_bank`): set the absorbed node to `merged`, update `merged_into`, and transfer all inbound/outbound edges to the target node.

---

### Rule 17: Phase Transition Validation

At each phase boundary, run these checks before proceeding:

| Transition | Validation | Script |
|------------|-----------|--------|
| **1a → 1b** | No orphan leaves — every leaf has `degree >= 1` lateral edge potential | `graph.admin validate --orphans` |
| **1b → 2a** | Impact subgraph is connected DAG, no isolated components | `graph.admin validate --dag --components` |
| **2a → 2b** | Every Trigger node has a hypothetical path to at least one Impact node ("So What?" test) | Manual review |
| **2b → 3** | Trigger subgraph is connected DAG | `graph.admin validate --dag` |
| **3 → 4** | All port nodes have at least one bridge edge, all feedback edges have delay >= MEDIUM_TERM | `graph.admin validate --bridges` |
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
| tcs (corporation) | Trigger | T3: Macro & Global Markets |
| tcs_salary | Impact | I4: Livelihood & Employment |
| upi (protocol) | Trigger | T4: Tech & Physical Infrastructure |
| upi_transaction | Impact | I10: Digital Life & Connectivity |
| hospital_beds | Impact | I6: Health & Physiology |
| school_fees | Impact | I7: Education & Human Capital |
| gold | Impact | I5: Personal Finance & Wealth |
| bangalore_traffic | Impact | I3: Transport & Mobility |
| gst | Trigger | T2: Institutional & Sovereign |
| farmer_protest | Trigger | T5: Social, Demographic & Cultural |
| diwali_festival | Trigger | T5: Social, Demographic & Cultural |
| netflix_subscription | Impact | I11: Leisure, Culture & Community |

---

## Example Causal Chains

### Chain 1: Inflation Cascade (Macro → Plate)
```
[T3] Brent Crude → [T2] Oil Marketing Policy → [I3] Retail Diesel →
[I3] Trucking Freight → [I1] Retail Tomato Price → [I5] Household Savings
```

### Chain 2: Climate-Health Nexus (Planet → Lungs)
```
[T1] Post-Monsoon Winds → [T3] Punjab Stubble Burning →
[I9] Delhi AQI → [I6] Pediatric Asthma → [I6] Inhaler Demand
```

### Chain 3: Digital Infrastructure Shock (Regulation → Wallet)
```
[T2] RBI Regulatory Action → [T4] Paytm Payments Bank →
[I10] FASTag Wallet → [I3] Toll Plaza Wait Times → [I4] Gig Worker Earnings
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
| Impact leaf nodes | 150-180 | ~15-20 per L1, enough to cover Indian life without bloat |
| Trigger leaf nodes | 70-100 | Domestic institutions + geopolitical entities with ≤4 hop paths |
| Total nodes (with L2 categories) | 300-350 | Leaves + ~85 L2s + 16 L1s |
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
| **3** | Bridge + Feedback edges (T→I and I→T) | Any lateral type | Full connected graph |
| **4** | End-to-end validation | — | 15+ traced scenarios, gap-fill |

Within each phase: build nodes → tag ports/portals → add edges → validate (Rule 17 checks at each boundary).
