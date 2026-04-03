"""Tier 2 prompt for analyzing a new event — impacts only, triggers pre-identified."""

from __future__ import annotations


def build_analyze_new_prompt(
    triggers: list[dict],
    i_trees: str,
    title: str,
    summary: str,
) -> str:
    """Build Tier 2 prompt for a new article/event.

    Args:
        triggers: List of {t_node, context} from Tier 1 classifier.
        i_trees: Filtered I-world taxonomy (excluding irrelevant L1 categories).
        title: Article headline.
        summary: Article body/summary text.
    """
    # Format triggers block
    trigger_lines = []
    for t in triggers:
        trigger_lines.append(f"- {t['t_node']}: {t.get('context', '')}")
    triggers_block = "\n".join(trigger_lines) if trigger_lines else "(none identified)"

    return f"""You are a causal impact analyst for Indian citizens. Triggers have already been identified for this article. Your job is to trace each trigger to its citizen-level IMPACTS.

== IDENTIFIED TRIGGERS ==
{triggers_block}

== IMPACT TAXONOMY (I-world) ==
These are citizen-level impacts — the things that CHANGE in people's lives.
Your output MUST use node IDs from this taxonomy.

{i_trees}

== ARTICLE ==
Title: {title}
Summary: {summary}

== TASK ==
For each trigger above, identify which I-world nodes are causally affected:
- probability (0-1): likelihood this impact materializes
- magnitude (0-1): severity of the impact
- delay_days: estimated days until citizens feel this impact (e.g., 3 for immediate, 14 for short-term, 60 for medium-term, 180 for long-term)
- polarity: +1 if it increases/worsens costs or -1 if it decreases/improves
- mechanism: 1-line causal chain from trigger to impact

Group impacts under their trigger. One trigger can have multiple impacts.

If the article actually has NO mass citizen impact despite being flagged, return:
{{"no_impact": true, "reason": "brief reason"}}

== CRITICAL RULES ==
- Impacts MUST be I-world nodes only from the taxonomy above. Use exact snake_case IDs.
- Only genuine causal mechanisms — not vague relatedness or thematic similarity.
- If a whole branch is affected, use the parent node instead of listing every leaf.
- Do NOT list impacts with probability below 0.2.
- delay_days must be a positive integer (not a string like "SHORT_TERM").
- 2-8 impact edges per trigger. Focus on the most significant ones.

== OUTPUT FORMAT ==
Return ONLY valid JSON:
{{
  "trigger_instances": [
    {{
      "t_node": "brent_crude",
      "context": "Crude oil prices surged due to Red Sea disruption",
      "edges": [
        {{
          "i_node": "retail_petrol",
          "probability": 0.95,
          "magnitude": 0.8,
          "delay_days": 7,
          "polarity": 1,
          "mechanism": "Crude oil price hike -> refinery costs -> retail petrol price"
        }}
      ]
    }}
  ],
  "summary": "2-3 line summary of this event and its citizen-level implications.",
  "stage": "new"
}}"""
