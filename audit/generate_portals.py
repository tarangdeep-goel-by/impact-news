"""Generate I→I cross-L1 portal edges using Gemini 3.1 Pro.

Sends all 11 Impact trees in one prompt and asks Gemini to identify
causal edges ACROSS different L1 trees.

Usage:
    python -m audit.generate_portals
    python -m audit.generate_portals --dry-run
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import yaml

OUTPUT_DIR = Path("taxonomy/eval_results")
LATERAL_DIR = Path("taxonomy/laterals")


def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        sys.exit(1)
    from google import genai
    return genai.Client(api_key=api_key)


def build_all_trees(G) -> str:
    """Build compact tree text for all I-world L1s."""
    sections = []
    for cat_id in [f"I{i}" for i in range(1, 12)]:
        nodes = [(n, d) for n, d in G.nodes(data=True) if d.get("category") == cat_id]
        l1_name = next((d.get("aliases", [""])[0] for n, d in nodes if d.get("level") == 1), cat_id)

        nodes_by_id = {n: d for n, d in nodes}
        lines = [f"## {cat_id}: {l1_name}"]

        def render(node_id, indent=0):
            d = nodes_by_id.get(node_id, {})
            prefix = "  " * indent
            level = d.get("level", "?")
            is_cat = " [CATEGORY]" if d.get("is_category") else ""
            alias = d.get("aliases", [""])[0][:30] if d.get("aliases") else ""
            alias_str = f" ({alias})" if alias else ""
            lines.append(f"{prefix}L{level}: {node_id}{alias_str}{is_cat}")
            for succ in sorted(G.successors(node_id)):
                if G[node_id][succ].get("type") == "CONTAINS" and succ in nodes_by_id:
                    render(succ, indent + 1)

        root = next((n for n, d in nodes if d.get("level") == 1), None)
        if root:
            render(root)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def build_prompt(trees_text: str) -> str:
    return f"""You are an expert on Indian economics and citizen-level causal cascades. You are building cross-L1 portal edges for a causal knowledge graph that traces how macro events affect Indian citizens.

## Task

Generate **cross-L1 portal edges** — causal edges BETWEEN different Impact L1 trees. These model how one life domain causally affects another for Indian citizens.

Key citizen cascades to consider:
- Environment (I9) → Health (I6): pollution → respiratory illness, heat → heatstroke
- Environment (I9) → Education (I7): pollution/flooding → school closures
- Environment (I9) → Livelihood (I4): heat → outdoor labor disruption
- Food (I1) → Finance (I5): food inflation → savings erosion
- Transport (I3) → Food (I1): freight/fuel costs → food prices
- Livelihood (I4) → Finance (I5): income changes → loan stress, savings
- Digital (I10) → Finance (I5): payment infra → banking access
- Health (I6) → Livelihood (I4): illness → lost wages
- Health (I6) → Finance (I5): medical costs → savings drain
- Housing (I2) → Finance (I5): rent/utility costs → savings
- Safety (I8) → Livelihood (I4): crime → business disruption
- Education (I7) → Livelihood (I4): skills → employment

These are starting points — identify ALL defensible cross-L1 causal edges, not just these.

## All 11 Impact Trees

```
{trees_text}
```

## Rules (STRICT)

### Targeting (Rule 20)
- **NEVER target L2 nodes** (marked [CATEGORY]). L2s are organizational folders.
- **Target L3 by default.** CONTAINS propagation pushes scores to L4 children.
- **Target L4 only when** the effect hits only ONE specific child under an L3.
- **Homogeneity Test:** Before targeting L3: "Does this source affect ALL L4 children under this L3 equally?" YES → L3. NO → specific L4s.

### Edge Type (Rule 12b — pick FIRST that fits)
1. **PRODUCES** — A literally creates/generates B
2. **SUPPLIES** — A provides physical goods/data/labor to B
3. **FUNDS** — A directly pays for or financially backs B
4. **DISRUPTS** — A physically blocks, breaks, or halts B
5. **DEPENDS_ON** — B structurally cannot function without A
6. **AFFECTS** — *Fallback only.* A changes price/frequency/quality of B

### Weight = causal pass-through strength (NOT importance)
- 0.9-1.0: Almost 1:1 pass-through
- 0.6-0.8: Strong but buffered
- 0.3-0.5: Noticeable but diluted
- Avoid below 0.3

### Polarity
- +1: source increases → target increases
- -1: source increases → target decreases
- Think about each entity's implied axis (price, volume, quality, availability)

### Delay
- IMMEDIATE / SHORT_TERM / MEDIUM_TERM / LONG_TERM

### Description (Rule 15)
Must explain the causal MECHANISM, not restate the edge.

### DAG (Rule 14)
No cycles. If A→B exists, B→A is forbidden.

### Quality
Only generate edges with clear, defensible causal mechanisms in India. Better to have 40 precise edges than 100 vague ones. Every edge must pass the "would a domain expert agree?" test.

## Output Format

Return ONLY a YAML array. No commentary. Include source_l1 and target_l1 for traceability:

