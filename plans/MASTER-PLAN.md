# Impact News — Master Plan

> **Not what interests you. What affects you.**

A system that traces how world events impact individual lives through multi-hop causal chains, scored against a personal life dependency graph.

**Created**: 2026-03-09
**Status**: Planning

---

## Table of Contents

1. [Vision & Core Insight](#1-vision--core-insight)
2. [System Architecture](#2-system-architecture)
3. [Layer 1: Personal Life Graph](#3-layer-1-personal-life-graph)
4. [Layer 2: Causal Knowledge Engine](#4-layer-2-causal-knowledge-engine)
5. [Layer 3: Delivery & Impact Matching](#5-layer-3-delivery--impact-matching)
6. [Data Sources & Pipeline](#6-data-sources--pipeline)
7. [Technology Stack](#7-technology-stack)
8. [Causal Template Registry](#8-causal-template-registry)
9. [Implementation Phases](#9-implementation-phases)
10. [Open Problems & Risks](#10-open-problems--risks)

---

## 1. Vision & Core Insight

### The Problem

Every news personalization system asks: "What content should we show?" — an engagement optimization frame. Nobody asks: "What real-world effects reach this person?"

### The Insight

Build a **personal impact graph** where nodes are concrete life dependencies (commute, rent, groceries, job sector, investments, medications) and edges are causal chains to world events. Score incoming events not by "interest" but by "impact magnitude × probability × proximity to your life."

### Why Now

- LLMs can extract causal relations from unstructured text at scale (didn't exist 2 years ago)
- Structured output from LLMs enables reliable graph triple extraction
- Causal AI is pre-market for consumers — Gartner predicts high impact in 2-5 years
- ~70% of AI orgs plan to incorporate causal reasoning by 2026

### Why Nobody Has Built This

1. **Problem framing** — news industry thinks in content, not impact
2. **Business model** — causal AI companies sell B2B ($24K/yr Bloomberg terminals), no consumer play
3. **Cold start** — requires life context before showing value (unlike click-based recommendation)
4. **Cross-domain knowledge** — fusing geopolitics + commodities + supply chains + local infrastructure doesn't exist in one place
5. **Liability** — "this will raise your grocery bill 15%" is a different kind of wrong than showing an irrelevant article

### Key Design Decision

**Don't ask the LLM to reason causally. Ask it to classify events. Let pre-built templates handle the causal chains.** This sidesteps the 3+ hop reliability problem entirely.

---

## 2. System Architecture

```
+-------------------------------------------------------------+
|                     USER DEVICE (Local)                      |
|                                                              |
|  +-------------+  +-----------------+  +--------------+     |
|  | Life Graph   |  | Impact Surface  |  | Profiling    |     |
|  | (encrypted)  |  | Index (derived) |  | Engine       |     |
|  +------+------+  +--------+--------+  +------+-------+     |
|         |                  |                   |             |
|  +------v------------------v-------------------v---------+   |
|  |             Impact Matching Engine                     |   |
|  |  News + causal chains -> life graph traversal          |   |
|  |  -> impact score per event -> ranked personal feed     |   |
|  +------------------------+------------------------------+   |
|                           |                                  |
|          +----------------v-----------------+                |
|          |         Local UI / App           |                |
|          +---------------------------------+                 |
+---------------------------+----------------------------------+
                            | (fetches news + causal chains)
                            | (NO life graph data sent up)
+---------------------------v----------------------------------+
|                     SERVER (Cloud)                           |
|                                                              |
|  +---------+  +----------+  +---------+  +---------------+  |
|  | News    |  | NLP      |  | Causal  |  | Template      |  |
|  | Ingest  |->| Pipeline |->| Chain   |->| Registry      |  |
|  | (RSS,   |  | (spaCy,  |  | Engine  |  | (curated      |  |
|  |  APIs)  |  |  LLM)    |  | (LLM)   |  |  chains)      |  |
|  +---------+  +----------+  +---------+  +---------------+  |
|       |            |             |              |            |
|  +----v------------v-------------v--------------v--------+   |
|  |          News + Causal Chain API                       |   |
|  |  Returns: event + trigger_category + causal_chains     |   |
|  |  Knows NOTHING about individual users' life graphs     |   |
|  +-------------------------------------------------------+   |
+--------------------------------------------------------------+

KEY PRINCIPLE: Life graph never leaves the device.
Server processes news/causal chains. Client matches locally.
```

### Three Layers

| Layer | Responsibility | Changes How Often |
|-------|---------------|-------------------|
| **1. Personal Life Graph** | "What do I depend on?" | When user's life changes |
| **2. Causal Knowledge** | "How does event X propagate?" | Templates: rarely. Novel chains: daily |
| **3. Delivery** | "Does this event reach this person?" | Every incoming event |

---

## 3. Layer 1: Personal Life Graph

### What It Is

A structured dependency map — not preferences, not interests. A map of what your life depends on.

### Life Dependency Dimensions (10 categories)

#### 3.1 Geographic Dependencies
- Primary residence (country, state, city, climate zone, risk zones)
- Workplace location + commute (mode, distance, fuel type, route)
- Family locations (parents, siblings — city + country)
- Frequent travel routes, property elsewhere

#### 3.2 Financial Dependencies
- Income streams (salary, freelance, rental — amount, currency, sector)
- Debts (mortgage fixed/variable, auto loan, student loan — rate, benchmark, bank)
- Investments (stocks, MF, ETF, crypto, gold — category, value, currency)
- Insurance (health, life, auto, home — provider, coverage, premium)
- Tax obligations, bank accounts, retirement accounts

#### 3.3 Consumption Dependencies
- Food (dietary restrictions, staple foods, import-dependent items)
- Energy (electricity provider, gas/heating type, monthly usage)
- Transport (vehicle make/fuel, public transit, ride-sharing)
- Healthcare consumption (medications, devices, therapy)
- Digital services, childcare/education

#### 3.4 Employment Dependencies
- Employer (name, sector, sub-sector, size, public/private, HQ country)
- Role (title, department, seniority, skills, automation risk)
- Employment type (full-time/contract/freelance, notice period)
- Remote work status

#### 3.5 Health Dependencies
- Chronic conditions (severity, management)
- Medications (specific drugs, manufacturer, generic availability, criticality)
- Healthcare provider, insurance plan
- Allergies, family health history

#### 3.6 Family & Dependent Dependencies
- Spouse/partner (employment, health, citizenship)
- Children (ages, schools, health)
- Elderly dependents (health, location, care needs)
- Dependents abroad (remittances, stability)

#### 3.7 Legal & Regulatory Dependencies
- Citizenship(s), visa/immigration status
- Professional licenses, business registrations
- Property titles, vehicle registrations

#### 3.8 Social & Institutional Dependencies
- Religious institution, community organizations
- Professional networks, social safety nets

#### 3.9 Asset Dependencies
- Real estate, vehicles, digital assets
- Intellectual property, business equity

#### 3.10 Time-Sensitive Dependencies
- Upcoming life transitions (moving, marriage, baby, retirement)
- Contract expirations (lease, employment, insurance)
- Scheduled medical events, financial milestones, travel plans

### Impact Surfaces

An "impact surface" is where a world event connects to a life node:

```
ImpactSurface {
  trigger_category: "commodity_price.crude_oil"
  life_node_path:   "consumption.transport.fuel_cost"
  impact_direction: COST_INCREASE
  hop_distance:     2
  confidence:       0.80
  chain:            "oil_price -> fuel_price -> commute_cost"
}
```

### Progressive Profiling Strategy

**Tier 0 — Zero input (immediate value):**
- Infer from IP geolocation (country, city)
- Show: "Here are today's stories affecting people in [city]"
- Graph completeness: ~5%

**Tier 1 — 30 seconds (3 questions):**
1. Where do you live? (city autocomplete)
2. What do you do? (job title + company)
3. Do you own or rent?

System infers from these three:
- Location → climate zone, disaster risk, jurisdiction, cost of living
- Job + company → sector, size, public/private, HQ country, income band
- Own/rent → mortgage exposure, rent regulation exposure
- Graph completeness: ~25%

**Tier 2 — Event-driven profiling (days/weeks):**
When news happens, ask if it affects them:
- "RBI raises repo rate" → "Do you have a floating rate home loan?"
- "Crude crosses $90" → "How do you commute?"
- "H-1B lottery results" → "Does immigration policy affect you?"

**Tier 3 — Periodic check-ins (monthly):**
"Anything changed recently?" — job, move, family, medication

**Tier 4 — Deep profiling (opt-in):**
Link accounts (Account Aggregator/Plaid), health profile

### Storage

**MVP:** Encrypted JSON file on device (AES-256-GCM). Life graph for one person < 1MB.

**Scale:** Neo4j for multi-user graph traversal queries ("who is affected by event X?").

### Privacy Architecture

- **Life graph never leaves the device** — zero-knowledge architecture
- Server serves news + causal chains (generic, same for everyone)
- Client matches locally against personal graph
- Optional encrypted cloud backup (user holds key)
- GDPR + DPDPA compliant by design (local-first = data minimization)

### Graph Update Patterns

| Change Type | Frequency | Examples |
|-------------|-----------|---------|
| Micro | Daily-weekly | WFH days, dosage adjustment |
| Periodic | Monthly-quarterly | Investment rebalance, salary revision |
| Life transition | Yearly+ | New job, marriage, baby, retirement |
| Sudden | Unpredictable | Job loss, diagnosis, family emergency |

Cascade logic: job change triggers updates to income, commute, insurance, visa status. Each node has staleness tracking (confidence decays with age).

---

## 4. Layer 2: Causal Knowledge Engine

### Architecture

Three components, not one monolithic reasoner:

#### 4a. Domain Causal Templates (pre-built, curated)

Known, stable causal structures that don't change with the news. This is the moat.

```yaml
template: crude_oil_supply_disruption
  trigger_conditions:
    - major_producer_conflict
    - shipping_route_blockade
    - OPEC_production_cut
  first_order_effects:      # confidence: 0.90
    - crude_oil_price: increase
    - oil_futures: increase
  second_order_effects:     # confidence: 0.75
    - petrol_price: increase (lag: 1-4 weeks)
    - diesel_price: increase (lag: 1-4 weeks)
    - aviation_fuel: increase (lag: 1-2 weeks)
  third_order_effects:      # confidence: 0.55
    - commute_cost: increase (via petrol_price)
    - food_transport_cost: increase (via diesel_price)
    - flight_prices: increase (via aviation_fuel)
  fourth_order_effects:     # confidence: 0.40
    - food_prices: increase (via food_transport + fertilizer)
    - general_inflation: increase
  confidence_decay: [0.90, 0.75, 0.55, 0.40]
```

**14 domains, 56 templates** (see Section 8 for full registry).

#### 4b. Event-to-Template Matcher (LLM-powered)

When a news event comes in, the LLM classifies — it does NOT reason causally:

```json
{
  "event": "Iran threatens to close Strait of Hormuz",
  "template_match": "crude_oil_supply_disruption",
  "trigger": "shipping_route_blockade",
  "status": "threatened_not_enacted",
  "probability": 0.15,
  "magnitude": "major_if_enacted",
  "confidence": 0.70
}
```

Use small, cheap models for this: Gemini Flash ($0.075/1M tokens) or GPT-4o-mini ($0.15/1M tokens).

#### 4c. Novel Chain Discovery (LLM + human-in-the-loop)

For events that don't match existing templates:

```
"New EU regulation requires all AI systems to be auditable by 2027"
→ LLM proposes: regulation → compliance cost → hiring shift →
  reduced R&D → slower product development
→ Confidence: LOW (novel, unvalidated)
→ Flag for human review before serving
```

Use larger models (Claude Sonnet/GPT-4o) in batch (daily). Novel chains get low confidence scores. Validated chains become new templates over time.

### Confidence Decay Model

| Hop | Typical Confidence | Reasoning |
|-----|-------------------|-----------|
| Trigger → 1st order | 85-95% | Direct, well-understood mechanism |
| 1st → 2nd order | 65-80% | Mediated by market/policy response |
| 2nd → 3rd order | 40-60% | Multiple competing forces |
| 3rd → Personal | 25-45% | Depends on individual circumstances |

### Calibration Notes

- Novel situations decay faster than precedented ones
- Geography matters enormously (coastal Florida ≠ inland Montana)
- Income modulates impact (high-income buffers more)
- Timing confidence is lower than direction confidence
- Government intervention can break chains at any hop
- Simultaneous multi-domain triggers are super-additive

---

## 5. Layer 3: Delivery & Impact Matching

### Scoring Algorithm

```python
def score_event_for_user(event, user_graph):
    template = match_event_to_template(event)  # LLM classification
    chains = template.get_causal_chains()

    impacts = []
    for chain in chains:
        for hop_idx, effect in enumerate(chain.effects):
            # Does this effect touch the user's life graph?
            matching_nodes = user_graph.find_matching_nodes(effect)
            for node in matching_nodes:
                score = (
                    event.magnitude *
                    event.probability *
                    chain.confidence_at_hop[hop_idx] *
                    node.importance
                )
                if score > THRESHOLD:
                    impacts.append(Impact(
                        score=score,
                        chain=chain.path_to(hop_idx),
                        life_node=node,
                        explanation=generate_explanation(chain, node)
                    ))

    return sorted(impacts, key=lambda i: i.score, reverse=True)
```

### Delivery Tiers

| Score | Delivery | Example |
|-------|----------|---------|
| > 0.8 | **PUSH** (instant) + full explanation | "RBI hiked 50bps. Your floating rate EMI increases ~Rs 2,800/month" |
| 0.3-0.8 | **DAILY DIGEST** (8 AM local) | "Oil rose 8% this week. May affect your commute cost by ~Rs 500/month" |
| < 0.3 | **WEEKLY SUMMARY** | "EU AI regulation advancing. Low impact on your sector for now" |

### Notification Fatigue Management

- Max 3 push notifications per day
- Batch medium-importance into morning digest
- User-configurable thresholds per category
- "Snooze" per topic (suppress tariff news for 7 days)
- Progressive disclosure: headline → 1-line impact → full explanation

### Explanation Generation

The "this affects you because..." chain is the core value proposition:

```
US announces 25% steel tariff on EU imports

This affects you because:
  Steel tariff (25%) → Higher input costs for auto manufacturers
  → Your employer (Ford) faces margin pressure
  → Potential impact on hiring decisions

  Steel tariff → Higher vehicle prices (+2-4%)
  → You have an auto loan renewal in 6 months

Impact score: 0.72 (moderate-high)
```

Generate with GPT-4o-mini at alert time, passing the causal chain path as context. Cache the explanation.

### Reverse Search Pattern (Bloomberg-inspired)

Instead of searching documents for queries, register user dependency patterns as "saved queries" and match incoming events against them.

When a new event arrives → find which users' impact surfaces match → score and alert. This is the Elasticsearch Percolator / Lucene Luwak pattern.

---

## 6. Data Sources & Pipeline

### News Ingestion (by tier)

**Free MVP ($0/month):**

| Source | Update Freq | Coverage | Format |
|--------|-------------|----------|--------|
| GDELT Event DB | Every 15 min | Global events, 100+ languages | BigQuery (1TB/mo free) |
| GDELT GKG | Every 15 min | Entities, themes, tone from news | BigQuery |
| Google News RSS | Real-time | Global, topic-filtered | XML/RSS |
| NewsAPI.org (free) | Real-time | 50K+ sources, 100 req/day | JSON REST |

**Paid Growth ($200-500/month):**

| Source | Cost | Value Add |
|--------|------|-----------|
| NewsAPI.ai | $89/mo | NLP-enriched, entity extraction, event clustering |
| Alpha Vantage Premium | $50/mo | Real-time commodity prices |
| TrueData | ~$10/mo | Indian market data (NSE, MCX) |
| OpenWeatherMap | $40/mo | Global weather alerts |

### Economic/Financial Data (free)

| Source | Coverage |
|--------|----------|
| FRED (St. Louis Fed) | 840K+ series: GDP, inflation, rates, CPI, forex |
| World Bank API | GDP, trade, demographics for 200+ countries |
| IMF Data Portal | WEO, BOP, commodity prices, exchange rates |
| RBI DBIE | Indian economy: rates, inflation, forex, trade |
| data.gov.in | Indian government open data |

### Geopolitical & Risk Data (free)

| Source | Coverage |
|--------|----------|
| ACLED | Political violence, protests globally |
| OFAC / OpenSanctions | Sanctions lists |
| GPR Index | Geopolitical risk index since 1900 |
| Global Trade Alert | 70K+ trade policy interventions |

### Climate & Weather (free)

| Source | Coverage |
|--------|----------|
| NOAA/NWS API | US forecasts, alerts, observations |
| EM-DAT | 27K+ disasters since 1900 |
| NASA EONET | Real-time natural events |

### NLP Pipeline

```
Article → spaCy (NER, tokenize) → Embeddings (all-MiniLM) → LLM (classify + extract)
```

| Layer | Tool | Purpose | Cost |
|-------|------|---------|------|
| Preprocessing | spaCy | NER, POS, tokenization | Free, <10ms |
| Embeddings | all-MiniLM-L6-v2 | Dedup, clustering | Free (local) |
| Classification | Gemini Flash | Event type, severity | $0.075/1M tokens |
| Triple extraction | GPT-4o-mini | Structured triples | $0.15/1M tokens |
| Novel discovery | Claude Sonnet | Complex causal reasoning | $3/1M tokens (batch) |
| Explanations | GPT-4o-mini | "This affects you because..." | $0.15/1M tokens |

### Deduplication (3-tier)

1. **Exact** — URL/title hash via Bloom filter or Redis SET
2. **Near** — MinHash LSH via `datasketch` (catches 80%+ similar articles)
3. **Semantic** — Embedding cosine similarity via pgvector (threshold ~0.85)

Then cluster remaining into "event clusters" using HDBSCAN.

---

## 7. Technology Stack

### MVP Stack ($37/month)

```
                MODULAR MONOLITH (Python/FastAPI)
  ┌──────────┐    ┌────────────┐    ┌────────────┐
  │ Ingestion│    │ Processing │    │  Delivery  │
  │ - RSS    │    │ - NER      │    │ - Scoring  │
  │ - APIs   │───>│ - Dedup    │───>│ - Email    │
  │ - GDELT  │    │ - Classify │    │ - Telegram │
  └──────────┘    │ - Extract  │    └────────────┘
                  └────────────┘
                       │
            Redis Streams (event bus)
                       │
         ┌─────────────┼──────────────┐
    PostgreSQL      Redis         Pgvector
    (graph+data)   (cache+dedup)  (embeddings)
```

| Component | MVP Choice | Scale Choice | Migration Trigger |
|-----------|-----------|-------------|-------------------|
| Language | Python 3.12 + FastAPI | Same | — |
| Task queue | Celery/ARQ | Same | — |
| Stream processing | Redis Streams | Kafka | >50K events/min |
| Graph storage | PostgreSQL + recursive CTEs | Neo4j | >50M edges or 4+ hop queries |
| Vector storage | Pgvector | Qdrant | >10M embeddings |
| Classification | Gemini Flash API | Fine-tuned 7B local | >100K articles/day |
| Triple extraction | GPT-4o-mini API | Fine-tuned 7B local | Cost >$500/mo |
| Causal reasoning | Claude Sonnet (batch) | Claude Sonnet (batch) | — |
| Scoring | BFS + multiplicative decay | Bayesian network (pgmpy) | Need uncertainty quantification |
| Delivery | Email + Telegram | Push + email + web + mobile | Mobile app launch |
| Deployment | Docker Compose on Hetzner VPS | Kubernetes | >1000 users |

**Estimated costs:**
- Hetzner VPS (CX31): ~$17/month
- LLM APIs (10K articles/day): ~$7/day = ~$200/month
- **Total: ~$220/month** at moderate scale

### PostgreSQL Graph Schema (MVP)

```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    type VARCHAR(50),       -- 'company', 'sector', 'commodity', 'location'
    name VARCHAR(255),
    wikidata_id VARCHAR(20),
    properties JSONB
);

CREATE TABLE causal_edges (
    id UUID PRIMARY KEY,
    source_id UUID REFERENCES entities(id),
    target_id UUID REFERENCES entities(id),
    relation_type VARCHAR(100),
    strength FLOAT DEFAULT 1.0,  -- 0-1 confidence
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,        -- NULL = active
    evidence JSONB
);

CREATE TABLE user_dependencies (
    user_id UUID,
    entity_id UUID REFERENCES entities(id),
    relation VARCHAR(100),
    importance FLOAT DEFAULT 0.5,
    PRIMARY KEY (user_id, entity_id, relation)
);

-- Causal chain traversal query
WITH RECURSIVE impact_chain AS (
    SELECT e.target_id, e.relation_type, e.strength, 1 AS depth,
           ARRAY[e.source_id] AS path
    FROM causal_edges e
    WHERE e.source_id = :event_entity_id
      AND (e.valid_to IS NULL OR e.valid_to > NOW())
    UNION ALL
    SELECT e.target_id, e.relation_type,
           ic.strength * e.strength AS strength,
           ic.depth + 1, ic.path || e.source_id
    FROM causal_edges e
    JOIN impact_chain ic ON e.source_id = ic.target_id
    WHERE ic.depth < 5 AND e.strength > 0.1
      AND NOT e.target_id = ANY(ic.path)
)
SELECT ic.*, ud.user_id, ud.relation, ud.importance
FROM impact_chain ic
JOIN user_dependencies ud ON ic.target_id = ud.entity_id;
```

---

## 8. Causal Template Registry

### Overview: 14 Domains, 56 Templates

| # | Domain | Templates | Key Personal Impacts |
|---|--------|-----------|---------------------|
| 1 | Energy & Oil | 5 | Commute cost, heating, food prices, inflation |
| 2 | Monetary Policy | 4 | EMI/mortgage, savings yield, asset values, job market |
| 3 | Trade & Tariffs | 4 | Consumer prices, food costs, job security |
| 4 | Food & Agriculture | 4 | Grocery costs, diet, food availability |
| 5 | Climate & Weather | 4 | Insurance, property, health, utilities |
| 6 | Technology & Regulation | 4 | Job displacement, privacy, platform access |
| 7 | Geopolitics & Conflict | 4 | Energy/food prices, remittances, travel, investments |
| 8 | Real Estate & Housing | 3 | Rent, mortgage, property value, mobility |
| 9 | Healthcare & Pharma | 4 | Medication access/cost, treatment, insurance |
| 10 | Employment & Labor | 4 | Job security, wages, service prices |
| 11 | Infrastructure | 4 | Commute, property value, utilities, safety |
| 12 | Financial Markets | 4 | Savings, retirement, insurance premiums |
| 13 | Education | 3 | Tuition, career options, student debt |
| 14 | Supply Chain | 4 | Product prices, availability, delivery times |

### Cross-Domain Compound Patterns

The most impactful events trigger chains across multiple domains simultaneously:

| Pattern | Example | Domains Hit |
|---------|---------|-------------|
| War → Triple Shock | Russia-Ukraine 2022 | Energy + Food + Finance |
| Climate → Insurance Cascade | FL/CA 2022-2024 | Climate + Insurance + Housing |
| Pandemic → Everything | COVID-19 2020 | Supply Chain + Employment + Healthcare + Education |
| Trade War → Consumer Squeeze | US-China 2025 | Trade + Supply Chain + Agriculture + Consumer |

### MVP Template Set (10 templates for Phase 1)

1. **OPEC production cut** → fuel → commute + food transport
2. **Central bank rate hike** → mortgage EMI + savings yield + housing
3. **Broad tariff escalation** → consumer prices across categories
4. **Monsoon failure / crop loss** → food inflation
5. **Shipping route blockade** → import delays + price increases
6. **Currency depreciation** → import costs + electronics + education abroad
7. **Major employer layoffs** → job security + local economy
8. **Drug shortage** → medication availability + cost
9. **Extreme weather event** → infrastructure + insurance + health
10. **Stock market crash** → retirement savings + wealth effect

### Template Data Format

Each template stored as structured YAML/JSON:

```yaml
id: energy_opec_production_cut
domain: energy_oil
version: 1.0
last_validated: 2026-03-09

trigger_conditions:
  - type: opec_production_decision
    keywords: ["OPEC", "production cut", "output reduction", "supply cut"]
  - type: producer_unilateral
    keywords: ["Saudi cut", "Russia cut", "voluntary reduction"]

causal_chain:
  - hop: 1
    effect: crude_oil_futures_rise
    magnitude_range: [5, 15]  # percent
    lag: "0-3 days"
    confidence: 0.90
    evidence: "Oct 2022: OPEC+ cut 2M bpd, Brent +6% same day"

  - hop: 2
    effect: retail_fuel_price_rise
    magnitude_range: [10, 25]  # percent
    lag: "1-4 weeks"
    confidence: 0.75
    evidence: "US gasoline $3.30 to $3.80 post Oct 2022 cut"
    depends_on: [crude_oil_futures_rise]

  - hop: 3
    effect: transport_logistics_cost_rise
    magnitude_range: [5, 15]
    lag: "2-6 weeks"
    confidence: 0.55
    depends_on: [retail_fuel_price_rise]

  - hop: 4
    effect: consumer_food_price_rise
    magnitude_range: [3, 8]
    lag: "4-12 weeks"
    confidence: 0.40
    depends_on: [transport_logistics_cost_rise]

impact_surfaces:
  - trigger: "commodity_price.crude_oil"
    affects: ["consumption.transport", "consumption.food", "consumption.energy"]
    direction: COST_INCREASE

  - trigger: "commodity_price.crude_oil"
    affects: ["financial.investments"]
    direction: MIXED  # energy stocks up, others down
    condition: "user has energy sector investments"

modifiers:
  - geography: "oil_importing_country"
    effect: "amplifies impact"
  - geography: "oil_exporting_country"
    effect: "inverts impact (benefit)"
  - income: "low"
    effect: "higher relative impact (larger % of budget)"
```

---

## 9. Implementation Phases

### Phase 1: MVP — Single User, End-to-End (Weeks 1-6)

**Goal:** Working pipeline for one user (you). Prove the concept works.

#### Week 1-2: Data Pipeline
- [ ] Set up FastAPI project structure
- [ ] GDELT BigQuery integration (event ingestion every 15 min)
- [ ] RSS feed parser (5-10 quality sources: Reuters, Bloomberg, Economic Times, Livemint)
- [ ] NewsAPI.org free tier integration
- [ ] Article dedup (exact hash + MinHash)
- [ ] spaCy NER pipeline
- [ ] Gemini Flash event classification
- [ ] PostgreSQL schema (entities, causal_edges, events)
- [ ] Redis Streams for internal event bus

#### Week 3-4: Causal Engine + Life Graph
- [ ] Implement 10 MVP causal templates as YAML files
- [ ] Event-to-template matcher (LLM classifier)
- [ ] PostgreSQL recursive CTE for chain traversal
- [ ] Life graph JSON schema
- [ ] Your personal life graph (first user)
- [ ] Impact surface computation from life graph + templates
- [ ] Scoring algorithm (BFS + multiplicative decay)

#### Week 5-6: Delivery + Polish
- [ ] Daily digest email generation (GPT-4o-mini explanations)
- [ ] Telegram bot for real-time high-impact alerts
- [ ] Impact explanation generator ("this affects you because...")
- [ ] Docker Compose deployment (Hetzner VPS)
- [ ] Celery beat for scheduled ingestion + scoring
- [ ] Basic monitoring (logs, error tracking)

**Deliverable:** You receive a daily digest + Telegram alerts scored against your actual life.

**Cost:** ~$37/month (VPS + LLM APIs at low volume)

---

### Phase 2: Validate & Refine (Weeks 7-12)

**Goal:** Is the output actually useful? Refine templates, add sources.

#### Accuracy & Calibration
- [ ] Track prediction accuracy (did predicted impacts materialize?)
- [ ] Calibrate confidence decay per template based on actual outcomes
- [ ] Add FRED + Alpha Vantage for real-time price validation
- [ ] Backtest templates against 2022-2025 events

#### More Templates + Sources
- [ ] Expand to 30 templates (add healthcare, employment, infrastructure)
- [ ] Add 50+ news sources
- [ ] Semantic dedup with embeddings (pgvector)
- [ ] Event clustering (HDBSCAN)
- [ ] ACLED integration for geopolitical events
- [ ] India-specific sources (RBI DBIE, data.gov.in, IMD)

#### User Experience
- [ ] Progressive profiling via Telegram ("Does this affect you?" questions)
- [ ] Life graph refinement based on event-driven prompts
- [ ] Feedback loop: "Was this relevant?" → tune scoring thresholds
- [ ] Weekly summary email alongside daily digest

---

### Phase 3: Multi-User Platform (Months 4-6)

**Goal:** Open to 10-50 beta users. Build the product.

#### Platform
- [ ] User auth (email/OAuth)
- [ ] Onboarding flow (3-question Tier 1)
- [ ] Web dashboard (React + D3.js for causal chain visualization)
- [ ] User settings (notification preferences, thresholds, snooze)
- [ ] Progressive profiling UI

#### Scale
- [ ] PostgreSQL → Neo4j migration (or keep Postgres if <50M edges)
- [ ] Elasticsearch Percolator for reverse search (event → matching users)
- [ ] Fine-tune 7B model for event classification (replace Gemini Flash API)
- [ ] Batch scoring optimization

#### Novel Chain Discovery
- [ ] Daily batch job: Claude Sonnet processes unmatched events
- [ ] Proposed novel chains flagged for review
- [ ] Review UI for validating/rejecting novel chains
- [ ] Validated chains promoted to templates

---

### Phase 4: Product-Market Fit (Months 7-12)

**Goal:** Find if people will pay for this.

#### Mobile App
- [ ] React Native or Flutter app
- [ ] Local life graph storage (encrypted)
- [ ] Push notifications (FCM/APNs)
- [ ] Causal chain visualization (interactive)
- [ ] Offline-capable (cached chains + local scoring)

#### Advanced Features
- [ ] "What if" simulator — user explores hypothetical events
- [ ] Impact timeline — "if this continues, here's your 6-month outlook"
- [ ] Compound event detection (multi-domain triggers)
- [ ] Bayesian scoring upgrade (pgmpy)
- [ ] Account Aggregator integration (India) for auto-profiling

#### Business
- [ ] Pricing model (freemium: 3 domains free, all 14 paid?)
- [ ] Waitlist / beta community
- [ ] Content partnerships (financial advisors, insurance)

---

### Phase 5: Scale (Year 2+)

- [ ] Kafka migration for event streaming
- [ ] Qdrant for vector search at scale
- [ ] Multi-country support (US, EU, India initially)
- [ ] Localized causal templates per country
- [ ] API for third-party integrations
- [ ] B2B offering (financial advisors, insurance companies)
- [ ] Temporal knowledge graph (Graphiti) for evolving causal relationships

---

## 10. Open Problems & Risks

### Technical

| Problem | Severity | Mitigation |
|---------|----------|------------|
| LLMs degrade at 3+ hop reasoning | High | Templates handle hops, LLM only classifies |
| Real-time graph updates at scale | Medium | Batch scoring (daily) for most, real-time for high-impact only |
| Cross-domain causal fusion | High | Start with single-domain templates, add compound patterns manually |
| Confidence calibration | Medium | Backtest against historical events, track actuals |
| Novel event coverage | Medium | Catch-all "unmatched event" category + human review |

### Product

| Risk | Severity | Mitigation |
|------|----------|------------|
| Cold start (no value without life graph) | Critical | Tier 0 value (location-only), event-driven profiling |
| False positives erode trust | High | Conservative thresholds, "confidence: low" labels |
| False negatives (missed impacts) | Medium | Transparent about coverage ("we track 14 domains") |
| Notification fatigue | Medium | Strict caps, digest-first, user control |
| "Anxiety machine" perception | Medium | Tone matters: inform, don't alarm. Include "no action needed" |

### Business

| Risk | Severity | Mitigation |
|------|----------|------------|
| No proven consumer business model | High | Validate with free beta, explore B2B pivot early |
| Privacy sensitivity limits growth | Medium | Local-first architecture is a feature, not a bug |
| Template curation doesn't scale | Medium | Novel chain discovery + community curation |
| Existing players copy the concept | Low | Execution + template quality = moat |

---

## Appendix: Key Research References

### Causal AI
- CausalEval (NAACL 2025) — LLM causal reasoning benchmarks
- Causal Graph Event Reasoning (ACL 2025) — multi-expert LLM causal DAGs
- Event-CausNet — LLM-driven causal knowledge bases
- CausalAgent (2026) — multi-agent causal inference

### Companies
- **Samaya AI** ($43.5M) — economy-wide causal world models
- **causaLens** — enterprise causal AI platform
- **PyWhy/DoWhy** (Microsoft) — open-source causal inference

### Architecture Patterns
- Bloomberg Luwak — reverse search for news alerting
- Dataminr — multi-modal weak signal fusion
- Palantir Ontology — entity modeling mirroring real-world structure

### Data
- GDELT — most cost-effective structured event pipeline (free via BigQuery)
- FRED — indispensable for macro data (free, 840K+ series)
- NewsAPI.ai — best NLP-enriched news API for the price
