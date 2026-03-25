"""Generate T→I bridge edges for one T-world L1 via Gemini 3.1 Pro Preview.

Usage: python3 scripts/gen_ti_bridges.py T1
       python3 scripts/gen_ti_bridges.py T3 --output /tmp/bridge_T3_edges.yaml
"""

import argparse
import sys
import time
import re
from pathlib import Path
from collections import Counter

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from google import genai

TAXONOMY_DIR = PROJECT_ROOT / "taxonomy"

TRIGGER_L1S = {
    "T1": "Natural & Planetary Systems",
    "T2": "Institutional & Sovereign Entities",
    "T3": "Macroeconomic & Global Markets",
    "T4": "Technological & Physical Infrastructure",
    "T5": "Social, Demographic & Cultural Forces",
}

IMPACT_L1S = {
    "I1": "Food & Nutrition",
    "I2": "Housing & Utilities",
    "I3": "Transport & Mobility",
    "I4": "Livelihood & Employment",
    "I5": "Personal Finance & Wealth",
    "I6": "Health & Physiology",
    "I7": "Education & Human Capital",
    "I8": "Safety & Security",
    "I9": "Local Environmental Quality",
    "I10": "Digital Life & Connectivity",
    "I11": "Leisure, Culture & Community",
}


def load_tree(l1_id: str) -> dict:
    path = TAXONOMY_DIR / f"{l1_id}.yaml"
    return yaml.safe_load(path.read_text())


def load_constitution() -> str:
    return (TAXONOMY_DIR / "TAXONOMY.md").read_text()


def format_tree_for_prompt(l1_id: str, data: dict, label_map: dict) -> str:
    nodes = data.get("nodes", [])
    lines = [f"### {l1_id}: {label_map.get(l1_id, l1_id)}"]
    by_level = {}
    for n in nodes:
        lvl = n.get("level", 0)
        by_level.setdefault(lvl, []).append(n)
    for lvl in sorted(by_level):
        if lvl <= 1:
            continue
        indent = "  " * (lvl - 2)
        for n in by_level[lvl]:
            cat_marker = " [CATEGORY]" if n.get("is_category") else ""
            aliases = ", ".join(n.get("aliases", [])[:3])
            lines.append(f"{indent}- `{n['id']}` (L{n.get('level')}) ({aliases}){cat_marker}")
    return "\n".join(lines)


def get_i_world_nodes_flat() -> str:
    """All I-world L3/L4 node IDs grouped by L1."""
    lines = []
    for l1_id in sorted(IMPACT_L1S):
        data = load_tree(l1_id)
        nodes = [n for n in data.get("nodes", []) if n.get("level") in (3, 4)]
        lines.append(f"\n**{l1_id} ({IMPACT_L1S[l1_id]}):**")
        for n in nodes:
            lines.append(f"  - `{n['id']}` (L{n.get('level')})")
    return "\n".join(lines)


def get_existing_lateral_summary() -> str:
    """Summarize existing I→I lateral edges for context."""
    path = TAXONOMY_DIR / "lateral_edges.yaml"
    data = yaml.safe_load(path.read_text())
    edges = data.get("edges", []) or []

    # Group by target L1 (approximate — just show unique targets)
    targets = set(e["to"] for e in edges)
    return f"{len(edges)} I→I lateral edges exist, covering {len(targets)} unique I-world target nodes. The I→I laterals handle propagation WITHIN impact world — bridges only need to connect to the FIRST point of impact."


