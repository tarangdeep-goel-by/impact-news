# Plan: Taxonomy Restructure — Goal-Driven, Gemini-Reasoned

## The Product Goal

Impact News tells Indian citizens: "Not what interests you. What affects you."

Given any news article, the system answers:
1. **What shifted in the world?** (MacroShift — T-world)
2. **How does it affect your life?** (MicroImpact — I-world)

## Agreed L1 Framework

### T-world: 7 L1s (MacroShifts — "What shifted")

Every node must work with: "[node] is escalating / deescalating / status_quo / disruption"

| # | L1 | Flow | Rationale |
|---|-----|------|-----------|
| T1 | Macroeconomic & Financial Markets | Money | Interest rates, inflation, currency, commodities, equity markets |
| T2 | Domestic Governance & Policy | Rules (internal) | Tax, welfare, judiciary, RBI/SEBI regulation, election policy |
| T3 | Geopolitical & External Forces | Shocks (external) | Trade embargoes, border tensions, visa regimes, foreign elections |
| T4 | Physical Infrastructure & Logistics | Atoms | Rail, ports, power grids, highways, supply chains |
| T5 | Digital & Tech Infrastructure | Bytes | UPI, Aadhaar, telecom, AI platforms — instant, pan-national |
| T6 | Social & Demographic Systems | Human capital | Labor markets, migration, communal dynamics, festivals |
| T7 | Ecological & Planetary Systems | Nature | Monsoon, seismic, pandemics, climate, water systems |

Split rationale: Separate by **speed and source**. Geopolitics = exogenous/sudden. Domestic policy = endogenous/planned. Digital = instant/pan-national. Physical = slow/geographic.

### I-world: 8 L1s (MicroImpacts — "How it affects you")

Every node must pass: "Can a citizen point to this in their wallet, body, schedule, or environment?"

| # | L1 | Test | Replaces |
|---|-----|------|----------|
| I1 | Income & Livelihood | Money IN | Old I4 (Employment) |
| I2 | Cost of Living | Money OUT | Old I1 (Food) + I2 (Housing) + parts of I5 |
| I3 | Mobility & Transport | Getting around | Old I3 |
| I4 | Health & Bodily Safety | Staying safe | Old I6 (Health) + I8 (Safety) |
| I5 | Education & Skilling | Moving up | Old I7 |
| I6 | Civic & Legal Friction | State interactions | Parts of old I5 (taxes) + new |
| I7 | Habitat & Surroundings | Local environment | Old I9 + I2 (utilities) |
| I8 | Digital & Leisure | Downtime | Old I10 + I11 |

### I-tree Architecture: Prompt Taxonomy + Enum Matrix

Instead of 500+ leaf nodes, use ~150-200 L3 nodes with enum parameters:
```json
{"node": "fuel_costs", "valid_enums": ["petrol", "diesel", "cng", "lpg", "ev_charging"]}
```
Backend concatenates to canonical ID: `cost_of_living.fuel_costs.petrol`

## Process: Phase by Phase

### Phase 1: L1 Framework — DONE
Agreed: 7 T-world L1s, 8 I-world L1s

### Phase 2: T-tree L1 by L1 deep dive with Gemini
Order: T7 (Ecological) → T1 (Macro) → T4 (Physical) → T5 (Digital) → T6 (Social) → T3 (Geopolitical) → T2 (Domestic Policy)

For each: provide current YAML, ask Gemini to reason about what L2/L3 nodes serve the goal.

### Phase 3: I-tree L1 by L1 deep dive with Gemini
Order: I2 (Cost of Living, biggest) → I1 (Income) → I3 (Mobility) → I4 (Health) → I5 (Education) → I6 (Civic) → I7 (Habitat) → I8 (Digital/Leisure)

### Phase 4: Bridge test — 20 Indian news scenarios through T→I chains
### Phase 5: Migration table + eval update
### Phase 6: Rebuild + regression eval (F1 >= 89%)

## Key Files
- `taxonomy/T1-T5.yaml`, `taxonomy/I1-I11.yaml` — source YAMLs
- `graph/merge.py` — rebuilds `data/merged_graph.yaml`
- `engine/taxonomy_context.py` — formats trees for LLM prompts
- `tests/eval/tier1_cases.json` — 190 eval cases with ground truth
