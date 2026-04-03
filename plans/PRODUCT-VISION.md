# Product Vision: Impact News

## Core Idea

"Not what interests you. What affects you."

A causal news engine that tells Indian citizens what's happening in the world that will impact their daily life — their wallet, their commute, their job, their food prices. Not engagement-driven recommendations, but causal chain reasoning from macro events to personal impact.

## Architecture (Current + Planned)

### What's Built

**Ingestion pipeline:** 14 RSS feeds → async collection → MinHash dedup → SQLite. Articles classified by Gemini LLM in one call: relevant (with T-triggers + I-impacts) or no_impact (with reason). 22% of articles pass the relevance filter.

**Taxonomy:** 769 nodes across two semantic worlds:
- T-world (237 nodes, 5 L1s): Macro triggers — crude oil, RBI policy, monsoon systems
- I-world (532 nodes, 11 L1s): Citizen impacts — retail petrol, home loan EMI, school fees

**LLM engine:** Full T+I taxonomy injected into Gemini prompt. Returns structured JSON with triggers, impacts (probability, magnitude, polarity, delay, causal mechanism). Model: gemini-3.1-flash-lite-preview.

**Eval:** 19 golden test cases (80% recall, 83% precision). 16 real-world ground truth events (0.460 NDCG).

### What's Next: Agent-Based Event Tracking

The current system processes articles independently. The next evolution is event-aware: articles cluster into events, events evolve over time, and impact assessments update as new information arrives.

**Agent architecture (not hardcoded pipeline):**

An agent receives each new article and has tools to investigate and act:

```
New Article → Agent
  Agent has tools:
    - search_events(query)           → find similar active events
    - get_event(event_id)            → full context (summary, impacts, article history)
    - create_event(name, summary, triggers, impacts) → start new event
    - update_event(event_id, new_impacts, summary)   → evolve existing event
    - classify_article(title, summary)               → relevant / not relevant (fast)
    - analyze_impacts(article, event_context)         → deep T/I analysis (reasoning model)
  Agent reasons and acts:
    1. Is this article relevant to mass citizens?
    2. Does it belong to an existing event?
    3. What's new or changed? Update impacts accordingly.
```

The LLM is the brain that decides what to do. Tools are the hands. This naturally handles the two-tier model split — the agent uses a fast classifier first, and only calls the deep reasoning model when needed.

**Event model:**

Events are living entities that progress through stages:

```
Event {
    id, name, summary (running, updated with each article)
    triggers: [T-nodes]
    current_impacts: [{node, probability, magnitude, polarity, delay, mechanism}]
    stage: new → escalating → stabilizing → resolved
    first_seen, last_updated, article_count
}
```

When a new article arrives for an existing event:
- Probabilities may increase (more confirmation) or decrease (situation easing)
- New impacts may appear that weren't visible from earlier articles
- Delays may shift (was MEDIUM_TERM, now IMMEDIATE — it's happening)
- Magnitude may change (government announces subsidy → fuel impact drops)

**Event lifecycle:**
- New event: first article, fresh impact assessment
- Evolving event: new articles update the impact picture
- Stale event: no articles for N days → mark resolved
- Resolved event: "this is over, here's what happened"

### Two-Tier LLM Design

Not two hardcoded stages — the agent decides when to go deep:

- **Fast model (flash-lite):** Classification, event matching, simple queries. <1s, cheap. Used for "is this relevant?" and "does this match event X?"
- **Reasoning model (flash/pro):** Full impact analysis with taxonomy context. ~3-5s, heavier. Used when the agent needs to assess causal chains, update event impacts, or reason about progression.

The agent uses judgment about which model to call. Most articles hit the fast model and stop (no_impact). Only relevant articles that need deep analysis trigger the reasoning model.

### User Profiles (Not Yet Built)

The critical missing piece: knowing who the user is.

```
User Profile {
    city, employment, industry, housing, transport, loans,
    dependents, investments, top_expenses, income_range
}
  → maps to I-world nodes with exposure weights
  → e.g., "has car + home loan" → retail_petrol(1.0), home_loan_emi(1.0)
```

**Matching:** Article/event impacts × user exposed I-nodes = personal relevance score + explanation.

**User notification strategy:**
- New event that affects them → immediate alert
- Existing event with significant impact change → update notification
- Upcoming delayed impact approaching → reminder
- Event resolved → closure summary

### End-to-End User Experience

```
User onboards: "I live in Bangalore, work in IT, have a car, home loan, invest in stocks"
  → System infers: retail_petrol, home_loan_emi, equity_investments, it_sector_jobs, ...

Article arrives: "RBI hikes repo rate by 25 basis points"
  → Agent classifies: relevant, links to "RBI Monetary Tightening" event
  → Agent updates event: home_loan_emi prob=0.95, fd_rates prob=0.8
  → User gets: "Your home loan EMI is likely going up. RBI hiked rates again.
                This is the 3rd hike this year. Impact: Rs 1,500-2,000/month increase.
                Timeline: next billing cycle (IMMEDIATE)."

Next week: "Banks announce new lending rates"
  → Agent updates same event: home_loan_emi prob=1.0, delay=IMMEDIATE
  → User gets: "Update: SBI just raised lending rates. Your EMI increase is now confirmed."
```

## Principles

1. **One Gemini call per article** for classification. Store results permanently. Don't re-process.
2. **Agent, not pipeline.** The LLM decides what to do, not hardcoded if/else chains.
3. **Events, not articles.** Users care about "what's happening with oil prices," not individual articles.
4. **Impacts evolve.** Probability, magnitude, and delay change as events progress. Early = speculative, late = confirmed.
5. **Aggressive filtering.** Most news doesn't affect citizens at scale. Sports, celebrity, petty crime, opinion pieces → filtered.
6. **Taxonomy as vocabulary, not engine.** T/I trees give the LLM a controlled vocabulary to reason with. The LLM does the causal reasoning, not graph traversal.