def build_prompt(l1_id: str) -> str:
    t_data = load_tree(l1_id)
    t_formatted = format_tree_for_prompt(l1_id, t_data, TRIGGER_L1S)

    # All I-world trees
    i_trees = []
    for iid in sorted(IMPACT_L1S):
        data = load_tree(iid)
        i_trees.append(format_tree_for_prompt(iid, data, IMPACT_L1S))
    i_trees_str = "\n\n".join(i_trees)

    i_nodes_str = get_i_world_nodes_flat()
    constitution = load_constitution()
    lateral_summary = get_existing_lateral_summary()

    return f"""You are generating T→I bridge edges from {l1_id} ({TRIGGER_L1S[l1_id]}) to I-world impact nodes.

## What Impact News Is
A causal news personalization engine for Indian citizens. It traces how macro events cascade through a knowledge graph to personal impacts.
- **T-world (Triggers):** Macro systems — nature, government, markets, infrastructure, social forces (T1-T5)
- **I-world (Impacts):** Citizen-facing effects — food, housing, transport, employment, finance, health, education, safety, environment, digital, leisure (I1-I11)

## Graph Constitution (MUST follow ALL rules)
{constitution}

## What You Are Doing: Phase 3 — T→I Bridge Edges from {l1_id}
Generate Bridge Edges (T→I) ONLY — from {l1_id} trigger nodes to I-world impact nodes.

**Critical principle: Bridges terminate at the FIRST POINT OF IMPACT.**
A bridge is valid ONLY if the trigger DIRECTLY affects the I-world node without requiring signal to pass through another I-world node first.
- VALID: `brent_crude (T3) → vehicle_fuel (I3)` — crude price directly sets fuel price
- INVALID: `brent_crude (T3) → retail_tomato (I1)` — needs vehicle_fuel → road_freight_movement → retail_tomato (all I→I laterals)

The I→I laterals (501 edges, already built) handle propagation from there.

**YOU MUST NOT GENERATE:**
- T→T edges (laterals) — already generated in Phase 2b
- I→I edges — already generated in Phase 1b
- I→T feedback edges — forbidden (no reverse flow)
- Edges with L1 or L2 sources/targets — ALL sources must be T-world L3/L4, ALL targets must be I-world L3/L4

## Existing I→I Laterals (context)
{lateral_summary}

## {l1_id} Trigger Tree (source nodes)
{t_formatted}

## All I-World Trees (target nodes)
{i_trees_str}

## All I-World L3/L4 Nodes
{i_nodes_str}

## Edge Type Priority (Rule 12b — use FIRST that fits)
1. PRODUCES — trigger literally creates the impact entity
2. SUPPLIES — trigger provides physical goods/resources
3. FUNDS — trigger directly pays for
4. DISRUPTS — trigger physically blocks/halts
5. DEPENDS_ON — impact structurally cannot function without trigger
6. AFFECTS — FALLBACK ONLY. Should be MINORITY type (<25%).
Note: REGULATES and MANAGES must NOT cross T→I boundary (Rule 18). Store as metadata, not edges.

## Bridge Density Guidance
- Each T-world L3/L4 leaf should have 1-5 bridges into I-world (sparse, not exhaustive)
- Fan-out is fine — crude legitimately hits vehicle_fuel, cooking_fuel, AND lpg_cylinder independently
- Err on the side of FEWER, MORE DIRECT bridges. If you're not sure a bridge is direct, leave it out — the T→T laterals + I→I laterals will find the path.

## Weight Guidelines
- 0.85-0.95: Direct physical dependency (crude → fuel, monsoon → reservoir)
- 0.7-0.85: Strong economic/institutional (RBI → lending rates)
- 0.5-0.7: Moderate cross-world effect
- 0.3-0.5: Weak/conditional

## Output Format
Return ONLY valid YAML starting with `edges:`. No markdown fencing, no commentary.

edges:
- from: <trigger_l3_or_l4_node_id>
  to: <impact_l3_or_l4_node_id>
  type: <EDGE_TYPE>
  weight: <0.0-1.0>
  polarity: <1|-1>
  delay: <IMMEDIATE|SHORT_TERM|MEDIUM_TERM|LONG_TERM>
  description: <One sentence proving the direct causal mechanism — must pass the Bypassing Test>

## Target
~30-60 bridge edges from {l1_id} to I-world. Cover all relevant I-world domains that {l1_id} directly affects.
Prioritize edges that enable ground truth event propagation: crude oil surges, RBI rate hikes, monsoon failures, IT layoffs, AQI crises, Delhi pollution.
"""


