# Adaptive User Profiling: Feedback-Driven Personalization Loop

## Context

The static questionnaire (segment 0/1/2) gives L1-depth profiling — "corporate worker" vs "farmer" — but can't distinguish a Bangalore PM at a fintech startup from a TCS developer in Pune. Both match `corporate_hiring_and_layoffs`, but only one cares about IT-sector layoffs.

Second problem: location-scoped impacts (Mumbai traffic, Delhi smog) currently hit all users because the LLM doesn't tag geographic scope on micro-impacts.

**Goal:** Hyper-personalized matching through a feedback-driven loop where articles are the questionnaire and feedback is the answer. Progressive disclosure: deliver value at L1, deepen on feedback.

---

## 1. The Three Learning Channels

### Channel A: Direct Intake (what we have now)
5 onboarding questions → ~40 nodes at L1 weights. Unchanged.

### Channel B: Feedback-Driven Depth (NEW — core innovation)
When user marks an article irrelevant that matched their L1 profile:
→ Ask a diagnostic question: "Why wasn't this relevant?"
→ Each diagnostic answer refines the profile deeper

When user marks an article relevant that matched weakly:
→ Ask a deepening question to strengthen the match
→ "Since you care about hiring trends, are you in IT specifically?"

### Channel C: Behavioral Inference (NEW — passive)
- Articles consistently ignored → decay weights on matched nodes
- Articles opened (clicked through) → boost matched nodes
- Feedback ratio per category → adjust category-level confidence

---

## 2. Location Scoping (T2 Prompt Change)

### Problem
LLM outputs `traffic_congestion: 0.95` without saying "in Mumbai". Bangalore user gets push for Mumbai traffic.

### Fix: Add `scope` field to micro-impact schema

T2 prompt addition:
```
For each micro-impact, include a "scope" field:
- "national" — affects all of India (e.g., petrol price hike, income tax change)
- "state:<name>" — affects one state (e.g., electricity tariff in Karnataka)
- "city:<name>" — affects one city (e.g., traffic diversion in Mumbai)
- "regional:<area>" — affects a region (e.g., Indo-Gangetic smog)
```

MicroImpact TypedDict update:
```python
class MicroImpact(TypedDict, total=False):
    i_node: str
    probability: float
    magnitude: float
    trajectory: str
    rationale: str
    driving_t_nodes: list[str]
    scope: str  # NEW: "national" | "state:Karnataka" | "city:Mumbai"
```

Matcher filter:
```python
def is_location_relevant(scope: str, user_city: str, user_state: str) -> bool:
    if not scope or scope == "national":
        return True
    if scope.startswith("city:"):
        return scope.split(":")[1].lower() == user_city.lower()
    if scope.startswith("state:"):
        return scope.split(":")[1].lower() == user_state.lower()
    return True  # unknown = assume relevant
```

### Which nodes are location-sensitive?

**City-specific** (MUST have city scope to match):
`traffic_congestion`, `road_conditions_and_closures`, `metro_and_local_train`, `city_bus_transit`, `auto_e_rickshaw`, `street_waterlogging`, `drinking_water_contamination`, `water_supply_and_tankers`, `uncollected_street_garbage`, `open_drains_and_sewage`, `riots_and_mob_violence`, `curfews_and_public_emergencies`, `crowd_stampedes`, `residential_rent_and_pg`

**State-specific:**
`electricity_tariff` (state discom), `government_schools` (state board), `school_board_exams` (state boards), `welfare_and_ration_cards`, `state_govt_jobs`

**Always national:**
`petrol_price`, `diesel_price`, `lpg_cylinder`, `personal_income_tax`, `indirect_taxes_gst`, `corporate_salaries`, `corporate_hiring_and_layoffs`, all food commodity nodes

---

## 3. Full User Knowledge Map (what we need to know)

### Per I-world category:

**I1: Income & Livelihood**
| Layer | Question | Depth | Trigger |
|-------|----------|-------|---------|
| L0 | Employment type | corporate/gig/farming/etc | Intake |
| L1 | Industry | IT/Fintech/BFSI/Manufacturing/Healthcare/Retail | Feedback: "not my industry" |
| L1 | Company type | Startup/Growth/MNC/PSU/Family | Feedback: "my job is stable" |
| L1 | Role level | IC/Manager/Founder | Feedback: "I'm a founder, not employee" |
| L2 | Income band | <5L/5-15L/15-30L/30L+ | Feedback on tax/investment articles |
| L2 | Spouse employment | Working/Homemaker/sector | Behavioral: dual-income signals |

