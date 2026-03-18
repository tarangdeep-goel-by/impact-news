"""Generate I→I intra-L1 lateral edges using Gemini 3.1 Pro.

For each Impact L1, sends the full tree to Gemini with taxonomy rules
and asks it to identify causal edges within the tree.

Usage:
    python -m audit.generate_laterals I1 I3 I5    # specific L1s
    python -m audit.generate_laterals all          # all 11
    python -m audit.generate_laterals I1 --dry-run # preview tree, don't call Gemini
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


def extract_tree(G, l1_id: str) -> dict:
    """Extract full tree structure for an L1 category."""
    nodes = []
    for n, d in sorted(G.nodes(data=True)):
        if d.get("category") != l1_id:
            continue
        level = d.get("level", "?")
        aliases = d.get("aliases", [])
        is_cat = d.get("is_category", False)

        # Find CONTAINS parent
        parent = None
        for pred in G.predecessors(n):
            if G[pred][n].get("type") == "CONTAINS":
                parent = pred
                break

        # Find CONTAINS children
        children = []
        for succ in G.successors(n):
            if G[n][succ].get("type") == "CONTAINS":
                children.append(succ)

        nodes.append({
            "id": n,
            "level": level,
            "aliases": aliases[:3],  # limit for token efficiency
            "is_category": is_cat,
            "parent": parent,
            "children": children,
        })

    return {
        "l1_id": l1_id,
        "l1_name": next((n["aliases"][0] for n in nodes if n["level"] == 1), l1_id),
        "node_count": len(nodes),
        "nodes": nodes,
    }


def format_tree_for_prompt(tree: dict) -> str:
    """Format tree as a readable hierarchy for the prompt."""
    nodes_by_id = {n["id"]: n for n in tree["nodes"]}
    lines = [f"# {tree['l1_id']}: {tree['l1_name']} ({tree['node_count']} nodes)\n"]

    def render(node_id, indent=0):
        n = nodes_by_id.get(node_id)
        if not n:
            return
        prefix = "  " * indent
        cat_marker = " [CATEGORY]" if n["is_category"] else ""
        alias_str = f" ({', '.join(n['aliases'][:2])})" if n["aliases"] else ""
        lines.append(f"{prefix}L{n['level']}: {n['id']}{alias_str}{cat_marker}")
        for child in n.get("children", []):
            render(child, indent + 1)

    # Find root (L1 node)
    root = next((n["id"] for n in tree["nodes"] if n["level"] == 1), None)
    if root:
        render(root)

    return "\n".join(lines)


def build_prompt(tree: dict, tree_text: str) -> str:
    """Build the Gemini prompt for intra-L1 lateral edge generation."""
    return f"""You are an expert on Indian economics and the causal mechanisms that connect citizen-level entities. You are building a causal knowledge graph where edges represent how changes in one entity propagate to another.

## Task

Generate **intra-L1 lateral edges** (causal edges WITHIN one Impact tree) for the following tree. These edges model how entities within the same life domain causally affect each other.

## Tree: {tree['l1_id']} — {tree['l1_name']}

```
{tree_text}
```

## Rules (STRICT — follow exactly)

### Targeting (Rule 20)
- **NEVER target L2 nodes** (marked [CATEGORY]). L2 nodes are organizational folders.
- **Target L3 by default.** CONTAINS propagation pushes scores to L4 children automatically.
- **Target L4 only when** the effect hits only ONE specific child under an L3, not all siblings.
- **Homogeneity Test:** Before targeting an L3, ask: "Does this source affect ALL L4 children under this L3 with the same mechanism and polarity?" YES → target L3. NO → target specific L4s.

### Edge Type (Rule 12b — pick the FIRST that fits)
1. **PRODUCES** — A literally creates/generates B
2. **SUPPLIES** — A provides physical goods/data/labor to B
3. **FUNDS** — A directly pays for or financially backs B
4. **DISRUPTS** — A physically blocks, breaks, or halts B
5. **DEPENDS_ON** — B structurally cannot function without A
6. **AFFECTS** — *Fallback only.* A changes price/frequency/quality of B

### Weight (causal pass-through strength, NOT importance)
- **0.9–1.0**: Almost 1:1 pass-through (wheat_flour → bread price)
- **0.6–0.8**: Strong but buffered (home_loan_emi → discretionary spending)
- **0.3–0.5**: Noticeable but diluted (electricity_tariff → restaurant meal cost)
- Avoid weights below 0.3 — PPR will drop them anyway.

### Polarity
- **+1**: When source increases, target increases (same direction)
- **-1**: When source increases, target decreases (opposite direction)
- Think about the entity's **implied axis** (price, volume, quality, availability)

### Delay
- **IMMEDIATE**: Hours/days (fuel price → pump price)
- **SHORT_TERM**: Weeks/1-2 months (supply shock → retail price)
- **MEDIUM_TERM**: 1-6 months (policy change → market adjustment)
- **LONG_TERM**: 6+ months (infrastructure investment → service quality)

### Description (Rule 15)
Must explain the **causal mechanism**, not restate the edge.
- Good: "Higher wheat flour prices directly raise production costs for packaged biscuits"
- Bad: "wheat_flour affects biscuits_and_snacks"

### DAG (Rule 14)
No cycles. If A→B exists, B→A is forbidden. Choose the dominant causal direction.

### Quality over quantity
Only generate edges where a clear, defensible causal mechanism exists in the Indian context. Do NOT generate edges just to connect every node. 5 high-quality edges are better than 20 questionable ones.

## Output Format

Return ONLY a YAML array of edges. No commentary, no markdown fences, just raw YAML:

