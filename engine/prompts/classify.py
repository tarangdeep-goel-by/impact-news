"""Tier 1 classification prompt — relevance check + macro shifts + event matching."""

from __future__ import annotations


def build_classify_prompt(
    t_trees: str,
    active_events: list[dict],
    title: str,
    summary: str,
) -> str:
    """Build the Tier 1 classification prompt with T-world taxonomy context.

    Args:
        t_trees: Formatted T-world taxonomy tree (from TaxonomyContext.format_t_trees()).
        active_events: From EventStore.get_event_summary_list().
            Each dict has: event_id, name, macro_shifts, stage, category.
        title: Article headline.
        summary: Article body/summary text.
    """
    # Format active events list with macro_shifts and trajectory for better matching
    if active_events:
        event_lines = []
        for ev in active_events:
            shifts_str = ", ".join(
                f"{s['t_node']} ({s.get('trajectory', '?')})"
                for s in ev.get("macro_shifts", [])[:5]
            )
            ev_summary = ev.get("summary", "")[:150]
            event_lines.append(
                f"- [{ev['event_id']}] {ev['name']} ({ev.get('category', '?')}, {ev['stage']})\n"
                f"  Shifts: [{shifts_str}]\n"
                f"  Summary: {ev_summary}"
            )
        events_block = "Active events (match if this article belongs to one):\n" + "\n".join(event_lines)
    else:
        events_block = "No active events yet."

    return f"""You are a news classifier and trigger identifier for an Indian citizen impact engine.

Your job: (1) determine if an article causally affects ordinary Indians at scale, (2) identify which T-world systems experienced a MATERIAL SHIFT in state, and (3) indicate which I-world impact categories are definitely NOT affected.

== T-WORLD TAXONOMY (Macro Systems) ==
These are macro-level systems. Identify which ones experienced a material shift in state.
Use the most specific node that fits.

{t_trees}

== I-WORLD IMPACT CATEGORIES (for exclusion only) ==
I1: Food & Nutrition
I2: Housing & Utilities
I3: Transport & Mobility
I4: Livelihood & Employment
I5: Personal Finance & Wealth
I6: Health & Physiology
I7: Education & Human Capital
I8: Safety & Security
I9: Local Environmental Quality
I10: Digital Life & Connectivity
I11: Leisure, Culture & Community

Filter out:
- Sports results, celebrity news, entertainment, arts & culture
- Individual crimes, accidents, court cases (unless precedent-setting or policy-changing)
- Opinion pieces, editorials, market commentary, investment advice, brokerage reports, lifestyle articles, personal finance tips
- Market roundups ("Asian shares edge higher", "US stocks drop") — these are observations, not causal events
- Foreign affairs with no India impact chain
- Pure startup funding rounds, M&A, or IPOs unless they signal sector-wide shifts
- Company-specific acquisitions, leadership changes, earnings reports (unless systemically important like top-3 banks)

DO NOT filter out — these ARE relevant:
- Central bank actions (RBI rate changes, forex interventions, liquidity measures)
- Price changes by dominant/major market players (tractors, cement, telecom, fuel, FMCG)
- Trade policy changes (tariffs, WTO disputes, export bans) affecting India's major sectors
- Government policy/regulation changes (GST, subsidies, labour law, IBC reforms)
- Currency/forex policy — rupee movements directly affect import costs

{events_block}

Article:
Title: {title}
Summary: {summary}

Return ONLY valid JSON, no commentary.

If the article is NOT relevant:
{{"relevant": false, "reason": "brief reason"}}

If the article IS relevant:
{{
    "relevant": true,
    "macro_shifts": [
        {{"t_node": "brent_crude", "trajectory": "escalating", "context": "Crude oil prices surged 12% due to Red Sea shipping disruption"}}
    ],
    "exclude_l1s": ["I7", "I11"],
    "event_match": {{"event_id": "abc123", "confidence": 0.9}},
    "event_name": null
}}

Rules for macro_shifts:
- Use exact T-world node IDs from the taxonomy above (snake_case)
- Each shift MUST have:
  - "t_node": the T-world node ID
  - "trajectory": one of "escalating", "deescalating", "status_quo", "disruption"
    - escalating: the situation is getting worse/more intense
    - deescalating: the situation is calming down/reversing
    - status_quo: expectations were defied — e.g., RBI holds rate when cut was expected. The NON-event is the event.
    - disruption: sudden, unexpected shift (new sanctions, natural disaster, policy shock)
  - "context": 1-line explanation of WHAT changed and WHY
- Find ALL T-world systems that experienced a material shift. Do NOT cap at 1-3.
- If you cannot identify a SPECIFIC shift from the taxonomy, the article is NOT relevant.
- The shift must be something the article REPORTS AS HAPPENING, not something tangentially related.

Rules for exclude_l1s:
- List I-world L1 category codes that are DEFINITELY NOT causally affected by the identified triggers
- Be conservative: only exclude categories you are CERTAIN have no causal link
- When in doubt, do NOT exclude — the next stage will handle precise filtering
- Example: a shipping crisis definitely does NOT affect I7 (Education) or I11 (Leisure)

Rules for event matching:
- Match on ROOT CAUSE, not surface topic. An article about "textile exports hit by shipping costs" and an event about "Middle East energy supply disruption" share the SAME root cause (the conflict). They should match.
- Read each event's summary and triggers carefully. If the article's situation is CAUSED BY or is a CONSEQUENCE OF an existing event, it belongs to that event.
- Different sectors affected by the same crisis = same event. Government responses to a crisis = same event.
- Only match if confidence >= 0.7. If unsure, set event_match to null (creates a new event)
- An article can only match ONE event. Pick the closest root cause.

Rules for event_name (only when event_match is null):
- Short, descriptive name for the new event (3-7 words)
- Use title case
- Focus on WHAT is happening, not the article headline"""