def parse_yaml_response(text: str) -> list[dict]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```ya?ml\s*", "", cleaned)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    idx = cleaned.find("edges:")
    if idx != -1:
        cleaned = cleaned[idx:]
    data = yaml.safe_load(cleaned)
    return data.get("edges", []) if isinstance(data, dict) else []


def validate_edges(edges: list[dict], t_node_ids: set[str], i_node_ids: set[str]) -> tuple[list[dict], list[str]]:
    valid = []
    issues = []
    valid_types = {"AFFECTS", "PRODUCES", "DISRUPTS", "SUPPLIES",
                   "DEPENDS_ON", "FUNDS", "COMPETES_WITH", "EMPLOYS"}

    for e in edges:
        src, tgt = e.get("from", ""), e.get("to", "")
        etype = e.get("type", "")

        if src not in t_node_ids:
            issues.append(f"SKIP: source `{src}` not T-world L3/L4")
            continue
        if tgt not in i_node_ids:
            issues.append(f"SKIP: target `{tgt}` not I-world L3/L4")
            continue
        if etype in ("REGULATES", "MANAGES"):
            issues.append(f"SKIP: `{src}→{tgt}` {etype} cannot cross T→I (Rule 18)")
            continue
        if etype not in valid_types:
            issues.append(f"SKIP: `{src}→{tgt}` bad type `{etype}`")
            continue

        w = e.get("weight", 0)
        if not (0 < w <= 1):
            e["weight"] = max(0.1, min(1.0, w))
        if e.get("polarity") not in (1, -1):
            e["polarity"] = 1
        if e.get("delay") not in ("IMMEDIATE", "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"):
            e["delay"] = "SHORT_TERM"

        valid.append(e)

    return valid, issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("l1_id", help="T-world L1 ID (T1-T5)")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    l1_id = args.l1_id.upper()
    if l1_id not in TRIGGER_L1S:
        print(f"ERROR: {l1_id} not in {list(TRIGGER_L1S)}")
        sys.exit(1)

    output = args.output or f"/tmp/bridge_{l1_id}_edges.yaml"

    prompt = build_prompt(l1_id)
    print(f"Prompt built for {l1_id} ({len(prompt)} chars)")

    client = genai.Client(api_key=settings.gemini_api_key)

    for attempt in range(5):
        try:
            print(f"Attempt {attempt+1}, model: gemini-3.1-pro-preview...")
            response = client.models.generate_content(
                model="gemini-3.1-pro-preview",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.1,
                    thinking_config=genai.types.ThinkingConfig(thinking_budget=32000),
                    max_output_tokens=16000,
                ),
            )
            raw = response.text
            print(f"Got response ({len(raw)} chars)")
            Path(f"/tmp/bridge_{l1_id}_raw.txt").write_text(raw)

            edges = parse_yaml_response(raw)
            print(f"Parsed {len(edges)} edges")

            # Load node IDs
            t_nodes = set()
            for tid in TRIGGER_L1S:
                data = load_tree(tid)
                for n in data.get("nodes", []):
                    if n.get("level") in (3, 4):
                        t_nodes.add(n["id"])

            i_nodes = set()
            for iid in IMPACT_L1S:
                data = load_tree(iid)
                for n in data.get("nodes", []):
                    if n.get("level") in (3, 4):
                        i_nodes.add(n["id"])

            valid, issues = validate_edges(edges, t_nodes, i_nodes)

            Path(output).write_text(
                yaml.dump({"edges": valid}, default_flow_style=False, sort_keys=False, allow_unicode=True)
            )

            types = Counter(e["type"] for e in valid)
            print(f"\nValid: {len(valid)} edges, Skipped: {len(edges)-len(valid)}")
            print(f"Type distribution: {dict(types.most_common())}")

            # Show I-world domain coverage
            i_domains = Counter()
            for e in valid:
                # Approximate L1 from node data
                for iid in IMPACT_L1S:
                    data = load_tree(iid)
                    node_ids = {n["id"] for n in data.get("nodes", [])}
                    if e["to"] in node_ids:
                        i_domains[iid] += 1
                        break
            print(f"I-world domain coverage: {dict(i_domains.most_common())}")

            if issues:
                print(f"\nIssues ({len(issues)}):")
                for iss in issues:
                    print(f"  {iss}")
            print(f"\nSaved to {output}")
            return

        except Exception as e:
            print(f"  Failed: {e}")
            time.sleep(15)

    print("ERROR: All attempts failed")
    sys.exit(1)


if __name__ == "__main__":
    main()