```yaml
- from: source_node_id
  to: target_node_id
  type: AFFECTS
  weight: 0.7
  polarity: 1
  delay: SHORT_TERM
  description: "Explanation of causal mechanism"
```

Generate the edges now."""


def call_gemini(client, prompt: str, l1_id: str) -> tuple[str, str]:
    """Send prompt to Gemini 3.1 Pro with thinking."""
    from google.genai import types

    chat = client.chats.create(
        model="gemini-3.1-pro-preview",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level="high",
                include_thoughts=True,
            ),
            temperature=0.3,
        ),
    )

    print(f"\n{'='*60}")
    print(f"Generating laterals for {l1_id} ({len(prompt)} chars)...")
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
        print(f"  FAILED after {max_retries} retries")
        return "", ""

    answer = ""
    thinking = ""
    for part in response.candidates[0].content.parts:
        if part.thought:
            thinking += part.text + "\n"
        else:
            answer += part.text + "\n"

    usage = response.usage_metadata
    print(f"  Thinking: {usage.thoughts_token_count} tokens")
    print(f"  Output: {usage.candidates_token_count} tokens")
    print(f"  Total: {usage.total_token_count} tokens")

    return answer.strip(), thinking.strip()


def parse_yaml_response(response: str) -> list[dict]:
    """Parse YAML edges from Gemini response, handling markdown fences."""
    # Strip markdown fences
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        edges = yaml.safe_load(text)
        if isinstance(edges, list):
            return edges
        return []
    except yaml.YAMLError as e:
        print(f"  YAML parse error: {e}")
        return []


def validate_edges(edges: list[dict], tree: dict, G) -> list[dict]:
    """Validate edges against the tree and rules. Return valid edges."""
    valid_nodes = {n["id"] for n in tree["nodes"]}
    cat_nodes = {n["id"] for n in tree["nodes"] if n.get("is_category")}
    l2_nodes = {n["id"] for n in tree["nodes"] if n.get("level") == 2}
    valid_types = {"AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES",
                   "DEPENDS_ON", "FUNDS", "COMPETES_WITH", "EMPLOYS", "MANAGES"}

    valid = []
    for i, edge in enumerate(edges):
        src = edge.get("from", "")
        dst = edge.get("to", "")
        etype = edge.get("type", "")
        issues = []

        if src not in valid_nodes:
            issues.append(f"source '{src}' not in {tree['l1_id']}")
        if dst not in valid_nodes:
            issues.append(f"target '{dst}' not in {tree['l1_id']}")
        if dst in l2_nodes:
            issues.append(f"target '{dst}' is L2 (Rule 20: never target L2)")
        if etype not in valid_types:
            issues.append(f"invalid type '{etype}'")
        if not edge.get("description"):
            issues.append("missing description")
        if edge.get("polarity") not in (1, -1):
            issues.append(f"invalid polarity: {edge.get('polarity')}")
        if src == dst:
            issues.append("self-loop")

        if issues:
            print(f"  REJECTED edge #{i+1} ({src}→{dst}): {'; '.join(issues)}")
        else:
            valid.append(edge)

    return valid


def main():
    parser = argparse.ArgumentParser(description="Generate I→I intra-L1 lateral edges")
    parser.add_argument("l1s", nargs="+", help="L1 IDs (I1, I2, ..., I11) or 'all'")
    parser.add_argument("--dry-run", action="store_true", help="Show tree only, don't call Gemini")
    args = parser.parse_args()

    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults

    merger = TaxonomyMerger()
    G = merger.merge(apply_patches=False)
    apply_defaults(G)

    all_l1s = [f"I{i}" for i in range(1, 12)]
    targets = all_l1s if "all" in args.l1s else args.l1s

    for l1_id in targets:
        if l1_id not in all_l1s:
            print(f"Skipping unknown L1: {l1_id}")
            continue

        tree = extract_tree(G, l1_id)
        tree_text = format_tree_for_prompt(tree)

        if args.dry_run:
            print(tree_text)
            print(f"\n  ({tree['node_count']} nodes — would send to Gemini)\n")
            continue

        client = get_gemini_client()
        prompt = build_prompt(tree, tree_text)
        answer, thinking = call_gemini(client, prompt, l1_id)

        if not answer:
            print(f"  No response for {l1_id}")
            continue

        # Parse and validate
        edges = parse_yaml_response(answer)
        print(f"  Parsed {len(edges)} edges from response")

        valid_edges = validate_edges(edges, tree, G)
        print(f"  Validated: {len(valid_edges)}/{len(edges)} edges passed")

        # Save raw response + thinking
        OUTPUT_DIR.mkdir(exist_ok=True)
        raw_path = OUTPUT_DIR / f"laterals_{l1_id.lower()}_raw.md"
        raw_content = f"# {l1_id} Lateral Edges — Gemini 3.1 Pro\n\n"
        raw_content += f"<details><summary>Thinking ({len(thinking)} chars)</summary>\n\n{thinking}\n\n</details>\n\n"
        raw_content += f"## Response\n\n```yaml\n{answer}\n```\n"
        raw_path.write_text(raw_content)

        # Save validated YAML
        LATERAL_DIR.mkdir(exist_ok=True)
        yaml_path = LATERAL_DIR / f"{l1_id.lower()}_laterals.yaml"
        yaml_content = yaml.dump(valid_edges, default_flow_style=False, sort_keys=False, allow_unicode=True)
        yaml_path.write_text(yaml_content)
        print(f"  Saved: {yaml_path} ({len(valid_edges)} edges)")
        print(f"  Raw:   {raw_path}")

        # Brief pause between L1s to avoid rate limits
        time.sleep(2)


if __name__ == "__main__":
    main()
