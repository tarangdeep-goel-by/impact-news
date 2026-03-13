"""Gemini-powered graph builder for v4 taxonomy.

Usage:
    python3 scripts/graph_builder.py generate-tree <L1_ID>
    python3 scripts/graph_builder.py review-tree <L1_ID>
    python3 scripts/graph_builder.py generate-edges <L1_ID>
    python3 scripts/graph_builder.py review-edges <L1_ID> [--world impact|trigger|cross]
    python3 scripts/graph_builder.py generate-portals --world <impact|trigger>
    python3 scripts/graph_builder.py generate-bridges
    python3 scripts/graph_builder.py generate-feedback
    python3 scripts/graph_builder.py full-review
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from google import genai

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import settings

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAXONOMY_DIR = PROJECT_ROOT / "taxonomy"
TAXONOMY_MD = TAXONOMY_DIR / "TAXONOMY.md"

# Gemini model fallback chain (thinking-capable only)
MODEL_CHAIN = [
    "gemini-3.1-pro-preview",
    "gemini-3-pro-preview",
    "gemini-2.5-pro",
]

# Retry config
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 10

# L1 definitions extracted from constitution
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

ALL_L1S = {**TRIGGER_L1S, **IMPACT_L1S}

CANONICAL_EDGE_TYPES = [
    "AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES",
    "DEPENDS_ON", "CONTAINS", "IS_A", "FUNDS", "COMPETES_WITH",
    "EMPLOYS", "MANAGES",
]

NODE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


# ---------------------------------------------------------------------------
# Gemini Client (enhanced)
# ---------------------------------------------------------------------------


class GraphGemini:
    """Enhanced Gemini client for graph building tasks."""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def call(self, prompt: str, *, temperature: float = 0.1, thinking_budget: int = 16000) -> str:
        """Call Gemini with thinking enabled. Retries on transient failures."""
        import time

        for attempt in range(1, MAX_RETRIES + 1):
            for model in MODEL_CHAIN:
                try:
                    log.info("Attempt %d — model: %s", attempt, model)
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=genai.types.GenerateContentConfig(
                            temperature=temperature,
                            thinking_config=genai.types.ThinkingConfig(
                                thinking_budget=thinking_budget,
                            ),
                        ),
                    )
                    return response.text
                except Exception as e:
                    log.warning("Model %s failed: %s", model, e)
                    continue

            if attempt < MAX_RETRIES:
                log.info("All models failed on attempt %d, retrying in %ds...", attempt, RETRY_DELAY_SECONDS)
                time.sleep(RETRY_DELAY_SECONDS)

        raise RuntimeError(f"All Gemini models failed after {MAX_RETRIES} attempts")


# ---------------------------------------------------------------------------
# Constitution loader
# ---------------------------------------------------------------------------


def load_constitution() -> str:
    """Read the full TAXONOMY.md as context for prompts."""
    if not TAXONOMY_MD.exists():
        raise FileNotFoundError(f"Constitution not found: {TAXONOMY_MD}")
    return TAXONOMY_MD.read_text()


def extract_l1_section(constitution: str, l1_id: str) -> str:
    """Extract the relevant L1 definition, examples, and boundary rules from the constitution."""
    name = ALL_L1S.get(l1_id, "Unknown")
    world = "Trigger" if l1_id.startswith("T") else "Impact"

    # Find the L1 row in the table
    lines = constitution.split("\n")
    l1_info = []
    for line in lines:
        if f"| {l1_id} |" in line:
            l1_info.append(line.strip())

    # Find boundary rules for this world
    boundary_section = ""
    if world == "Trigger":
        start = constitution.find("#### Trigger Boundary Rules")
        end = constitution.find("### 11 Impact L1s")
        if start != -1 and end != -1:
            boundary_section = constitution[start:end].strip()
    else:
        start = constitution.find("#### Impact Boundary Rules")
        end = constitution.find("---", constitution.find("#### Impact Boundary Rules"))
        if start != -1 and end != -1:
            boundary_section = constitution[start:end].strip()

    return f"""L1 ID: {l1_id}
L1 Name: {name}
World: {world}
Table row: {chr(10).join(l1_info)}

