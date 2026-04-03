# Plan: Level 1 (Event Schema) + Level 2 (Two-Tier LLM)

## Level 1: Event Schema & Tracking

### Goal
Articles cluster into events. An event is a living entity that accumulates articles and evolves its impact assessment over time.

### Database Schema

```sql
-- An event is a macro-level happening that generates multiple articles
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,          -- UUID
    name TEXT NOT NULL,                 -- "Iran-Hormuz Shipping Crisis"
    summary TEXT NOT NULL,              -- Running 2-3 line summary, updated with each article
    triggers_json TEXT NOT NULL,        -- ["brent_crude", "global_shipping_routes"]
    current_impacts_json TEXT NOT NULL, -- [{node, probability, magnitude, polarity, delay, mechanism}]
    stage TEXT NOT NULL DEFAULT 'new',  -- new | escalating | stable | resolved
    category TEXT,                      -- Broad category for grouping: energy, monetary, weather, etc.
    first_seen_at TEXT NOT NULL,
    last_updated_at TEXT NOT NULL,
    article_count INTEGER DEFAULT 1
);

-- Links articles to events, tracks what each article added
CREATE TABLE event_articles (
    event_id TEXT NOT NULL REFERENCES events(event_id),
    article_id TEXT NOT NULL REFERENCES articles(id),
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_seed INTEGER DEFAULT 0,          -- 1 = first article that created this event
    PRIMARY KEY (event_id, article_id)
);

CREATE INDEX idx_events_stage ON events(stage);
CREATE INDEX idx_events_category ON events(category);
CREATE INDEX idx_events_last_updated ON events(last_updated_at);
CREATE INDEX idx_event_articles_event ON event_articles(event_id);
CREATE INDEX idx_event_articles_article ON event_articles(article_id);
```

### Event Lifecycle

```
Article 1 (seed) → create event (stage=new, impacts from Tier 2)
Article 2 (same event) → update event (stage=escalating, impacts revised)
Article N → update event (impacts revised, stage may change)
No articles for 7 days → stage=resolved
```

### Event Operations (pipeline/events.py)

```python
class EventStore:
    """SQLite-backed event storage and retrieval."""
    
    def __init__(self, db: Database): ...
    
    def create_event(
        self, name: str, summary: str, triggers: list[str],
        impacts: list[dict], category: str, seed_article_id: str
    ) -> str:
        """Create new event, return event_id."""
    
    def update_event(
        self, event_id: str, summary: str, impacts: list[dict],
        stage: str | None = None
    ) -> None:
        """Update event summary and impacts after a new article."""
    
    def link_article(self, event_id: str, article_id: str) -> None:
        """Link an article to an existing event."""
    
    def get_event(self, event_id: str) -> dict | None:
        """Full event with all fields."""
    
    def get_event_articles(self, event_id: str) -> list[dict]:
        """All articles linked to this event, chronological."""
    
    def search_active_events(self, limit: int = 50) -> list[dict]:
        """All non-resolved events, most recent first."""
    
    def get_events_by_trigger(self, trigger_node: str) -> list[dict]:
        """Find events that share a trigger node."""
    
    def resolve_stale_events(self, days: int = 7) -> int:
        """Mark events with no new articles in N days as resolved. Returns count."""
    
    def get_event_summary_list(self) -> list[dict]:
        """Short list of active events for Tier 1 prompt context.
        Returns: [{event_id, name, triggers, stage, last_updated_at}]"""
```

### Files
- `pipeline/events.py` — EventStore class
- `pipeline/database.py` — add events + event_articles tables to schema

---

## Level 2: Two-Tier LLM Split

### Goal
Split the current single Gemini call into two tiers. Tier 1 is fast and cheap (classification + event matching). Tier 2 is deep (full impact analysis with taxonomy). Only relevant articles reach Tier 2.

### Tier 1: Fast Classifier (engine/classifier.py)

**Model:** gemini-3.1-flash-lite-preview (same as now, but much shorter prompt)

**Input:** Article title + summary + list of active event names (from EventStore.get_event_summary_list)

