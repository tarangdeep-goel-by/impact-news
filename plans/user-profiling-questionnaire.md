# User Profiling Questionnaire: Design Spec

## Context

Impact News classifies articles into 160 I-world leaf nodes (8 categories). We need a questionnaire that maps each user to the leaf nodes that affect them, enabling rule-based matching: `user_weights * article_impacts → relevance_score`. Progressive disclosure: show value early, ask more later.

**Active taxonomy:** New I-world (I1-I8, 160 leaves) from `taxonomy/I*-new.yaml`. Old taxonomy (I1-I11, 532 nodes) to be removed from merged_graph.yaml.

---

## 1. Progressive Disclosure Segments

| Segment | Questions | Covers | Trigger |
|---------|-----------|--------|---------|
| **0: Essentials** | 5 | City + Work + Transport + Housing + Dependents → I1, I2 (partial), I3 | On first `/start` |
| **1: Household** | 6 | Cooking + Diet + Health + Insurance + Digital + Travel → I2 (food/energy), I4, I8 (digital) | After 3+ delivered stories AND 1 feedback |
| **2: Fine-tuning** | 5 | Govt services + Safety + Environment + Recreation + Movements → I6, I7, I8 (leisure) | After 7 days OR event hits unresolved node |

~16 questions total across all segments. Segment 0 alone activates ~60 of 160 nodes.

---

## 2. Universal Nodes (Always ON, no question needed)

17 nodes activated at weight 1.0 for every user:

**I2 Cost of Living:** `staple_grains`, `pulses_and_dals`, `dairy_and_eggs`, `edible_oils`, `spices_sugar_salt`, `electricity_tariff`, `lpg_cylinder`
**I3 Mobility:** `road_conditions_and_closures`
**I4 Health:** `hospital_and_medical_care`, `medicines_and_pharmaceuticals`, `respiratory_and_viral_infections`
**I6 Civic:** `identity_and_travel_documents`, `indirect_taxes_gst`
**I7 Habitat:** `air_pollution`, `extreme_heat`
**I8 Digital:** `mobile_tariffs`, `spam_and_scams`

Universal floor rule: question answers cannot suppress universals below weight 0.5.

---

## 3. City-Tier Auto-Inference

City answer (s0_city) → tier lookup → additional nodes activated:

**Metro** (Mumbai, Delhi, Bangalore, Chennai, Hyderabad, Kolkata, Pune, Ahmedabad):
`traffic_congestion:0.8`, `metro_and_local_train:0.7`, `ride_hailing_cabs_bikes:0.7`, `food_delivery_services:0.6`, `parking_fees:0.5`, `residential_rent_and_pg:0.7`, `broadband_and_wifi:0.6`
+ Seasonal: `winter_smog:0.8` for Delhi NCR/Lucknow/Patna (Oct-Feb)

**Tier 2** (Jaipur, Lucknow, Kochi, Indore, etc.):
`auto_e_rickshaw:0.7`, `city_bus_transit:0.6`, `street_waterlogging:0.5`, `road_conditions_and_closures:0.7`

**Rural:**
`farm_labor_wages:0.5`, `mgnrega_wages:0.5`, `water_supply_and_tankers:0.7`, `drinking_water_contamination:0.6`, `welfare_and_ration_cards:0.7`, `piped_natural_gas:0.0` (override: unavailable)

Gemini task: generate full city-tier mapping for top 200 Indian cities + seasonal env flags.

---

## 4. Question Schema

Each question defined in YAML:

```yaml
- id: s0_work
  segment: 0
  text: "What best describes your work?"
  type: single_choice          # single_choice | multi_choice | autocomplete
  max_selections: 1            # for multi_choice
  telegram_ux: inline_keyboard # inline_keyboard | inline_keyboard_multi | text_input
  options:
    - label: "Private company job"
      value: corporate
      activations:
        corporate_salaries: 1.0
        corporate_hiring_and_layoffs: 0.9
        personal_income_tax: 0.8
        tds_and_compliance: 0.6
        professional_upskilling: 0.5
    - label: "Gig work (delivery/driving)"
      value: gig
      activations:
        food_and_grocery_delivery_payouts: 0.8
        ride_hailing_earnings: 0.8
        petrol_price: 0.9
        statutory_minimum_wage: 0.7
    # ... more options
```

### Segment 0: Essentials

| Q | Text | Type | Options (brief) | Key activations |
|---|------|------|-----------------|-----------------|
| s0_city | Which city? | autocomplete | free text → tier lookup | ~6-8 city-tier nodes |
| s0_work | What describes your work? | single | corporate/govt/freelance/business/gig/labor/farming/student/homemaker/retired | I1 entire subtree (22 nodes) |
| s0_transport | How do you get around? | multi(2) | petrol/diesel/CNG/EV/metro/bus/auto/cab/walk | I3 subtree (fuel + transit) |
| s0_housing | Housing situation? | single | rent/own-loan/own-free/hostel/family | I2 housing L2 |
| s0_family | Who depends on you? | multi(4) | kids-school/kids-college/toddlers/elderly/none | I5 education + I4 health subset |

### Segment 1: Household

| Q | Text | Type | Options (brief) | Key activations |
|---|------|------|-----------------|-----------------|
| s1_cooking | How do you cook? | single | LPG/piped gas/electric/chulha | I2 energy L2 |
| s1_diet | Household diet? | single | veg/non-veg/mostly outside | I2 groceries filtering |
| s1_health | Family health concerns? | multi(3) | chronic/respiratory/maternity/mental/none | I4 subtrees |
| s1_insurance | Which insurance? | multi(3) | health/vehicle/life/none | I2 insurance L2 |
| s1_digital | What do you do online? | multi(3) | social/OTT/gaming/news/work-tools | I8 digital/entertainment |
| s1_intercity | How often intercity travel? | single | weekly/monthly/occasional/rare | I3 intercity L2 |

