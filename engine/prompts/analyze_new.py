"""Tier 2 prompt for analyzing a new event — cascading multi-order impact analysis."""

from __future__ import annotations


def build_analyze_new_prompt(
    macro_shifts: list[dict],
    i_trees: str,
    title: str,
    summary: str,
) -> str:
    """Build Tier 2 prompt for a new event — cascading impact analysis.

    Args:
        macro_shifts: List of {t_node, trajectory, context} from Tier 1.
        i_trees: Filtered I-world taxonomy (excluding irrelevant L1 categories).
        title: Article headline.
        summary: Article body/summary text.
    """
    # Format macro shifts block
    shift_lines = []
    for s in macro_shifts:
        shift_lines.append(f"- {s['t_node']} [{s.get('trajectory', '?')}]: {s.get('context', '')}")
    shifts_block = "\n".join(shift_lines) if shift_lines else "(none identified)"

    return f"""You are a causal impact analyst for Indian citizens. Your job: trace how macro-level shifts cascade into citizen-level impacts across multiple orders.

== ACTIVE MACRO SHIFTS ==
{shifts_block}

== IMPACT TAXONOMY (I-world) ==
These are citizen-level impacts. Your output MUST use LEAF node IDs (snake_case) from this taxonomy. Never use L1 or L2 category IDs.

{i_trees}

== ARTICLE ==
Title: {title}
Summary: {summary}

== TASK: MULTI-ORDER IMPACT CASCADE ==

Think in three orders of impact:

**1st order (direct):** What changes IMMEDIATELY for citizens because of this event?
Example: Oil price spike → petrol_price, diesel_price go up.

**2nd order (knock-on):** What changes BECAUSE of the 1st order effects?
Example: Diesel up → transport costs rise → packaged_foods_and_beverages prices rise, intercity_bus_fare increases.

**3rd order (systemic):** What broader changes ripple out from the 2nd order?
Example: Higher transport + food costs → factory_worker_wages under pressure, restaurant_and_street_food prices rise.

For EACH impact, rate three dimensions:
- **probability** (0.0-1.0): How likely is this to actually materialize?
  - 1st order: typically 0.7-1.0
  - 2nd order: typically 0.4-0.8
  - 3rd order: typically 0.2-0.5
- **magnitude** (0.0-1.0): How severely does this affect the average citizen?
- **delay_days** (integer): When do citizens feel this? 1st order = days, 2nd = weeks, 3rd = months.

Target: 6-10 impacts total across all three orders. Aim for 2-4 per order.

== CRITICAL RULES ==
1. Use ONLY leaf-level node IDs from the taxonomy. Never output L1/L2 category names.
2. Every impact needs a clear causal chain — not thematic association.
3. Include the order (1, 2, or 3) in each impact.
4. Do NOT skip 2nd and 3rd order effects — this is the most important part.
5. driving_t_nodes must reference T-nodes from the macro shifts above.
6. Think about INDIAN citizens specifically — rickshaw drivers, housewives, factory workers, farmers, students, gig workers.
7. For each impact, assign a geographic "scope":
   - "national" — policy/price changes that affect all of India (petrol price, income tax, RBI rate, food commodities)
   - "state:<StateName>" — state-level policy (electricity tariff, state board exams, state govt jobs). Use official state name.
   - "city:<CityName>" — city-specific disruption (traffic diversion, metro delay, local flooding, rent trends). Use common city name.
   Default to "national" if the impact is not geographically limited.

If the article has NO mass citizen impact, return:
{{"no_impact": true, "reason": "brief reason"}}

== OUTPUT FORMAT ==
Return ONLY valid JSON:
{{
  "micro_impacts": [
    {{
      "i_node": "petrol_price",
      "order": 1,
      "trajectory": "escalating",
      "probability": 0.95,
      "magnitude": 0.8,
      "delay_days": 3,
      "rationale": "1st order: Crude spike directly raises OMC import costs, passed to pump prices within days",
      "driving_t_nodes": ["brent_crude"],
      "scope": "national"
    }},
    {{
      "i_node": "packaged_foods_and_beverages",
      "order": 2,
      "trajectory": "escalating",
      "probability": 0.7,
      "magnitude": 0.4,
      "delay_days": 30,
      "rationale": "2nd order: Higher diesel raises transport costs for FMCG distribution, passed to MRP in 2-4 weeks",
      "driving_t_nodes": ["brent_crude"],
      "scope": "national"
    }},
    {{
      "i_node": "factory_worker_wages",
      "order": 3,
      "trajectory": "deescalating",
      "probability": 0.3,
      "magnitude": 0.3,
      "delay_days": 90,
      "rationale": "3rd order: Sustained cost pressure squeezes MSME margins, leading to wage stagnation or cuts",
      "driving_t_nodes": ["brent_crude"],
      "scope": "national"
    }}
  ],
  "summary": "2-3 line summary of the event and its citizen-level cascade.",
  "stage": "new"
}}"""