**I2: Cost of Living**
| Layer | Question | Depth | Trigger |
|-------|----------|-------|---------|
| L0 | Housing type | rent/own/PG | Intake |
| L0 | Diet | veg/nonveg/outside | Segment 1 |
| L1 | Cooking oil type | mustard/sunflower/coconut/refined | Feedback: "I don't use this oil" |
| L1 | Grocery source | kirana/supermarket/online | Feedback: "prices don't match my experience" |
| L1 | Rent band | <10K/10-25K/25-50K/50K+ | Feedback on rent articles |
| L1 | Loan types | home/car/education/personal/none | Segment 1.5 or feedback |
| L1 | Investment types | MF/FD/gold/crypto/PPF/NPS | Segment 1.5 or feedback |

**I3: Mobility & Transport**
| Layer | Question | Depth | Trigger |
|-------|----------|-------|---------|
| L0 | Primary mode | petrol/diesel/metro/bus/cab | Intake |
| L1 | 2W vs 4W | bike/scooter vs car/SUV | Feedback: vehicle-specific article |
| L1 | Commute distance | <5km/5-20km/20km+ | Feedback: "tolls don't affect me" |
| L1 | Intercity mode | train/flight/bus/drive | Segment 1 |
| L2 | Specific corridor | which route | Behavioral (too granular for questions) |

**I4: Health & Bodily Safety**
| Layer | Question | Depth | Trigger |
|-------|----------|-------|---------|
| L0 | Health concerns | chronic/respiratory/maternity/mental/none | Segment 1 |
| L1 | Specific conditions | diabetes/BP/thyroid/cancer | Feedback: "we have diabetes, not BP" |
| L1 | Hospital type | govt/private/CGHS/Ayushman | Feedback: "govt hospital news irrelevant" |
| L1 | Gender context | women in household? | Feedback on women's safety articles |
| L2 | Specific medications | insulin/inhalers/etc | Behavioral (pharma article opens) |

**I5: Education & Skilling**
| Layer | Question | Depth | Trigger |
|-------|----------|-------|---------|
| L0 | Education stage | kids-school/kids-college/student/none | Intake |
| L1 | Board | CBSE/ICSE/State/International | Feedback: "not my board" |
| L1 | School type | govt/private/budget-private | Feedback on fee articles |
| L1 | Exam track | JEE/NEET/UPSC/SSC/CAT | Feedback: "not my exam" |
| L2 | Specific institution type | engineering/medical/law/arts | Feedback on specific college news |

**I6: Civic & Legal Friction**
| Layer | Question | Depth | Trigger |
|-------|----------|-------|---------|
| L0 | Govt services | tax/passport/RTO/ration | Segment 2 |
| L1 | Tax regime | old/new | Feedback on budget/tax articles |
| L1 | Property owner | yes/no + disputes | Feedback on RERA/property articles |
| L1 | Business licenses | FSSAI/shops/none | Feedback on compliance articles |
| L2 | Specific legal | FIR/court case/RTI | Behavioral (rarely asked directly) |

**I7: Habitat & Surroundings**
| Layer | Question | Depth | Trigger |
|-------|----------|-------|---------|
| L0 | City + tier | metro/tier2/rural | Intake |
| L1 | Housing resilience | gated society/independent/kachha | Feedback on infrastructure articles |
| L1 | Water source | municipal/borewell/tanker | Feedback: "I have municipal water" |
| L1 | Power backup | inverter/generator/none | Feedback on power cut articles |
| L2 | Specific area vulnerabilities | flood zone/industrial zone | Behavioral |

**I8: Digital & Leisure**
| Layer | Question | Depth | Trigger |
|-------|----------|-------|---------|
| L0 | Online activities | social/OTT/gaming/news/work | Segment 1 |
| L1 | Phone type | budget/mid/premium | Feedback on device pricing articles |
| L1 | Telecom plan | prepaid/postpaid | Feedback on tariff articles |
| L1 | Sports preference | cricket/football/kabaddi/none | Feedback on sports articles |
| L1 | Entertainment type | multiplex/OTT/live events/religious | Feedback on entertainment articles |
| L2 | Gaming type | casual/RMG/esports | Feedback on gaming regulation articles |

---

## 4. Feedback-Driven Question Engine

### 4.1 Feedback Types (extend current binary)

Current: 👍 Relevant / 👎 Not Relevant

New: Keep binary as primary, but on 👎 present a quick diagnostic:

