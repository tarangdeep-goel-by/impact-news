"""Prompt template for Gemini impact analysis."""

from __future__ import annotations


def build_impact_prompt(t_trees: str, i_trees: str, title: str, summary: str) -> str:
    """Build the full prompt for Gemini impact analysis.

    Args:
        t_trees: Formatted T-world taxonomy hierarchy (from TaxonomyContext.format_t_trees())
        i_trees: Formatted I-world taxonomy hierarchy (from TaxonomyContext.format_i_trees())
        title: Article headline
        summary: Article body/summary text

    Returns:
        Complete prompt string for Gemini.
    """
    return f"""You are a causal impact analyst for Indian citizens. Your job is to identify \
how a news article causally affects the daily life of ordinary Indians.

You have two reference taxonomies:

== TRIGGER TAXONOMY (T-world) ==
These are macro-level triggers — the events that SET OFF causal chains.

{t_trees}

== IMPACT TAXONOMY (I-world) ==
These are citizen-level impacts — the things that CHANGE in people's lives.

{i_trees}

== ARTICLE ==
Title: {title}
Summary: {summary}

== TASK ==
1. Identify which T-world node(s) this article triggers. Use the most specific node that fits.
2. For each triggered node, trace the causal chain to every I-world node that is genuinely affected.
3. For each affected I-world node, assess:
   - probability (0-1): likelihood this node is actually affected by this article
   - magnitude (0-1): severity of the impact if it occurs
   - polarity: +1 if the impact increases/worsens or -1 if it decreases/improves
   - delay: IMMEDIATE, SHORT_TERM, MEDIUM_TERM, or LONG_TERM
   - mechanism: a 1-line causal chain from trigger to impact (e.g. "Crude oil price hike -> refinery costs -> retail petrol price")

== CRITICAL RULES ==
- Impacts MUST be I-world nodes only (from the IMPACT TAXONOMY above). Never return T-world nodes as impacts.
  For example: "nifty_50" is a T-world trigger, NOT an impact. The citizen-level impact is "equity_markets" (I-world).
  Similarly: "aviation_turbine_fuel" is T-world. The citizen impact is "domestic_flight_ticket" (I-world).
- Only genuine causal mechanisms — not vague relatedness or thematic similarity.
- If a whole branch is affected, use the parent node instead of listing every leaf.
- Gold prices do NOT affect wheat or fuel. Stick to real causal chains.
- Probability = likelihood this is affected (not every impact is certain). Magnitude = severity of impact.
- Do NOT list impacts with probability below 0.2 — if it's that unlikely, skip it.
- Use node IDs exactly as they appear in the taxonomy above (snake_case, e.g. "retail_petrol", NOT path-style like "i3:transport:retail_petrol").

== OUTPUT FORMAT ==
Return ONLY valid JSON, no commentary:
{{
  "triggers": ["t_node_id_1", "t_node_id_2"],
  "impacts": [
    {{
      "node": "retail_petrol",
      "probability": 0.95,
      "magnitude": 0.8,
      "polarity": 1,
      "delay": "SHORT_TERM",
      "mechanism": "Crude oil price hike -> refinery costs -> retail petrol price"
    }}
  ]
}}"""
