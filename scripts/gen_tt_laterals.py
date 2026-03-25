"""Generate T→T lateral edges for one T-world L1 via Gemini 3.1 Pro Preview.

Usage: python3 scripts/gen_tt_laterals.py T1
       python3 scripts/gen_tt_laterals.py T3 --output /tmp/tt_T3_edges.yaml
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


def load_tree(l1_id: str) -> dict:
    path = TAXONOMY_DIR / f"{l1_id}.yaml"
    return yaml.safe_load(path.read_text())


def load_constitution() -> str:
    return (TAXONOMY_DIR / "TAXONOMY.md").read_text()


def format_tree_for_prompt(l1_id: str, data: dict) -> str:
    """Format an L1 tree as a readable hierarchy for the prompt."""
    nodes = data.get("nodes", [])
    lines = [f"### {l1_id}: {TRIGGER_L1S.get(l1_id, l1_id)}"]
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
            lines.append(f"{indent}- `{n['id']}` ({aliases}){cat_marker}")
    return "\n".join(lines)


def get_all_t_world_nodes() -> str:
    """All T-world L3/L4 node IDs grouped by L1."""
    lines = []
    for l1_id in sorted(TRIGGER_L1S):
        data = load_tree(l1_id)
        nodes = [n for n in data.get("nodes", []) if n.get("level") in (3, 4)]
        lines.append(f"\n**{l1_id} ({TRIGGER_L1S[l1_id]}):**")
        for n in nodes:
            lines.append(f"  - `{n['id']}` (L{n.get('level')})")
    return "\n".join(lines)


def get_existing_lateral_edges() -> list[tuple[str, str]]:
    path = TAXONOMY_DIR / "lateral_edges.yaml"
    data = yaml.safe_load(path.read_text())
    edges = data.get("edges", []) or []
    return [(e["from"], e["to"]) for e in edges]


def build_prompt(l1_id: str) -> str:
    target_tree = load_tree(l1_id)
    target_formatted = format_tree_for_prompt(l1_id, target_tree)

    all_trees = []
    for tid in sorted(TRIGGER_L1S):
        data = load_tree(tid)
        all_trees.append(format_tree_for_prompt(tid, data))
    all_trees_str = "\n\n".join(all_trees)

    all_nodes_str = get_all_t_world_nodes()
    constitution = load_constitution()

    existing = get_existing_lateral_edges()
    existing_str = f"({len(existing)} I→I edges already exist — do not generate I→I or I→T edges)"

    return f"""You are generating T→T lateral edges for {l1_id} ({TRIGGER_L1S[l1_id]}).

## What Impact News Is
A causal news personalization engine for Indian citizens. It traces how macro events cascade through a knowledge graph to personal impacts.
- **T-world (Triggers):** Macro systems — nature, government, markets, infrastructure, social forces (T1-T5)
- **I-world (Impacts):** Citizen-facing effects — food, housing, transport, employment, finance, health, education, safety, environment, digital, leisure (I1-I11)

## Graph Constitution (MUST follow ALL rules)
{constitution}

## What You Are Doing: Phase 2b — T→T Lateral Edges for {l1_id}
Generate ONLY T-world to T-world causal edges:
- **Intra-{l1_id}:** Edges between nodes WITHIN {l1_id}
- **Incoming portals:** Edges FROM other T-world L1s INTO {l1_id} nodes
- **Outgoing portals:** Edges FROM {l1_id} nodes TO other T-world L1s

**YOU MUST NOT GENERATE:**
- T→I edges (bridges) — those come in Phase 3. NO edges where the target is I-world (I1-I11).
- I→T feedback edges — forbidden. NO edges where source is I-world.
- Edges involving L1 or L2 category nodes — ALL sources and targets must be L3 or L4.

## Existing Edges
{existing_str}

## {l1_id} Tree Structure (your primary domain)
{target_formatted}

## All T-World Trees (for portal edge context)
{all_trees_str}

## All T-World L3/L4 Nodes (valid sources and targets)
{all_nodes_str}