```
👎 User marks "Infosys lays off 2000" as irrelevant

Bot: "Got it! Quick question — was this irrelevant because..."
  [Not my industry]
  [My job is stable]  
  [Wrong city]
  [Just not interested in job news]
```

Each diagnostic option maps to a profile refinement + optional follow-up question.

### 4.2 Diagnostic Question Schema

```yaml
diagnostic_questions:
  - id: diag_wrong_industry
    trigger:
      feedback: irrelevant
      matched_nodes_any: [corporate_hiring_and_layoffs, corporate_salaries, professional_upskilling]
      profile_missing: industry  # only ask if we don't know their industry yet
    text: "Was this irrelevant because..."
    options:
      - label: "Not my industry"
        action: ask_follow_up
        follow_up_id: depth_industry
      - label: "My company is stable"
        adjustments:
          corporate_hiring_and_layoffs: -0.3
      - label: "I'm a founder, not employee"
        adjustments:
          corporate_hiring_and_layoffs: -0.2
        depth_update:
          role_level: founder
      - label: "Wrong city/location"
        action: flag_location_issue

  - id: depth_industry
    text: "What industry are you in?"
    type: single_choice
    options:
      - label: "IT / Software Services"
        value: it_services
        depth_update: { industry: it_services }
        node_adjustments:
          corporate_hiring_and_layoffs: +0.2  # IT layoffs are frequent
          professional_upskilling: +0.3
      - label: "Fintech / Payments"
        value: fintech
        depth_update: { industry: fintech }
        node_adjustments:
          corporate_hiring_and_layoffs: -0.1  # less frequent in fintech
      - label: "E-commerce / D2C"
        value: ecommerce
        depth_update: { industry: ecommerce }
      - label: "Banking / BFSI"
        value: bfsi
        depth_update: { industry: bfsi }
        node_adjustments:
          psu_and_bank_jobs: +0.5
      - label: "Manufacturing"
        value: manufacturing
        depth_update: { industry: manufacturing }
        node_adjustments:
          factory_worker_wages: +0.3
      - label: "Healthcare"
        value: healthcare
      - label: "Other"
        value: other
```

### 4.3 Positive Feedback Deepening

When user marks an article relevant and we have room for a depth question:

```yaml
deepening_questions:
  - id: deepen_loans
    trigger:
      feedback: relevant
      matched_nodes_any: [residential_rent_and_pg, building_materials_and_labor]
      profile_missing: loans
      min_feedback_count: 3  # don't ask too early
    text: "Since housing costs matter to you — do you have a home loan?"
    options:
      - label: "Yes, paying EMI"
        depth_update: { has_home_loan: true }
        node_adjustments:
          building_materials_and_labor: +0.3
          capital_gains_tax: +0.3
      - label: "No"
        depth_update: { has_home_loan: false }
```

### 4.4 Rate Limiting

- Max 1 diagnostic question per article delivery
- Max 2 depth questions per day
- Don't ask depth questions in the first 3 deliveries (let user settle in)
- If user dismisses 2 diagnostic questions in a row, stop for 7 days
- Never ask the same depth dimension twice

---

## 5. Weight Adjustment Mechanics

### 5.1 Feedback adjustments (not absolute, relative)

```python
def apply_feedback_adjustment(
    current_weights: dict[str, float],
    adjustments: dict[str, float],  # node_id: delta (-0.3 to +0.3)
) -> dict[str, float]:
    """Apply relative weight adjustments from feedback."""
    for node, delta in adjustments.items():
        current = current_weights.get(node, 0.0)
        new = max(0.0, min(1.0, current + delta))
        
        # Universal floor still applies
        if node in UNIVERSAL_NODES:
            new = max(new, UNIVERSAL_FLOOR)
        
        current_weights[node] = new
    return current_weights
```

### 5.2 Implicit decay

Nodes that match articles but user consistently ignores (no feedback) or marks irrelevant:

```python
# After every 5 deliveries with no positive feedback on a node:
# decay weight by 0.05 (slow drift toward irrelevance)
# Floor: 0.1 for non-universal nodes (never fully zero from decay alone)
```

### 5.3 Profile recomputation

On any depth answer, recompute full profile:
1. Start with intake answers (L0)
2. Apply depth answers (L1, L2) as adjustments
3. Apply feedback-derived adjustments
4. Apply decay
5. Apply universal floor

Store separately: `raw_answers_json` (intake), `depth_answers_json` (feedback-derived), `adjustments_json` (cumulative feedback deltas).

---

## 6. Data Model Changes

### user_profiles table (extend)

