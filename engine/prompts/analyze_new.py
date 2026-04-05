"""Tier 2 prompt for analyzing a new event — flat M:N impact analysis."""

from __future__ import annotations


def build_analyze_new_prompt(
    macro_shifts: list[dict],
    i_trees: str,
    title: str,
    summary: str,
) -> str:
    """Build Tier 2 prompt for a new event — flat M:N impact analysis.

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

    return f"""You are a causal impact analyst for Indian citizens. Macro-level shifts have been identified. Your job is to determine how these shifts COMBINE to affect citizens.

== ACTIVE MACRO SHIFTS ==
{shifts_block}

== IMPACT TAXONOMY (I-world) ==
These are citizen-level impacts — the things that CHANGE in people's lives.
Your output MUST use node IDs from this taxonomy.

{i_trees}

== ARTICLE ==
Title: {title}
Summary: {summary}

== TASK ==
Analyze the COMBINED effect of ALL macro shifts on citizens. Key rules:
- A single impact can be driven by MULTIPLE shifts (e.g., retail_petrol driven by brent_crude + usd_inr_exchange)
- Think about compounding effects — two shifts pushing in the same direction amplify the impact
- Think about offsetting effects — a shift and a policy response may cancel out

For each citizen impact:
- i_node: exact I-world node ID from taxonomy (snake_case)
- trajectory: escalating | deescalating | status_quo
- probability (0-1): likelihood this impact materializes
- magnitude (0-1): severity of the impact
- delay_days: estimated days until citizens feel this (positive integer)
- rationale: 1-line explaining the causal chain from shift(s) to impact
- driving_t_nodes: list of T-node IDs that drive this impact

If the article has NO mass citizen impact despite being flagged, return:
{{"no_impact": true, "reason": "brief reason"}}

== CRITICAL RULES ==
- Impacts MUST be I-world nodes only from the taxonomy above. Use exact snake_case IDs.
- Only genuine causal mechanisms — not vague relatedness or thematic similarity.
- If a whole branch is affected, use the parent node instead of listing every leaf.
- Do NOT list impacts with probability below 0.2.
- delay_days must be a positive integer.
- driving_t_nodes must reference T-nodes from the macro shifts above.
- Include ALL genuinely affected I-nodes. Black swan events can have many impacts.

== OUTPUT FORMAT ==
Return ONLY valid JSON:
{{
  "micro_impacts": [
    {{
      "i_node": "retail_petrol",
      "trajectory": "escalating",
      "probability": 0.95,
      "magnitude": 0.8,
      "delay_days": 7,
      "rationale": "Crude spike + rupee weakening both push import bill up, OMCs will pass to consumers",
      "driving_t_nodes": ["brent_crude", "usd_inr_exchange"]
    }}
  ],
  "summary": "2-3 line summary of this event and its citizen-level implications.",
  "stage": "new"
}}"""