## Edge Type Priority (Rule 12b — use FIRST that fits)
1. PRODUCES — A literally creates/generates B
2. SUPPLIES — A provides physical goods/resources to B
3. FUNDS — A directly pays for / financially sustains B
4. DISRUPTS — A physically blocks/halts/degrades B
5. DEPENDS_ON — B structurally cannot function without A
6. REGULATES — A sets rules/constraints for B (T-world specific, legitimate here)
7. MANAGES — A operationally controls B (T-world specific, legitimate here)
8. EMPLOYS — A hires labor from B
9. COMPETES_WITH — A takes market share from B (unidirectional)
10. AFFECTS — FALLBACK ONLY. Should be MINORITY type (<25%).

## T-World Specific Guidance
- T2 (Institutions): REGULATES and MANAGES are the dominant edge types. RBI regulates banks, SEBI regulates equity markets, ministries manage their domains.
- T3 (Markets): Watch for circular flows (FII→equity→forex→FII). Financial markets have feedback loops — break them by modeling the PRIMARY causal direction only.
- T4 (Infrastructure): Physical dependencies (power grid → telecom towers) are strong DEPENDS_ON/SUPPLIES edges.
- T5 (Social): Demographic forces (urbanization → migration) are long-term PRODUCES relationships.
- Cross-L1: T2 institutions regulate T3 markets and manage T4 infrastructure. T1 natural systems disrupt T4 infrastructure.

## Weight Guidelines
- 0.85-0.95: Direct physical/structural dependency (power grid → telecom)
- 0.7-0.85: Strong institutional/economic control (RBI → repo rate)
- 0.5-0.7: Moderate systemic effect (crude prices → trade deficit)
- 0.3-0.5: Weak/indirect effect (demographics → consumer confidence)

## Output Format
Return ONLY valid YAML starting with `edges:`. No markdown fencing, no commentary.

edges:
- from: <source_node_id>
  to: <target_node_id>
  type: <EDGE_TYPE>
  weight: <0.0-1.0>
  polarity: <1|-1>
  delay: <IMMEDIATE|SHORT_TERM|MEDIUM_TERM|LONG_TERM>
  description: <One sentence proving the direct causal mechanism>

## Target
~30-50 edges for {l1_id}. Include both intra-tree AND portal edges.
Prioritize edges that enable ground truth event propagation: crude oil surges, RBI rate hikes, monsoon failures, IT layoffs, AQI crises.
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


def validate_edges(edges: list[dict], t_node_ids: set[str]) -> tuple[list[dict], list[str]]:
    """Validate and return (valid_edges, issues)."""
    valid = []
    issues = []
    valid_types = {"AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES",
                   "DEPENDS_ON", "FUNDS", "COMPETES_WITH", "EMPLOYS", "MANAGES"}

    for e in edges:
        src, tgt = e.get("from", ""), e.get("to", "")
        etype = e.get("type", "")

        if src not in t_node_ids:
            issues.append(f"SKIP: source `{src}` not T-world L3/L4")
            continue
        if tgt not in t_node_ids:
            issues.append(f"SKIP: target `{tgt}` not T-world L3/L4")
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

    output = args.output or f"/tmp/tt_{l1_id}_edges.yaml"

    prompt = build_prompt(l1_id)
    print(f"Prompt built for {l1_id} ({len(prompt)} chars)")

    # Call Gemini
    client = genai.Client(api_key=settings.gemini_api_key)

    for attempt in range(5):
        try:
            print(f"Attempt {attempt+1}, model: gemini-3.1-pro-preview...")
            response = client.models.generate_content(
                model="gemini-3.1-pro-preview",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.1,
                    thinking_config=genai.types.ThinkingConfig(thinking_budget=16000),
                ),
            )
            raw = response.text
            print(f"Got response ({len(raw)} chars)")
            Path(f"/tmp/tt_{l1_id}_raw.txt").write_text(raw)

            edges = parse_yaml_response(raw)
            print(f"Parsed {len(edges)} edges")

            # Load all T-world L3/L4 node IDs
            t_nodes = set()
            for tid in TRIGGER_L1S:
                data = load_tree(tid)
                for n in data.get("nodes", []):
                    if n.get("level") in (3, 4):
                        t_nodes.add(n["id"])

            valid, issues = validate_edges(edges, t_nodes)

            Path(output).write_text(
                yaml.dump({"edges": valid}, default_flow_style=False, sort_keys=False, allow_unicode=True)
            )

            types = Counter(e["type"] for e in valid)
            print(f"\nValid: {len(valid)} edges, Skipped: {len(edges)-len(valid)}")
            print(f"Type distribution: {dict(types.most_common())}")
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