```sql
ALTER TABLE user_profiles ADD COLUMN state TEXT;
ALTER TABLE user_profiles ADD COLUMN depth_answers_json TEXT DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN adjustments_json TEXT DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN feedback_stats_json TEXT DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN last_depth_question_at TEXT;
ALTER TABLE user_profiles ADD COLUMN depth_questions_today INTEGER DEFAULT 0;
```

### New table: profile_feedback_log

```sql
CREATE TABLE profile_feedback_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    match_id INTEGER,                -- which delivery triggered this
    feedback TEXT,                    -- relevant | irrelevant
    diagnostic_question_id TEXT,     -- which diagnostic was shown (nullable)
    diagnostic_answer TEXT,          -- what they picked (nullable)
    depth_question_id TEXT,          -- follow-up question (nullable)
    depth_answer TEXT,               -- follow-up answer (nullable)
    node_adjustments_json TEXT,      -- what changed in profile
    created_at TEXT DEFAULT (datetime('now'))
);
```

---

## 7. T2 Prompt Change for Location Scoping

Add to the micro-impact output schema in `engine/prompts/analyze_new.py`:

```
For each micro-impact, also output:
  "scope": "national" | "state:<StateName>" | "city:<CityName>"

Rules:
- Infrastructure disruptions (traffic, road closures, metro) → scope to the specific city
- State policy (electricity tariff, state board exams, state govt jobs) → scope to state
- National policy (income tax, GST, petrol price, RBI rate) → "national"
- Weather/environment (smog, flooding, heat) → scope to affected city/region
- If impact affects multiple cities, use the most specific common scope
```

---

## 8. Implementation Phases

### Phase 1: Location scoping (highest impact, smallest change)
- Add `scope` to T2 prompt schema
- Add `scope` to MicroImpact TypedDict in `engine/base.py`
- Add location filter in `profiling/matcher.py`
- Add `state` field to user_profiles
- **Files:** `engine/prompts/analyze_new.py`, `engine/base.py`, `profiling/matcher.py`, `pipeline/database.py`

### Phase 2: Extended feedback UI
- Change bot feedback from binary to diagnostic
- After 👎, show 3-4 diagnostic options inline
- Store diagnostic answers in `profile_feedback_log`
- **Files:** `bot/bot.py`, `pipeline/database.py`

### Phase 3: Diagnostic question engine
- Create `profiling/diagnostics.py` — loads diagnostic YAML, selects appropriate question based on trigger conditions
- Create `profiling/questions/diagnostics.yaml` — all diagnostic + depth questions
- Wire into feedback handler: on 👎 → select diagnostic → present → store answer → adjust weights
- **Files:** new `profiling/diagnostics.py`, new `profiling/questions/diagnostics.yaml`, `bot/bot.py`

### Phase 4: Deepening questions
- Create `profiling/deepening.py` — positive feedback triggers
- Occasionally ask depth questions after 👍 (rate-limited)
- **Files:** new `profiling/deepening.py`, `bot/bot.py`

### Phase 5: Weight adjustment engine
- Apply feedback-derived adjustments to profile
- Implement decay for consistently-ignored nodes
- Profile recomputation with all layers
- **Files:** `profiling/engine.py` (extend compute_profile)

### Phase 6: Gemini generation of full diagnostic trees
- For each I-world category, generate complete diagnostic question trees with Gemini
- Validate with synthetic personas
- **Files:** `profiling/questions/diagnostics.yaml`

---

## 9. Verification

1. **Location scoping:** Run pipeline trace, verify Mumbai traffic article doesn't push to Bangalore user
2. **Diagnostic flow:** Simulate: deliver article → user marks irrelevant → diagnostic shows → answer refines profile → next similar article scores lower
3. **Depth question:** Simulate: deliver article → user marks relevant → depth question asked → profile deepens → next article scores more precisely
4. **Rate limiting:** Verify max 2 depth questions/day, no repeat questions
5. **Decay:** After 10 deliveries with no positive feedback on a node, verify weight decreases

---

## 10. Key Principle

**Articles are the questionnaire. Feedback is the answer. The system gets smarter with every delivery.**

The intake gives us a rough sketch. Every article we deliver and every feedback we receive adds a brushstroke. Over 50 deliveries, the profile should converge from "corporate worker in Bangalore" to "fintech PM at a seed-stage startup in Koramangala, rents a 2BHK, drives a petrol car 8km to office, has no kids, invests in MFs and crypto, eats out 4x/week, watches OTT not cinema."