**Output (structured JSON):**
```json
{
    "relevant": true,
    "event_match": {
        "event_id": "abc123",        // null if no match → new event
        "confidence": 0.9
    },
    "category": "energy",            // broad category hint
    "headline_triggers": ["crude oil", "shipping disruption"]  // plain text, not node IDs
}
```

Or for irrelevant:
```json
{
    "relevant": false,
    "reason": "sports result"
}
```

**Prompt design (~2K tokens vs current ~19K):**
```
You are a news relevance classifier for Indian citizens.

Does this article describe an event that causally affects ordinary Indians at scale?

Filter out: sports, celebrity, individual crimes, opinion pieces, company-specific
news that doesn't ripple to consumers, foreign affairs with no India chain.

Active events (match if this article belongs to one):
- [abc123] Iran-Hormuz Shipping Crisis (energy, escalating)
- [def456] RBI Rate Hike Cycle (monetary, stable)
- ...

Article:
Title: {title}
Summary: {summary}

Return JSON: {relevant, event_match: {event_id, confidence} | null, category, headline_triggers}
Or: {relevant: false, reason: "..."}
```

**Key:** No taxonomy in prompt. No T/I node IDs. Just natural language classification. Fast, cheap, <1s.

**Implementation:**
```python
class ArticleClassifier:
    def __init__(self, gemini: GeminiClient, event_store: EventStore): ...
    
    def classify(self, title: str, summary: str) -> ClassificationResult:
        """Tier 1: classify relevance + match to existing event."""
        # Build prompt with active event list from event_store
        # Call gemini flash-lite with short prompt
        # Parse and return result
```

```python
class ClassificationResult(TypedDict):
    relevant: bool
    event_match: dict | None   # {event_id, confidence} or None
    category: str | None
    headline_triggers: list[str]
    reason: str | None         # Only if not relevant
```

### Tier 2: Deep Impact Analyzer (engine/llm_engine.py — refactored)

**Model:** gemini-2.0-flash (upgrade from flash-lite for reasoning quality)

**Input:** Article title + summary + full T/I taxonomy + event context (if updating existing event)

**Two modes:**

**Mode A — New event:** Same as current prompt. Article + taxonomy → triggers + impacts.

**Mode B — Event update:** Article + taxonomy + event's current state → UPDATED impacts + UPDATED summary.

```
== EXISTING EVENT CONTEXT ==
Name: Iran-Hormuz Shipping Crisis
Summary: Houthi-linked attacks disrupted shipping through Hormuz Strait...
Current impacts:
  - retail_petrol: prob=0.9, mag=0.7, pol=+1, delay=SHORT_TERM
  - retail_diesel: prob=0.9, mag=0.7, pol=+1, delay=SHORT_TERM
  - domestic_flight_ticket: prob=0.8, mag=0.6, pol=+1, delay=SHORT_TERM
Stage: escalating

== NEW ARTICLE ==
Title: Government announces Rs 5/litre subsidy on diesel for transporters
Summary: ...

== TASK ==
Given this new development, update the event's impact assessment:
- Which impacts changed? (probability, magnitude, delay may shift)
- Any new impacts?
- Any impacts no longer relevant?
- What stage is this event in now? (new/escalating/stable/resolved)
- Updated 2-line event summary incorporating this new development.
```

**Output:**
```json
{
    "triggers": ["brent_crude", "ministry_of_finance"],
    "impacts": [
        {"node": "retail_petrol", "probability": 0.9, "magnitude": 0.7, ...},
        {"node": "retail_diesel", "probability": 0.7, "magnitude": 0.4, ...},  // magnitude dropped!
        {"node": "domestic_flight_ticket", "probability": 0.8, "magnitude": 0.6, ...}
    ],
    "stage": "stable",
    "summary": "Iran-Hormuz shipping crisis disrupted oil supply. Government diesel subsidy partially cushions transport sector impact."
}
```