### Segment 2: Fine-tuning

| Q | Text | Type | Options (brief) | Key activations |
|---|------|------|-----------------|-----------------|
| s2_govt | Govt services you deal with? | multi(4) | tax/passport/RTO/ration/property/legal | I6 subtrees |
| s2_safety | Local safety concerns? | multi(3) | crime/women-safety/flooding/strays/noise/none | I4 crime + I7 water |
| s2_environment | Environment issues in your area? | multi(3) | water/garbage/greenery/river/mosquitoes/none | I7 subtrees |
| s2_recreation | What do you do for fun? | multi(3) | sports/movies/concerts/gym/religious/parks | I8 leisure subtrees |
| s2_movements | Which movements affect you? | multi(2) | labor/farmer/reservation/student/none | I6 civic movements |

---

## 5. Weight Composition

```python
def compute_user_weight(node_id, sources):
    """MAX wins, not additive. Universal floor = 0.5."""
    weights = [s.weight for s in sources]
    raw = max(weights) if weights else 0.0

    if node_id in UNIVERSAL_NODES:
        return max(raw, 0.5)

    return raw
```

- Multiple questions activating same node → take MAX weight
- Explicit 0.0 from a question = suppression (overrides city-tier, not universals)
- Profile recomputed on each new answer (idempotent)

---

## 6. Matching Algorithm

```python
def score_article_for_user(article_impacts, user_weights):
    """
    article_impacts: list[MicroImpact] (post confidence_filter)
    user_weights: dict[str, float]  (node_id -> 0.0-1.0)
    """
    scores = []
    for impact in article_impacts:
        user_w = user_weights.get(impact["i_node"], 0.0)
        if user_w > 0:
            impact_score = impact["probability"] * impact["magnitude"]
            scores.append(impact_score * user_w)

    if not scores:
        return 0.0

    # Top-3 personal scores, normalized
    scores.sort(reverse=True)
    raw = sum(scores[:3])
    return min(raw / 2.0, 1.0)
```

**Delivery tiers:** score >= 0.5 → push, >= 0.2 → daily digest, else → weekly/skip

**Pipeline integration:**
```
Article → LLM → MicroImpacts → confidence_filter → user_matcher → delivery_tier → Telegram
```

---

## 7. Data Model

### New table: `user_profiles`

```sql
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    telegram_chat_id TEXT UNIQUE NOT NULL,
    city TEXT,
    city_tier TEXT,                -- metro/tier2/rural
    raw_answers_json TEXT,         -- {"s0_work": "corporate", "s0_transport": ["petrol_vehicle", "metro"]}
    node_weights_json TEXT,        -- {"petrol_price": 1.0, "corporate_salaries": 1.0, ...}
    completed_segments TEXT,       -- ["segment_0"]
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
```

Existing `UserGraph`/`UserEdge` models in `models.py` can be extended or replaced.

---

## 8. Gemini 3.1 Pro Tasks (one-time generation, not runtime)

1. **Validate mappings:** Send full question schema + 160 leaf taxonomy → find missing activations, wrong weights, unreachable nodes
2. **City-tier mapping:** Top 200 Indian cities → metro/tier2/rural + seasonal env flags
3. **Persona testing:** 20 synthetic personas → simulate answers → verify node weight output makes sense
4. **Gap analysis:** Which of 160 leaves are never reached by any segment? Should they be universal or event-triggered?

---

## 9. Implementation Phases

### Phase 1: Schema + Engine
- `profiling/questions/segment_0.yaml`, `segment_1.yaml`, `segment_2.yaml`
- `profiling/universals.py` — universal nodes, city-tier mappings
- `profiling/engine.py` — `ProfileEngine`: process answers, compute weights, get next question
- `profiling/schema.py` — YAML question loader + validation
- Add `user_profiles` table to `pipeline/database.py`

### Phase 2: Matching Layer
- `profiling/matcher.py` — `score_article_for_user()`
- Wire into `confidence_filter.py` → matcher → delivery tier

### Phase 3: Telegram Bot
- `/start` → Segment 0 conversation flow
- Inline keyboard handlers for answers
- Segment unlock logic (story count, feedback, days)
- Delivery pipeline uses per-user matching

### Phase 4: Gemini Validation
- Run 3 Gemini tasks above
- Adjust weights, add missing activations
- Test with real pipeline output

### Key files to modify
- `pipeline/database.py` — add user_profiles table
- `bot/bot.py` — add questionnaire conversation handler
- `engine/confidence_filter.py` — integration point for user matching
- `models.py` — extend or replace UserGraph

### Prerequisite
- Rebuild `data/merged_graph.yaml` from new I*-new.yaml files (remove old I1-I11.yaml)
- Run `python -m graph.merge` with new files
- Update `engine/taxonomy_context.py` if category codes changed (I1-I8 vs I1-I11)

---

## 10. Coverage Estimate

| Source | Nodes | % of 160 |
|--------|-------|----------|
| Universal (always ON) | 17 | 11% |
| City-tier auto-inference | ~8-12 | ~6% |
| Segment 0 (5 questions) | ~40-60 | ~31% |
| Segment 1 (6 questions) | ~25-35 | ~19% |
| Segment 2 (5 questions) | ~25-35 | ~19% |
| **Total reachable** | **~130-145** | **~85%** |

Remaining ~15-20 nodes: niche (PhD, crowd_stampedes, railway_accidents) → activated by event-driven profiling or added to universals.
