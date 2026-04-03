"""Tier 2 prompt for updating an existing event's causal edges (upsert)."""

from __future__ import annotations

import json


def build_analyze_update_prompt(
    triggers: list[dict],
    i_trees: str,
    title: str,
    summary: str,
    existing_instances: list[dict],
) -> str:
    """Build Tier 2 prompt for updating an existing event's impact assessment.

    Args:
        triggers: List of {t_node, context} from Tier 1 classifier.
        i_trees: Filtered I-world taxonomy.
        title: New article headline.
        summary: New article body.
        existing_instances: Current TriggerInstances with IDs from EventStore.get_event_edges().
            Each: {id, t_node, context, edges: [{id, i_node, probability, magnitude, delay_days, polarity, mechanism}]}
    """
    # Format triggers from Tier 1
    trigger_lines = []
    for t in triggers:
        trigger_lines.append(f"- {t['t_node']}: {t.get('context', '')}")
    triggers_block = "\n".join(trigger_lines) if trigger_lines else "(none identified)"

    # Format existing causal edges
    if existing_instances:
        existing_block = json.dumps(existing_instances, indent=2)
    else:
        existing_block = "(no existing edges — treat as new analysis)"

    return f"""You are a causal impact analyst for Indian citizens. You are UPDATING an existing event's impact assessment based on a new article.

== TRIGGERS IDENTIFIED IN NEW ARTICLE ==
{triggers_block}

== EXISTING CAUSAL EDGES (with IDs) ==
{existing_block}

== IMPACT TAXONOMY (I-world) ==
{i_trees}

== NEW ARTICLE ==
Title: {title}
Summary: {summary}

== TASK ==
Given this new article, produce an UPDATED set of causal edges using the UPSERT pattern:

1. **UPDATE** existing edges: If the article changes the probability, magnitude, or delay of an existing edge, output it WITH its existing "id" field.
2. **INSERT** new edges: If the article reveals new impacts, output them WITHOUT an "id" field.
3. **REMOVE** by omission: If an impact edge is no longer relevant, simply omit it from the output.
4. **NEW TRIGGERS**: If the article introduces a new trigger not in the existing edges, add a new trigger_instance WITHOUT an "id" field.

Also determine:
- What stage is this event in? (new/escalating/stable/resolved)
- Updated 2-3 line event summary incorporating this new development.

== CRITICAL RULES ==
- Impacts MUST be I-world nodes only from the taxonomy above. Use exact snake_case IDs.
- Only genuine causal mechanisms — not vague relatedness.
- Do NOT list impacts with probability below 0.2.
- delay_days must be a positive integer.
- Do NOT accumulate tangential triggers. Only include triggers with direct causal chains to citizen impacts.
- The output should reflect the CUMULATIVE state of the event, not just this article.
- Preserve existing edge IDs when updating — this is critical for tracking provenance.

== OUTPUT FORMAT ==
Return ONLY valid JSON:
{{
  "trigger_instances": [
    {{
      "id": "existing-trigger-id",
      "t_node": "brent_crude",
      "context": "Updated: Crude prices still elevated after Red Sea attacks",
      "edges": [
        {{"id": "existing-edge-id", "i_node": "retail_petrol", "probability": 0.95, "magnitude": 0.85, "delay_days": 5, "polarity": 1, "mechanism": "Updated mechanism"}},
        {{"i_node": "lpg_cylinder", "probability": 0.7, "magnitude": 0.5, "delay_days": 14, "polarity": 1, "mechanism": "New impact discovered"}}
      ]
    }},
    {{
      "t_node": "ministry_of_finance",
      "context": "New trigger: government announces fuel subsidy",
      "edges": [
        {{"i_node": "retail_diesel", "probability": 0.8, "magnitude": -0.3, "delay_days": 7, "polarity": -1, "mechanism": "Subsidy reduces pump price"}}
      ]
    }}
  ],
  "summary": "Updated 2-3 line summary.",
  "stage": "escalating"
}}"""