{boundary_section}"""


# ---------------------------------------------------------------------------
# YAML I/O
# ---------------------------------------------------------------------------


def load_l1_yaml(l1_id: str) -> dict[str, Any] | None:
    """Load existing YAML for an L1 if it exists."""
    path = TAXONOMY_DIR / f"{l1_id}.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text())


def save_l1_yaml(l1_id: str, data: dict[str, Any]) -> Path:
    """Save YAML data for an L1."""
    path = TAXONOMY_DIR / f"{l1_id}.yaml"
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )
    log.info("Saved %s", path)
    return path


def load_all_world_yamls(world: str) -> dict[str, dict[str, Any]]:
    """Load all YAMLs for a world (impact or trigger)."""
    result = {}
    l1s = IMPACT_L1S if world == "impact" else TRIGGER_L1S
    for l1_id in l1s:
        data = load_l1_yaml(l1_id)
        if data:
            result[l1_id] = data
    return result


def parse_yaml_from_response(text: str) -> dict[str, Any]:
    """Extract YAML from Gemini response (may be wrapped in ```yaml blocks)."""
    cleaned = text.strip()
    # Remove markdown fences
    cleaned = re.sub(r"^```ya?ml\s*", "", cleaned)
    cleaned = re.sub(r"```\s*$", "", cleaned)

    # Try to find YAML content
    if cleaned.startswith("nodes:") or cleaned.startswith("edges:"):
        return yaml.safe_load(cleaned)

    # Try to find yaml block in response
    yaml_match = re.search(r"```ya?ml\s*\n(.*?)```", text, re.DOTALL)
    if yaml_match:
        return yaml.safe_load(yaml_match.group(1))

    # Last resort: try parsing the whole thing
    return yaml.safe_load(cleaned)


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------


def validate_nodes(nodes: list[dict], l1_id: str) -> list[str]:
    """Run basic programmatic checks on generated nodes."""
    issues = []
    seen_ids: set[str] = set()

    for node in nodes:
        nid = node.get("id", "")

        # Check node ID format
        if not NODE_ID_RE.match(nid):
            issues.append(f"Bad node_id format: '{nid}'")

        # Check duplicates
        if nid in seen_ids:
            issues.append(f"Duplicate node_id: '{nid}'")
        seen_ids.add(nid)

        # Check category matches L1
        cat = node.get("category", "")
        if cat and cat != l1_id:
            issues.append(f"Node '{nid}' has category '{cat}', expected '{l1_id}'")

        # Check aliases
        aliases = node.get("aliases", [])
        if len(aliases) < 3:
            issues.append(f"Node '{nid}' has only {len(aliases)} aliases (need 3+)")

        # Check level (1+ is valid, no upper cap)
        level = node.get("level")
        if not isinstance(level, int) or level < 1:
            issues.append(f"Node '{nid}' has invalid level: {level}")

    return issues


def validate_edges(edges: list[dict], known_nodes: set[str]) -> list[str]:
    """Run basic programmatic checks on generated edges."""
    issues = []

    for edge in edges:
        src = edge.get("from", "")
        dst = edge.get("to", "")
        etype = edge.get("type", "")

        if src not in known_nodes:
            issues.append(f"Edge source '{src}' not in known nodes")
        if dst not in known_nodes:
            issues.append(f"Edge target '{dst}' not in known nodes")
        if etype not in CANONICAL_EDGE_TYPES:
            issues.append(f"Edge {src}->{dst} has non-canonical type '{etype}'")
        if not edge.get("description"):
            issues.append(f"Edge {src}->{dst} missing description")

        weight = edge.get("weight", 0)
        if not (0 < weight <= 1):
            issues.append(f"Edge {src}->{dst} weight {weight} out of range (0,1]")

        polarity = edge.get("polarity", 0)
        if polarity not in (1, -1):
            issues.append(f"Edge {src}->{dst} polarity must be +1 or -1, got {polarity}")

        delay = edge.get("delay", "")
        if delay not in ("IMMEDIATE", "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"):
            issues.append(f"Edge {src}->{dst} invalid delay '{delay}'")

    return issues


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------


def build_tree_prompt(l1_id: str, constitution: str) -> str:
    """Build prompt for generating a vertical tree (Phase 1a/2a)."""
    l1_section = extract_l1_section(constitution, l1_id)
    name = ALL_L1S[l1_id]
    world = "Trigger" if l1_id.startswith("T") else "Impact"

    return f"""You are building the v4 impact knowledge graph for an Indian news personalization engine.

## Constitution (MUST follow all 17 rules):
{constitution}

## Your Task
Generate the complete vertical tree for L1 category: {l1_id} ({name})

{l1_section}

## Requirements

### Tree depth — go as deep as the domain demands
- Start with L2 broad subcategories under {l1_id}
- Under each L2, create L3 sub-subcategories OR leaf entities — whichever fits
- If an L3 naturally contains distinct, individually newsworthy sub-entities, go to L4 (or even L5)
- Stop deepening when you hit entities that pass the Leaf Node Test (Rule 5)
- Example of correct depth: `I1 → fresh_produce → vegetables → retail_tomato` (L4 leaf)
- Example of too shallow: `I1 → fresh_produce → retail_tomato` (skips natural grouping)
- Non-leaf nodes (any node with children) get `is_category: true`

### Content coverage — be thorough for India
- Think about what actually appears in Indian newspaper headlines, TV debates, kitchen table conversations
- Include the obvious big entities AND the long-tail entities that matter regionally
- Include Hindi/colloquial/regional terms as aliases (pyaaz, tamatar, atta, doodh, etc.)
- Don't forget entities that are small nationally but massive locally (e.g., fish in Bengal/Kerala, coconut oil in Kerala)
- For high-weight L1s, err on the side of more entities rather than fewer

### Constitution rules (non-negotiable)
- Rule 1: Entities only (things that exist), NOT events or changes
- Rule 5: Every LEAF must be Matchable (LLM can extract from headline), Mappable (user onboarding connects), Edgeable (has causal edges)
- Rule 6: Use CONTAINS for parent→child, IS_A only for within-level specialization
- Rule 9: Siblings should be as mutually exclusive as practical
- Rule 10: Similar granularity depth across siblings at the same level
- Rule 11: India-first scoping — {"Does this entity have a causal path to an Indian citizen?" if world == "Trigger" else "Would this plausibly appear in an Indian news headline in 2026?"}
- Rule 16: All nodes status=active
- Node IDs must be snake_case matching ^[a-z][a-z0-9_]*$
- Each node needs 3+ aliases including Hindi/colloquial terms where applicable
- Include the L1 root node itself

## Output Format (YAML only, no other text):
```yaml
nodes:
  - id: {l1_id.lower()}
    aliases: ["{name}", ...]
    category: {l1_id}
    level: 1
    status: active
    is_category: true
  - id: example_l2
    aliases: ["Example L2", "example alias", "hindi term"]
    category: {l1_id}
    level: 2
    status: active
    is_category: true
  - id: example_l3_category
    aliases: ["Example L3 Group", "alias", "hindi term"]
    category: {l1_id}
    level: 3
    status: active
    is_category: true
  - id: example_l4_leaf
    aliases: ["Example Leaf", "alias 2", "hindi term"]
    category: {l1_id}
    level: 4
    status: active
edges:
  - from: {l1_id.lower()}
    to: example_l2
    type: CONTAINS
    weight: 0.9
    polarity: 1
    delay: IMMEDIATE
    description: "{name} contains this subcategory"
  - from: example_l2
    to: example_l3_category
    type: CONTAINS
    weight: 0.9
    polarity: 1
    delay: IMMEDIATE
    description: "L2 contains this sub-group"
  - from: example_l3_category
    to: example_l4_leaf
    type: CONTAINS
    weight: 0.9
    polarity: 1
    delay: IMMEDIATE
    description: "L3 group contains this leaf entity"
```"""


def build_review_prompt(l1_id: str, tree_yaml: str, constitution: str) -> str:
    """Build prompt for reviewing a generated tree."""
    name = ALL_L1S[l1_id]
    world = "Trigger" if l1_id.startswith("T") else "Impact"

    return f"""You are a strict reviewer for the v4 impact knowledge graph constitution.

## Constitution:
{constitution}

## Tree to Review: {l1_id} ({name})
```yaml
{tree_yaml}
```

## Review Checklist
For EACH node, verify:
1. **Entity Principle (Rule 1):** Is it an entity (thing that exists), not an event?
2. **{world} Classification (Rule 2):** Does it belong in the {world} world?
3. **Leaf Node Test (Rule 5):** Matchable? Mappable? Edgeable?
4. **India-first (Rule 11):** {"Would a causal path to Indian citizens exist?" if world == "Trigger" else "Would this appear in Indian news?"}
5. **Granularity Parity (Rule 10):** Similar depth across siblings?
6. **Sibling Distinctness (Rule 9):** Can news affect one without the other?
7. **Node ID (Convention):** Valid snake_case? Descriptive?
8. **Aliases:** At least 3? Include Hindi/colloquial terms?

## Output Format
For each node, one line:
- PASS: <node_id> — <brief note>
- FAIL: <node_id> — <rule violated> — <suggested fix>

Then a summary:
- Total nodes: X
- Passed: Y
- Failed: Z
- Overall score: X/10
- Suggested structural changes (if any)"""


def build_edges_prompt(l1_id: str, all_trees_yaml: str, constitution: str) -> str:
    """Build prompt for generating lateral edges (Phase 1b/2b)."""
    name = ALL_L1S[l1_id]
    world = "Impact" if l1_id.startswith("I") else "Trigger"

    return f"""You are building lateral edges for the v4 impact knowledge graph.

## Constitution:
{constitution}

## All {world} Trees (for portal edge context):
```yaml
{all_trees_yaml}
```

## Your Task
Generate lateral edges for L1: {l1_id} ({name})

Two types:
1. **Intra-tree edges:** Between nodes within {l1_id}
2. **Portal edges:** From {l1_id} nodes to nodes in other {world} L1s

## Rules
- Rule 7: Intra-tree and Portal edge types
- Rule 12: Every edge needs type, weight, polarity, delay, description
- Rule 14: Must form DAG — no cycles
- Rule 15: Description must explain the causal mechanism (not just "A affects B")
- Mark nodes that have portal edges with portal: true

## Target
- 3-5 lateral edges per leaf node (average)
- Focus on the strongest, most newsworthy causal links
- Use appropriate edge types from: AFFECTS, PRODUCES, REGULATES, DISRUPTS, SUPPLIES, DEPENDS_ON, FUNDS, COMPETES_WITH, EMPLOYS, MANAGES

## Output Format (YAML only):
```yaml
edges:
  - from: source_node_id
    to: target_node_id
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: SHORT_TERM
    description: "Detailed causal mechanism explanation"
portal_nodes:
  - node_id_1
  - node_id_2
```"""


def build_bridge_prompt(trigger_yaml: str, impact_yaml: str, constitution: str) -> str:
    """Build prompt for generating bridge edges (Phase 3)."""
    return f"""You are building bridge and feedback edges for the v4 impact knowledge graph.

## Constitution:
{constitution}

## Trigger Subgraph:
```yaml
{trigger_yaml}
```

## Impact Subgraph:
```yaml
{impact_yaml}
```

## Your Task
Generate two types of cross-world edges:

### 1. Bridge Edges (T->I)
Connect Trigger nodes to Impact nodes where there's a direct causal mechanism.
- Mark Impact nodes receiving bridges with port: true
- Every Impact port node should be reachable from at least one Trigger node

### 2. Feedback Edges (I->T)
Connect Impact nodes back to Trigger nodes where citizen outcomes influence system entities.
- Feedback edges MUST have delay >= MEDIUM_TERM (citizen impact lags system response)
- Examples: retail inflation -> RBI policy, unemployment -> organized labor, health crisis -> health ministry

## Rules
- Rule 7: Bridge = T->I, Feedback = I->T
- Rule 8: Impact nodes receiving bridges get port: true
- Rule 12: Full edge properties (type, weight, polarity, delay, description)
- Rule 15: Causal provenance in every description

## Output Format (YAML only):
```yaml
bridge_edges:
  - from: trigger_node_id
    to: impact_node_id
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: SHORT_TERM
    description: "How the trigger entity causally affects the impact entity"
feedback_edges:
  - from: impact_node_id
    to: trigger_node_id
    type: AFFECTS
    weight: 0.5
    polarity: 1
    delay: MEDIUM_TERM
    description: "How citizen-level outcome feeds back to system entity"
port_nodes:
  - impact_node_id_1
  - impact_node_id_2
```"""


def build_full_review_prompt(full_graph_yaml: str, constitution: str) -> str:
    """Build prompt for end-to-end validation (Phase 4)."""
    return f"""You are performing a final review of the complete v4 impact knowledge graph.

## Constitution:
{constitution}

## Complete Graph:
```yaml
{full_graph_yaml}
```

## Task: Run these 15 scenario traces

For each scenario, trace the causal chain through the graph and verify it reaches the expected Impact nodes.

1. **Brent crude price spike** -> diesel -> freight -> food prices -> household savings
2. **RBI repo rate hike** -> home loan EMI -> personal savings -> consumer spending
3. **Southwest monsoon deficit** -> crop yield -> food prices -> farmer income
4. **IT layoffs wave** -> tech jobs -> personal income -> loan defaults
5. **Delhi AQI crisis** -> respiratory health -> hospital visits -> healthcare costs
6. **GST rate change** -> consumer prices -> household budget -> discretionary spending
7. **US Fed rate cut** -> FII flows -> Nifty -> mutual fund portfolios
8. **Jio tariff hike** -> mobile data costs -> digital service access -> gig worker earnings
9. **Metro fare revision** -> commute costs -> work location choices -> rental demand
10. **School fee increase** -> education costs -> household savings -> loan demand
11. **Gold price rally** -> retail gold investment -> wedding costs -> personal finance
12. **Startup funding winter** -> job market -> gig economy -> platform pricing
13. **Power grid failure** -> electricity supply -> industrial output -> employment
14. **Monsoon flooding** -> urban flooding -> property damage -> insurance claims
15. **UPI outage** -> digital payments -> small business -> cash demand

## For Each Scenario:
1. Identify the trigger event and starting node
2. Trace the causal chain through edges (list each hop with edge type)
3. Note if any link is missing or broken
4. Rate chain completeness: COMPLETE / PARTIAL / BROKEN

## Also Verify North Star Metrics:
- Total nodes (target: 300-350)
- Impact leaves (target: 150-180)
- Trigger leaves (target: 70-100)
- Lateral edges per leaf (target: 3-5 avg)
- Orphans (target: 0)
- Connected components (target: 1)
- Edge descriptions (target: 100%)
- Cycles (target: 0)

## Output:
Scenario traces followed by metric assessment and overall graph health score (1-10)."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_generate_tree(args: argparse.Namespace) -> int:
    """Generate a vertical tree for one L1."""
    l1_id = args.l1_id.upper()
    if l1_id not in ALL_L1S:
        print(f"ERROR: Unknown L1 ID '{l1_id}'. Valid: {', '.join(sorted(ALL_L1S))}")
        return 1

    # Check if file already exists
    existing = load_l1_yaml(l1_id)
    if existing and not args.force:
        print(f"WARNING: {l1_id}.yaml already exists ({len(existing.get('nodes', []))} nodes). Use --force to overwrite.")
        return 1

    print(f"Generating tree for {l1_id} ({ALL_L1S[l1_id]})...")

    constitution = load_constitution()
    prompt = build_tree_prompt(l1_id, constitution)

    gemini = GraphGemini()
    response = gemini.call(prompt, temperature=0.1)

    # Parse YAML
    try:
        data = parse_yaml_from_response(response)
    except Exception as e:
        print(f"ERROR: Failed to parse YAML from Gemini response: {e}")
        print("Raw response (first 2000 chars):")
        print(response[:2000])
        return 1

    if not data or not data.get("nodes"):
        print("ERROR: No nodes in generated output")
        print("Raw response (first 2000 chars):")
        print(response[:2000])
        return 1

    # Basic validation
    issues = validate_nodes(data.get("nodes", []), l1_id)
    if data.get("edges"):
        node_ids = {n["id"] for n in data["nodes"]}
        issues.extend(validate_edges(data["edges"], node_ids))

    if issues:
        print(f"\nValidation issues ({len(issues)}):")
        for issue in issues:
            print(f"  - {issue}")
        print()

    # Save
    path = save_l1_yaml(l1_id, data)

    # Summary
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    l2_count = sum(1 for n in nodes if n.get("level") == 2)
    l3_count = sum(1 for n in nodes if n.get("level") == 3)
    print(f"\nSaved to {path}")
    print(f"  Nodes: {len(nodes)} (1 L1 + {l2_count} L2s + {l3_count} L3s)")
    print(f"  Edges: {len(edges)}")
    if issues:
        print(f"  Validation issues: {len(issues)} (review recommended)")

    return 0


def cmd_review_tree(args: argparse.Namespace) -> int:
    """Review a generated tree against the constitution."""
    l1_id = args.l1_id.upper()
    if l1_id not in ALL_L1S:
        print(f"ERROR: Unknown L1 ID '{l1_id}'.")
        return 1

    data = load_l1_yaml(l1_id)
    if not data:
        print(f"ERROR: {l1_id}.yaml not found. Generate it first.")
        return 1

    print(f"Reviewing tree for {l1_id} ({ALL_L1S[l1_id]})...")

    constitution = load_constitution()
    tree_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    prompt = build_review_prompt(l1_id, tree_yaml, constitution)

    gemini = GraphGemini()
    response = gemini.call(prompt, temperature=0.3)

    print("\n" + "=" * 60)
    print(f"REVIEW: {l1_id} ({ALL_L1S[l1_id]})")
    print("=" * 60)
    print(response)

    return 0


def cmd_generate_edges(args: argparse.Namespace) -> int:
    """Generate lateral edges for one L1."""
    l1_id = args.l1_id.upper()
    if l1_id not in ALL_L1S:
        print(f"ERROR: Unknown L1 ID '{l1_id}'.")
        return 1

    data = load_l1_yaml(l1_id)
    if not data:
        print(f"ERROR: {l1_id}.yaml not found. Generate tree first.")
        return 1

    world = "impact" if l1_id.startswith("I") else "trigger"
    all_trees = load_all_world_yamls(world)

    if not all_trees:
        print(f"ERROR: No {world} trees found. Generate trees first.")
        return 1

    print(f"Generating lateral edges for {l1_id} ({ALL_L1S[l1_id]})...")

    constitution = load_constitution()
    all_trees_yaml = yaml.dump(all_trees, default_flow_style=False, sort_keys=False, allow_unicode=True)
    prompt = build_edges_prompt(l1_id, all_trees_yaml, constitution)

    gemini = GraphGemini()
    response = gemini.call(prompt, temperature=0.1)

    try:
        edge_data = parse_yaml_from_response(response)
    except Exception as e:
        print(f"ERROR: Failed to parse YAML: {e}")
        print("Raw response (first 2000 chars):")
        print(response[:2000])
        return 1

    new_edges = edge_data.get("edges", [])
    portal_nodes = edge_data.get("portal_nodes", [])

    # Collect all known node IDs across world
    known_nodes: set[str] = set()
    for tree_data in all_trees.values():
        for node in tree_data.get("nodes", []):
            known_nodes.add(node["id"])

    # Validate edges
    issues = validate_edges(new_edges, known_nodes)
    if issues:
        print(f"\nValidation issues ({len(issues)}):")
        for issue in issues[:20]:
            print(f"  - {issue}")

    # Merge edges into existing YAML
    existing_edges = data.get("edges", [])
    data["edges"] = existing_edges + new_edges

    # Mark portal nodes
    for node in data.get("nodes", []):
        if node["id"] in portal_nodes:
            node["portal"] = True

    save_l1_yaml(l1_id, data)

    print(f"\nAdded {len(new_edges)} lateral edges to {l1_id}.yaml")
    print(f"Portal nodes marked: {len(portal_nodes)}")
    if issues:
        print(f"Validation issues: {len(issues)} (review recommended)")

    return 0


def cmd_generate_portals(args: argparse.Namespace) -> int:
    """Generate portal edges across L1s within a world."""
    world = args.world
    if world not in ("impact", "trigger"):
        print("ERROR: --world must be 'impact' or 'trigger'")
        return 1

    all_trees = load_all_world_yamls(world)
    if len(all_trees) < 2:
        print(f"ERROR: Need at least 2 {world} trees for portal edges.")
        return 1

    print(f"Generating portal edges for {world} world ({len(all_trees)} L1s)...")

    # Use the edges prompt with a combined context
    constitution = load_constitution()
    all_yaml = yaml.dump(all_trees, default_flow_style=False, sort_keys=False, allow_unicode=True)

    prompt = f"""You are building portal edges (cross-L1, same world) for the v4 impact knowledge graph.

## Constitution:
{constitution}

## All {world.title()} Trees:
```yaml
{all_yaml}
```

## Your Task
Generate ONLY portal edges — edges that connect nodes in DIFFERENT L1 categories within the {world} world.

Rules:
- Rule 7: Portal edges connect nodes across different L1s in the same world
- Rule 12: Every edge needs type, weight, polarity, delay, description
- Rule 14: Must form DAG — no cycles
- Rule 15: Description must explain the causal mechanism
- Mark both source and target nodes with portal: true

Focus on the strongest, most newsworthy cross-category causal links.

## Output Format (YAML only):
```yaml
edges:
  - from: source_l1_node_id
    to: target_l1_node_id
    type: AFFECTS
    weight: 0.7
    polarity: 1
    delay: SHORT_TERM
    description: "Causal mechanism explanation"
portal_nodes:
  - node_id_1
  - node_id_2
```"""

    gemini = GraphGemini()
    response = gemini.call(prompt, temperature=0.1)

    try:
        edge_data = parse_yaml_from_response(response)
    except Exception as e:
        print(f"ERROR: Failed to parse YAML: {e}")
        print(response[:2000])
        return 1

    new_edges = edge_data.get("edges", [])
    portal_nodes_list = set(edge_data.get("portal_nodes", []))

    # Determine which L1 each edge belongs to (by source node)
    node_to_l1: dict[str, str] = {}
    for l1_id, tree_data in all_trees.items():
        for node in tree_data.get("nodes", []):
            node_to_l1[node["id"]] = l1_id

    # Add edges to source L1 files
    edges_per_l1: dict[str, list[dict]] = {}
    for edge in new_edges:
        src_l1 = node_to_l1.get(edge.get("from", ""), "")
        if src_l1:
            edges_per_l1.setdefault(src_l1, []).append(edge)

    for l1_id, edges in edges_per_l1.items():
        data = load_l1_yaml(l1_id)
        if not data:
            continue
        existing = data.get("edges", [])
        data["edges"] = existing + edges
        # Mark portal nodes
        for node in data.get("nodes", []):
            if node["id"] in portal_nodes_list:
                node["portal"] = True
        save_l1_yaml(l1_id, data)
        print(f"  {l1_id}: added {len(edges)} portal edges")

    print(f"\nTotal portal edges: {len(new_edges)}")
    return 0


def cmd_generate_bridges(args: argparse.Namespace) -> int:
    """Generate T->I bridge edges (Phase 3)."""
    trigger_trees = load_all_world_yamls("trigger")
    impact_trees = load_all_world_yamls("impact")

    if not trigger_trees:
        print("ERROR: No trigger trees found.")
        return 1
    if not impact_trees:
        print("ERROR: No impact trees found.")
        return 1

    print(f"Generating bridge edges ({len(trigger_trees)} Trigger L1s -> {len(impact_trees)} Impact L1s)...")

    constitution = load_constitution()
    trigger_yaml = yaml.dump(trigger_trees, default_flow_style=False, sort_keys=False, allow_unicode=True)
    impact_yaml = yaml.dump(impact_trees, default_flow_style=False, sort_keys=False, allow_unicode=True)

    prompt = build_bridge_prompt(trigger_yaml, impact_yaml, constitution)

    gemini = GraphGemini()
    response = gemini.call(prompt, temperature=0.1, thinking_budget=24000)

    try:
        data = parse_yaml_from_response(response)
    except Exception as e:
        print(f"ERROR: Failed to parse YAML: {e}")
        print(response[:2000])
        return 1

    bridge_edges = data.get("bridge_edges", [])
    feedback_edges = data.get("feedback_edges", [])
    port_nodes_list = set(data.get("port_nodes", []))

    # Save bridge edges to a dedicated patch file
    patch_data = {
        "edges": bridge_edges + feedback_edges,
        "new_nodes": [],
    }
    patch_path = TAXONOMY_DIR / "bridge_edges.yaml"
    patch_path.write_text(
        yaml.dump(patch_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    # Mark port nodes in impact YAMLs
    for l1_id, tree_data in impact_trees.items():
        changed = False
        for node in tree_data.get("nodes", []):
            if node["id"] in port_nodes_list and not node.get("port"):
                node["port"] = True
                changed = True
        if changed:
            save_l1_yaml(l1_id, tree_data)

    print(f"\nBridge edges: {len(bridge_edges)}")
    print(f"Feedback edges: {len(feedback_edges)}")
    print(f"Port nodes marked: {len(port_nodes_list)}")
    print(f"Saved to {patch_path}")

    return 0


def cmd_generate_feedback(args: argparse.Namespace) -> int:
    """Generate I->T feedback edges (Phase 3). Included in generate-bridges."""
    print("Feedback edges are generated together with bridges.")
    print("Run: python3 scripts/graph_builder.py generate-bridges")
    return 0


def cmd_review_edges(args: argparse.Namespace) -> int:
    """Review generated edges."""
    l1_id = args.l1_id
    if l1_id:
        l1_id = l1_id.upper()
        if l1_id not in ALL_L1S:
            print(f"ERROR: Unknown L1 ID '{l1_id}'.")
            return 1
        data = load_l1_yaml(l1_id)
        if not data:
            print(f"ERROR: {l1_id}.yaml not found.")
            return 1
        edges = data.get("edges", [])
        lateral = [e for e in edges if e.get("type") not in ("CONTAINS", "IS_A")]
        print(f"Lateral edges in {l1_id}: {len(lateral)}")
        for e in lateral:
            print(f"  {e['from']} --[{e.get('type')}]--> {e['to']}")
            if e.get("description"):
                print(f"    {e['description'][:80]}")
    else:
        # Review all edges across a world
        world = args.world or "impact"
        all_trees = load_all_world_yamls(world)
        total_lateral = 0
        for l1, tree_data in sorted(all_trees.items()):
            edges = tree_data.get("edges", [])
            lateral = [e for e in edges if e.get("type") not in ("CONTAINS", "IS_A")]
            total_lateral += len(lateral)
            print(f"  {l1}: {len(lateral)} lateral edges")
        print(f"\nTotal {world} lateral edges: {total_lateral}")

    return 0


def cmd_full_review(args: argparse.Namespace) -> int:
    """End-to-end validation with Gemini (Phase 4)."""
    # Load all trees
    all_data: dict[str, Any] = {}
    for l1_id in ALL_L1S:
        data = load_l1_yaml(l1_id)
        if data:
            all_data[l1_id] = data

    if len(all_data) < 10:
        print(f"WARNING: Only {len(all_data)}/16 L1 files found. Full review works best with all L1s.")

    print("Running full Gemini review...")

    constitution = load_constitution()
    full_yaml = yaml.dump(all_data, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Truncate if too long (Gemini context limit)
    if len(full_yaml) > 200000:
        print(f"WARNING: Graph YAML is {len(full_yaml)} chars, truncating to 200k for review")
        full_yaml = full_yaml[:200000] + "\n... (truncated)"

    prompt = build_full_review_prompt(full_yaml, constitution)

    gemini = GraphGemini()
    response = gemini.call(prompt, temperature=0.3, thinking_budget=24000)

    print("\n" + "=" * 60)
    print("FULL GRAPH REVIEW")
    print("=" * 60)
    print(response)

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="graph_builder",
        description="Gemini-powered graph builder for v4 taxonomy",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # generate-tree
    p = sub.add_parser("generate-tree", help="Generate vertical tree for one L1")
    p.add_argument("l1_id", help="L1 ID (e.g., I1, T2)")
    p.add_argument("--force", action="store_true", help="Overwrite existing YAML")

    # review-tree
    p = sub.add_parser("review-tree", help="Review generated tree against constitution")
    p.add_argument("l1_id", help="L1 ID")

    # generate-edges
    p = sub.add_parser("generate-edges", help="Generate lateral edges for one L1")
    p.add_argument("l1_id", help="L1 ID")

    # review-edges
    p = sub.add_parser("review-edges", help="Review generated edges")
    p.add_argument("l1_id", nargs="?", help="L1 ID (optional, reviews one L1)")
    p.add_argument("--world", choices=["impact", "trigger", "cross"], help="World to review")

    # generate-portals
    p = sub.add_parser("generate-portals", help="Generate cross-L1 portal edges")
    p.add_argument("--world", required=True, choices=["impact", "trigger"])

    # generate-bridges
    sub.add_parser("generate-bridges", help="Generate T->I bridge + I->T feedback edges")

    # generate-feedback
    sub.add_parser("generate-feedback", help="(Included in generate-bridges)")

    # full-review
    sub.add_parser("full-review", help="End-to-end validation with Gemini")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    dispatch = {
        "generate-tree": cmd_generate_tree,
        "review-tree": cmd_review_tree,
        "generate-edges": cmd_generate_edges,
        "review-edges": cmd_review_edges,
        "generate-portals": cmd_generate_portals,
        "generate-bridges": cmd_generate_bridges,
        "generate-feedback": cmd_generate_feedback,
        "full-review": cmd_full_review,
    }

    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
