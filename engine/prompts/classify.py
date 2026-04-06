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

== RELEVANCE BIAS: WHEN IN DOUBT, INCLUDE ==
Missing a relevant article is WORSE than including an irrelevant one. Err on the side of inclusion.

CLEARLY RELEVANT:
- Policy actions, regulations, court orders, legislative changes
- Realized economic data: GDP, exports, inflation, employment, forex reserves, commodity prices
- Market movements with identifiable causes: oil surges, stock crashes, rupee moves
- Crises, conflicts, natural disasters and their ripple effects on India
- Foreign policy/legislation that affects Indian trade, diaspora, or supply chains
- Government responses to crises (export bans, relief flights, price controls)
- Draft regulations and proposals by RBI/SEBI (these WILL become policy)
- Significant data releases even if retrospective (exports jumped 9%, complaints surged 60%)
- Industry-wide distress or structural shifts (MSME shutdowns, worker exodus, sector-wide tariffs)

CLEARLY NOT RELEVANT — filter these out:
- Sports scores, celebrity gossip, entertainment, lifestyle
- Individual company earnings, leadership changes, funding rounds (unless top-5 systemically important)
- Personal finance tips, "check fuel price in your city today"
- Individual crimes or accidents (unless systemic)

ALSO FILTER — these look relevant but are NOT actionable macro shifts:
- **Pure opinion/explainer pieces with NO underlying event:** "architecture of resilience", "how India managed disruptions better", F&O technical analysis, investment advice. Key test: remove the expert's opinion — is there still a NEW fact? If not, filter.
- **Industry body complaints/lobbying without policy action:** "EEPC says steel import curbs will hurt MSMEs", "NAREDCO says sector short 20 lakh workers". These are stakeholder opinions, not shifts.
- **Company-specific news:** One company's dispute/profile/pivot is not macro. "Sun Pharma exposed to tariffs" = company analysis. "India bans pharma exports" = macro shift.
- **Market roundups without cause:** "Asian shares edge higher", "stocks gain in volatile week". No causal trigger = not relevant.

DO NOT filter these even if they SOUND like analysis:
- **Foreign legislation/policy that passed or is being enacted:** "US Big Beautiful Bill pulls back on solar/EVs" — this IS a law. "US imposes 1% remittance tax" — this IS enacted policy. The analytical framing doesn't make the underlying event less real.
- **Quantified risk assessments tied to real events:** "$30B exports at risk from tariffs" — the tariffs ARE happening, the impact estimate is news. "US tariffs could knock 50bps off growth" — if tariffs exist, the GDP impact analysis is actionable.
- **Trade deals in progress:** "India-UK FTA signed", "India talks trade with China for first time since RCEP" — diplomatic events even if reported analytically.
- **Central bank/govt signaling that moves markets:** "RBI signals rate cut", "Food inflation likely to ease: RBI bulletin" — these move bond yields and expectations even without formal action.
- **World Bank/IMF forecast revisions:** These change sovereign ratings, capital flows, and policy response. They ARE events.
- Company-specific news (earnings, leadership, M&A) for non-systemically-important companies
- Trivial daily updates: "check fuel price in your city", "bank holiday list"

DO NOT filter out (even if they feel like commentary):
- Central bank ACTIONS and draft regulations — these move markets (but filter RBI Governor speeches that don't announce action)
- Government policy responses to crises — export bans, relief schemes, price controls
- Realized data releases — export growth, employment data, inflation numbers, forex reserves
- Industry-wide distress — MSME shutdowns, sector layoffs, supply chain disruptions
- Draft regulations by RBI/SEBI/TRAI — markets price these in immediately

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
        {{"t_node": "global_crude_oil", "trajectory": "escalating", "context": "Crude oil prices surged 12% due to Red Sea shipping disruption"}}
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

T2 vs T3 disambiguation (IMPORTANT):
- T2 = DOMESTIC governance. Use when INDIA'S government/regulator takes action.
  - "India bans wheat exports" → trade_and_tariff_policy (T2, India enacted it)
  - "RBI cuts repo rate" → monetary_policy (T2, RBI is domestic)
  - "SEBI tightens F&O rules" → market_and_corporate_regulation (T2)
- T3 = EXTERNAL forces. Use when a FOREIGN actor/event impacts India.
  - "Trump imposes tariffs on Indian goods" → trade_wars_and_tariffs (T3, US action)
  - "OPEC cuts production" → energy_cartel_actions (T3, foreign cartel)
  - "US-Iran war disrupts Hormuz" → third_party_geopolitical_conflicts (T3)
- If BOTH: India responds to a foreign event, tag BOTH T2 and T3 nodes.
  - "India bans petrol exports amid Iran war" → trade_and_tariff_policy (T2) + third_party_geopolitical_conflicts (T3)

T1 vs T2 disambiguation:
- T1 = MARKET OUTCOMES (measured data). Use for realized prices, indices, flows.
  - "Forex reserves drop $10B" → forex_reserves_india (T1, measured outcome)
  - "Rupee gains 1.8%" → inr_exchange_rates (T1, market movement)
- T2 = POLICY ACTIONS (decisions). Use for rules, regulations, interventions.
  - "RBI bans NDF rebooking" → banking_and_credit_regulation (T2, regulatory action)
  - If an article covers BOTH the action AND its market outcome, tag both.

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