**Implementation:**
```python
class ImpactAnalyzer:
    """Tier 2: Deep impact analysis with full taxonomy context."""
    
    def __init__(self, taxonomy: TaxonomyContext, gemini: GeminiClient): ...
    
    def analyze_new(self, title: str, summary: str) -> AnalysisResult:
        """Full analysis for a new event (no prior context)."""
    
    def analyze_update(
        self, title: str, summary: str, event: dict
    ) -> AnalysisResult:
        """Update analysis given existing event context."""
```

```python
class AnalysisResult(TypedDict):
    triggers: list[str]
    impacts: list[ImpactResult]
    stage: str              # new | escalating | stable | resolved
    summary: str            # Updated event summary
    is_relevant: bool
    rejection_reason: str | None
```

### Prompt Files (engine/prompts/)

Split current monolithic prompt into:
- `engine/prompts/classify.py` — Tier 1 prompt builder (short, no taxonomy)
- `engine/prompts/analyze_new.py` — Tier 2 new event prompt (full taxonomy)
- `engine/prompts/analyze_update.py` — Tier 2 event update prompt (taxonomy + event context)

### Updated Ingest Pipeline (pipeline/ingest.py)

```
For each unprocessed article:
    1. Tier 1: classifier.classify(title, summary)
       → not relevant? Store in article_impacts (is_relevant=0), done.
       → relevant + event_match? Go to step 2a.
       → relevant + no match? Go to step 2b.
    
    2a. Event update:
        event = event_store.get_event(event_match.event_id)
        result = analyzer.analyze_update(title, summary, event)
        event_store.update_event(event_id, result.summary, result.impacts, result.stage)
        event_store.link_article(event_id, article_id)
        Store in article_impacts (is_relevant=1, triggers, impacts)
    
    2b. New event:
        result = analyzer.analyze_new(title, summary)
        event_id = event_store.create_event(
            name=<derived from title>,
            summary=result.summary,
            triggers=result.triggers,
            impacts=result.impacts,
            category=classification.category,
            seed_article_id=article_id
        )
        Store in article_impacts (is_relevant=1, triggers, impacts, event_id)
```

### Updated article_impacts table

Add event linkage:
```sql
ALTER TABLE article_impacts ADD COLUMN event_id TEXT REFERENCES events(event_id);
ALTER TABLE article_impacts ADD COLUMN tier1_ms INTEGER;   -- classification latency
ALTER TABLE article_impacts ADD COLUMN tier2_ms INTEGER;   -- analysis latency (null if filtered)
```

---

## Cost & Latency Estimates

| Step | Model | Prompt tokens | Time | Cost/article |
|------|-------|--------------|------|-------------|
| Tier 1 (all articles) | flash-lite | ~2K | <1s | ~$0.0001 |
| Tier 2 new event (~20% of articles) | 2.0-flash | ~19K | ~5s | ~$0.001 |
| Tier 2 event update (~10% of articles) | 2.0-flash | ~20K | ~5s | ~$0.001 |

**Savings vs current:** Right now every article gets the 19K-token prompt. With two tiers, ~70% of articles only hit the 2K-token Tier 1. Roughly 5x cheaper per article on average.

---

## Execution Order

```
Step 1: Events schema (database.py + events.py)          -- no LLM deps
Step 2: Tier 1 classifier (classifier.py + classify.py)   -- no event deps
Step 3: Tier 2 refactor (prompts/ split, analyze modes)   -- no event deps
Step 4: Wire ingest.py to use Tier 1 → Tier 2 → Events   -- depends on 1+2+3
Step 5: Test on 100 articles, compare with current results
```

Steps 1, 2, 3 are independent → parallelizable.

---

## Verification

1. `python -m pipeline.ingest --limit 20` — runs the new two-tier pipeline
2. Check: ~80% hit Tier 1 only (no Tier 2 call)
3. Check: events table populated, articles linked
4. Check: same articles classified as relevant as before (no regression)
5. `python -m pipeline.ingest --stats` — shows events, per-event article counts, stages
6. `python -m pipeline.events list` — shows active events
7. `python -m pipeline.events show <event_id>` — shows event detail with linked articles