```yaml
- from: source_node_id
  to: target_node_id
  type: AFFECTS
  weight: 0.7
  polarity: 1
  delay: SHORT_TERM
  source_l1: I3
  target_l1: I1
  description: "Explanation of causal mechanism"
```

Generate the cross-L1 portal edges now."""


def parse_yaml_response(response: str) -> list[dict]:
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        edges = yaml.safe_load(text)
        return edges if isinstance(edges, list) else []
    except yaml.YAMLError as e:
        print(f"  YAML parse error: {e}")
        return []


def validate_edges(edges: list[dict], G) -> list[dict]:
    i_nodes = {n for n, d in G.nodes(data=True) if d.get("category", "").startswith("I")}
    l2_nodes = {n for n, d in G.nodes(data=True) if d.get("category", "").startswith("I") and d.get("level") == 2}
    valid_types = {"AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES",
                   "DEPENDS_ON", "FUNDS", "COMPETES_WITH", "EMPLOYS", "MANAGES"}

    valid = []
    for i, edge in enumerate(edges):
        src = edge.get("from", edge.get("source", ""))
        dst = edge.get("to", edge.get("target", ""))
        etype = edge.get("type", edge.get("relation_type", ""))

        # Normalize field names
        edge["from"] = src
        edge["to"] = dst
        edge["type"] = etype

        issues = []
        if src not in i_nodes:
            issues.append(f"source '{src}' not in I-world")
        if dst not in i_nodes:
            issues.append(f"target '{dst}' not in I-world")
        if dst in l2_nodes:
            issues.append(f"target '{dst}' is L2 (Rule 20)")
        if etype not in valid_types:
            issues.append(f"invalid type '{etype}'")
        if not edge.get("description"):
            issues.append("missing description")
        if src == dst:
            issues.append("self-loop")

        # Check it's actually cross-L1
        src_cat = G.nodes[src].get("category", "") if G.has_node(src) else ""
        dst_cat = G.nodes[dst].get("category", "") if G.has_node(dst) else ""
        if src_cat == dst_cat:
            issues.append(f"same L1 ({src_cat}) — not a portal edge")

        if issues:
            print(f"  REJECTED #{i+1} ({src}→{dst}): {'; '.join(issues)}")
        else:
            valid.append(edge)

    return valid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults
    G = TaxonomyMerger().merge(apply_patches=False)
    apply_defaults(G)

    trees_text = build_all_trees(G)

    if args.dry_run:
        print(trees_text)
        print(f"\n({len(trees_text)} chars — would send to Gemini)")
        return

    client = get_gemini_client()
    from google.genai import types

    prompt = build_prompt(trees_text)

    chat = client.chats.create(
        model="gemini-3.1-pro-preview",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="high", include_thoughts=True),
            temperature=0.3,
        ),
    )

    print(f"\n{'='*60}")
    print(f"Generating cross-L1 portals ({len(prompt)} chars)...")
    print(f"{'='*60}")

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = chat.send_message(prompt)
            break
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e):
                wait = 30 * (attempt + 1)
                print(f"  Retry {attempt + 1}/{max_retries} — waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    else:
        print("FAILED")
        return

    answer, thinking = "", ""
    for part in response.candidates[0].content.parts:
        if part.thought:
            thinking += part.text + "\n"
        else:
            answer += part.text + "\n"

    usage = response.usage_metadata
    print(f"  Thinking: {usage.thoughts_token_count} tokens")
    print(f"  Output: {usage.candidates_token_count} tokens")
    print(f"  Total: {usage.total_token_count} tokens")

    edges = parse_yaml_response(answer.strip())
    print(f"  Parsed {len(edges)} edges")

    valid = validate_edges(edges, G)
    print(f"  Validated: {len(valid)}/{len(edges)} passed")

    # Save
    LATERAL_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    yaml_path = LATERAL_DIR / "cross_l1_portals.yaml"
    yaml_path.write_text(yaml.dump(valid, default_flow_style=False, sort_keys=False, allow_unicode=True))
    print(f"  Saved: {yaml_path} ({len(valid)} edges)")

    raw_path = OUTPUT_DIR / "portals_cross_l1_raw.md"
    raw_content = f"# Cross-L1 Portal Edges — Gemini 3.1 Pro\n\n"
    raw_content += f"<details><summary>Thinking ({len(thinking)} chars)</summary>\n\n{thinking}\n\n</details>\n\n"
    raw_content += f"## Response\n\n```yaml\n{answer.strip()}\n```\n"
    raw_path.write_text(raw_content)
    print(f"  Raw: {raw_path}")

    # Summary by L1 pair
    from collections import Counter
    pairs = Counter()
    for e in valid:
        sl = e.get("source_l1", "?")
        tl = e.get("target_l1", "?")
        pairs[f"{sl}→{tl}"] += 1
    print(f"\n  Cross-L1 pairs:")
    for pair, count in pairs.most_common():
        print(f"    {pair}: {count}")


if __name__ == "__main__":
    main()
