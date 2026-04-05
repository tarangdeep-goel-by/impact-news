"""Tier 2 prompt for updating an existing event — delta output only."""

from __future__ import annotations


def build_analyze_update_prompt(
    macro_shifts: list[dict],
    i_trees: str,
    title: str,
    summary: str,
    compressed_state: str,
) -> str:
    """Build Tier 2 prompt for updating an existing event — delta output only.

    Args:
        macro_shifts: List of {t_node, trajectory, context} — NEW shifts from Tier 1 for this article.
        i_trees: Filtered I-world taxonomy.
        title: New article headline.
        summary: New article body.
        compressed_state: Compressed current state from EventStore.get_compressed_state().
    """
    # Format new macro shifts
    shift_lines = []
    for s in macro_shifts:
        shift_lines.append(f"- {s['t_node']} [{s.get('trajectory', '?')}]: {s.get('context', '')}")
    shifts_block = "\n".join(shift_lines) if shift_lines else "(none identified)"

    return f"""You are a causal impact analyst for Indian citizens. You are UPDATING an existing event's impact assessment based on a new article.

== CURRENT EVENT STATE ==
{compressed_state}

== NEW MACRO SHIFTS FROM THIS ARTICLE ==
{shifts_block}

== IMPACT TAXONOMY (I-world) ==
{i_trees}

== NEW ARTICLE ==
Title: {title}
Summary: {summary}

== TASK ==
Given the current event state and this new article, determine what CHANGES:
1. **New impacts**: citizen impacts not previously identified
2. **Updated impacts**: existing impacts whose probability, magnitude, or trajectory changed
3. **Do NOT repeat unchanged impacts** — they are retained automatically

For each changed or new impact:
- i_node, trajectory, probability, magnitude, delay_days, rationale, driving_t_nodes

Also determine:
- What stage is this event in? (new/escalating/stable/resolved)
- Updated 2-3 line event summary incorporating this new development.

== CRITICAL RULES ==
- Impacts MUST be I-world nodes only from the taxonomy above. Use exact snake_case IDs.
- Only genuine causal mechanisms — not vague relatedness.
- Do NOT list impacts with probability below 0.2.
- delay_days must be a positive integer.
- driving_t_nodes must reference T-nodes from the active macro shifts (both existing and new).
- Output ONLY impacts that are NEW or CHANGED. Unchanged impacts are preserved automatically.

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
      "rationale": "Crude spike + rupee weakening both push import bill up, OMCs pass cost to consumers",
      "driving_t_nodes": ["brent_crude", "usd_inr_exchange"]
    }}
  ],
  "summary": "Updated 2-3 line summary.",
  "stage": "escalating"
}}"""
