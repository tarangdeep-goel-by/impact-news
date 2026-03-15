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

    def call(self, prompt: str, *, temperature: float = 0.1, thinking_budget: int = 16000, max_output_tokens: int | None = None) -> str:
        """Call Gemini with thinking enabled. Retries on transient failures."""
        import time

        for attempt in range(1, MAX_RETRIES + 1):
            for model in MODEL_CHAIN:
                try:
                    log.info("Attempt %d — model: %s", attempt, model)
                    config_kwargs: dict = {
                        "temperature": temperature,
                        "thinking_config": genai.types.ThinkingConfig(
                            thinking_budget=thinking_budget,
                        ),
                    }
                    if max_output_tokens:
                        config_kwargs["max_output_tokens"] = max_output_tokens
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=genai.types.GenerateContentConfig(**config_kwargs),
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

## Task: Run these 30 scenario traces

For each scenario, trace the FULL causal chain through the graph — every hop must use an actual edge
that exists in the graph. Verify it reaches the expected Impact nodes at the citizen level.

### Energy & Commodity Cascades
1. **Brent crude price spike** → diesel → freight costs → food prices → household savings
2. **Iran-US conflict escalates** → oil supply disruption → crude prices → LPG cylinder cost → cooking gas expense → household budget
3. **Gold price rally (geopolitical safe haven)** → retail gold investment → gold loan collateral value → wedding costs → personal finance
4. **Global natural gas price surge** → CNG fuel prices → auto-rickshaw fares → commute costs → gig worker margins

### Monetary & Fiscal Policy
5. **RBI repo rate hike** → home loan EMI → personal savings → consumer spending → kirana store income
6. **US Fed rate cut** → FII inflows → Nifty index → mutual fund portfolios → retirement corpus
7. **GST rate revision on packaged food** → FMCG prices → household grocery bill → discretionary spending
8. **LPG subsidy removal (₹60 hike)** → cooking fuel cost → household food budget → calorie intake → malnutrition

### Technology & Digital
9. **AI boom → global RAM shortage** → smartphone prices → device replacement cycles → digital access → UPI adoption → kirana store payments
10. **Jio tariff hike** → mobile data costs → OTT streaming → gig worker app access → delivery earnings
11. **UPI infrastructure outage** → digital payment failure → cash demand → small business disruption → street vendor income
12. **Aadhaar authentication server downtime** → EPF withdrawal blocked → pension access → elderly financial stress

### Climate & Natural Systems
13. **El Niño 2026 → weak southwest monsoon** → kharif crop failure → rice/wheat prices → farmer income → rural distress → MGNREGA demand
14. **Delhi winter inversion (AQI 500+)** → respiratory illness → hospital visits → healthcare costs → productivity loss
15. **Himalayan glacier retreat** → river basin water levels → irrigation availability → crop yield → food prices
16. **Tropical cyclone (Bay of Bengal)** → coastal flooding → fish catch disruption → marine fish prices → fisher livelihood
17. **Post-monsoon stubble burning winds** → air quality → school closures → education disruption → child learning outcomes

### Employment & Livelihood
18. **IT layoffs wave (global recession)** → tech sector jobs → personal income → loan defaults → credit score → future borrowing
19. **Startup funding winter** → startup jobs → gig economy shift → platform worker density → per-delivery earnings
20. **MGNREGA budget cut** → rural employment guarantee → daily wage income → rural consumption → kirana store income
21. **Zomato/Swiggy commission hike** → restaurant margins → menu prices → food delivery demand → delivery worker trips

### Trade & Geopolitical
22. **US Section 301 tariffs on India** → export manufacturing → factory employment → industrial town economy → local rent prices
23. **India-US trade deal (tariff reduction to 18%)** → cheaper imports → domestic manufacturing competition → MSME revenue → informal employment
24. **China-Taiwan semiconductor tensions** → chip supply → electronics prices → laptop costs → edtech access → student outcomes
25. **Russia-Ukraine grain corridor collapse** → global wheat prices → Indian wheat export ban → domestic wheat supply → atta prices

### Social & Demographic
26. **Mass rural-to-urban migration wave** → urban housing demand → rental prices → slum growth → sanitation access → waterborne disease
27. **Major religious festival (Kumbh Mela scale)** → mass pilgrimage → local economy boost → transport demand → hotel prices → tourism revenue
28. **Farmer protest / highway blockade** → freight disruption → perishable food wastage → vegetable prices → urban household costs
29. **Heatwave (48°C in north India)** → outdoor labor productivity → construction sector → daily wage loss → dehydration hospitalizations
30. **School fee hyperinflation** → education loan demand → household debt → credit card EMIs → discretionary spending cuts → OTT cancellations

## For Each Scenario:
1. Identify the trigger event and map it to a starting node in the graph
2. Trace the causal chain through actual edges (list each hop: node → node, edge type, weight)
3. Note EVERY missing link or broken connection — be specific about which edge is absent
4. Rate chain completeness: COMPLETE (all hops exist) / PARTIAL (>50% hops exist) / BROKEN (<50% or critical link missing)
5. For PARTIAL/BROKEN: suggest specific edges that should be added

## Also Verify Graph Health:
- Total nodes vs target (700-800 with variable depth)
- Orphan nodes (leaves with zero lateral edges)
- Connected components (target: 1 after bridge edges)
- Edge description coverage (target: 100%)
- Feedback edge delays (all must be >= MEDIUM_TERM)
- Port node coverage (every Impact L1 should have port nodes)

## Output Format:
For each scenario: scenario name, chain trace, rating, missing edges.
Then: metric summary table, list of all suggested new edges, overall health score (1-10)."""


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
    """Generate T->I bridge edges (Phase 3).

    Runs per-T-L1 for better coverage — each Trigger L1 gets its own
    call against all Impact L1s, with higher thinking/output budgets.
    Use --append to add to existing bridge_edges.yaml instead of overwriting.
    """
    trigger_trees = load_all_world_yamls("trigger")
    impact_trees = load_all_world_yamls("impact")

    if not trigger_trees:
        print("ERROR: No trigger trees found.")
        return 1
    if not impact_trees:
        print("ERROR: No impact trees found.")
        return 1

    constitution = load_constitution()
    impact_yaml = yaml.dump(impact_trees, default_flow_style=False, sort_keys=False, allow_unicode=True)

    gemini = GraphGemini()
    all_bridge_edges = []
    all_feedback_edges = []
    all_port_nodes = set()

    # Load existing bridge edges if --append
    patch_path = TAXONOMY_DIR / "bridge_edges.yaml"
    if getattr(args, "append", False) and patch_path.exists():
        existing = yaml.safe_load(patch_path.read_text()) or {}
        all_bridge_edges.extend(existing.get("edges", []))
        existing_pairs = {(e["from"], e["to"]) for e in all_bridge_edges}
        print(f"Loaded {len(all_bridge_edges)} existing bridge/feedback edges")
    else:
        existing_pairs = set()

    trigger_yaml = yaml.dump(trigger_trees, default_flow_style=False, sort_keys=False, allow_unicode=True)

    per_impact = getattr(args, "per_impact", False)

    if per_impact:
        # Per-I-L1: each Impact L1 gets its own call against all Trigger L1s
        for i_id, i_data in sorted(impact_trees.items()):
            i_yaml = yaml.dump({i_id: i_data}, default_flow_style=False, sort_keys=False, allow_unicode=True)
            print(f"\nGenerating bridges: all Trigger L1s -> {i_id}...")

            prompt = build_bridge_prompt(trigger_yaml, i_yaml, constitution)
            response = gemini.call(prompt, temperature=0.1, thinking_budget=32000, max_output_tokens=16000)

            try:
                data = parse_yaml_from_response(response)
            except Exception as e:
                print(f"  WARNING: Failed to parse YAML for {i_id}: {e}")
                continue

            bridges = data.get("bridge_edges", [])
            feedback = data.get("feedback_edges", [])
            ports = set(data.get("port_nodes", []))

            new_bridges = [e for e in bridges if (e["from"], e["to"]) not in existing_pairs]
            new_feedback = [e for e in feedback if (e["from"], e["to"]) not in existing_pairs]
            for e in new_bridges + new_feedback:
                existing_pairs.add((e["from"], e["to"]))

            all_bridge_edges.extend(new_bridges)
            all_feedback_edges.extend(new_feedback)
            all_port_nodes.update(ports)
            print(f"  {i_id}: +{len(new_bridges)} bridges, +{len(new_feedback)} feedback, {len(ports)} ports")
    else:
        # Per-T-L1: each Trigger L1 gets its own call against all Impact L1s
        for t_id, t_data in sorted(trigger_trees.items()):
            t_yaml = yaml.dump({t_id: t_data}, default_flow_style=False, sort_keys=False, allow_unicode=True)
            print(f"\nGenerating bridges: {t_id} -> all Impact L1s...")

            prompt = build_bridge_prompt(t_yaml, impact_yaml, constitution)
            response = gemini.call(prompt, temperature=0.1, thinking_budget=32000, max_output_tokens=16000)

            try:
                data = parse_yaml_from_response(response)
            except Exception as e:
                print(f"  WARNING: Failed to parse YAML for {t_id}: {e}")
                continue

            bridges = data.get("bridge_edges", [])
            feedback = data.get("feedback_edges", [])
            ports = set(data.get("port_nodes", []))

            new_bridges = [e for e in bridges if (e["from"], e["to"]) not in existing_pairs]
            new_feedback = [e for e in feedback if (e["from"], e["to"]) not in existing_pairs]
            for e in new_bridges + new_feedback:
                existing_pairs.add((e["from"], e["to"]))

            all_bridge_edges.extend(new_bridges)
            all_feedback_edges.extend(new_feedback)
            all_port_nodes.update(ports)
            print(f"  {t_id}: +{len(new_bridges)} bridges, +{len(new_feedback)} feedback, {len(ports)} ports")

    # Save all bridge edges
    patch_data = {
        "edges": all_bridge_edges + all_feedback_edges,
        "new_nodes": [],
    }
    patch_path.write_text(
        yaml.dump(patch_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    # Mark port nodes in impact YAMLs
    for l1_id, tree_data in impact_trees.items():
        changed = False
        for node in tree_data.get("nodes", []):
            if node["id"] in all_port_nodes and not node.get("port"):
                node["port"] = True
                changed = True
        if changed:
            save_l1_yaml(l1_id, tree_data)

    print(f"\nTotal bridge edges: {len(all_bridge_edges)}")
    print(f"Total feedback edges: {len(all_feedback_edges)}")
    print(f"Port nodes marked: {len(all_port_nodes)}")
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

    # Include bridge edges
    bridge_path = TAXONOMY_DIR / "bridge_edges.yaml"
    if bridge_path.exists():
        bridge_data = yaml.safe_load(bridge_path.read_text()) or {}
        all_data["bridge_edges"] = bridge_data

    full_yaml = yaml.dump(all_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"Graph YAML size: {len(full_yaml):,} chars")

    prompt = build_full_review_prompt(full_yaml, constitution)
    print(f"Total prompt size: {len(prompt):,} chars")

    gemini = GraphGemini()
    response = gemini.call(prompt, temperature=0.3, thinking_budget=65000, max_output_tokens=32000)

    print("\n" + "=" * 60)
    print("FULL GRAPH REVIEW")
    print("=" * 60)
    print(response)

    return 0


def cmd_test(args: argparse.Namespace) -> int:
    """Run scenario tests against the merged graph."""
    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults
    from graph.scenarios import load_scenarios, validate_scenario_refs, run_all, print_results, export_failures

    # Load graph
    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()
    apply_defaults(G)
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Load scenarios
    scenarios_path = getattr(args, 'scenarios', None)
    if scenarios_path:
        scenarios_path = Path(scenarios_path)
    scenarios = load_scenarios(scenarios_path)
    print(f"Loaded {len(scenarios)} scenarios")

    # Filter by domain or id
    if args.domain:
        scenarios = [s for s in scenarios if s.get("domain") == args.domain]
        print(f"Filtered to {len(scenarios)} scenarios (domain={args.domain})")
    if args.id:
        scenarios = [s for s in scenarios if s.get("id") == args.id]
        print(f"Filtered to {len(scenarios)} scenarios (id={args.id})")

    if not scenarios:
        print("No scenarios to run.")
        return 0

    # Validate refs
    ref_errors = validate_scenario_refs(scenarios, set(G.nodes()))
    if ref_errors:
        print(f"\nWARNING: {len(ref_errors)} node reference issues:")
        for err in ref_errors:
            print(f"  {err}")
        print()

    # Run
    results = run_all(G, scenarios)
    print_results(results)

    # Export failures
    failures = [r for r in results if r["status"] in ("FAIL", "ERROR")]
    if failures:
        export_path = Path(args.export) if args.export else PROJECT_ROOT / "data" / "failed_scenarios.json"
        export_failures(results, export_path)
        print(f"\nFailures exported to {export_path}")

    return 1 if failures else 0


def cmd_generate_scenarios(args: argparse.Namespace) -> int:
    """Generate new scenarios via Gemini for a domain."""
    from graph.merge import TaxonomyMerger
    from graph.scenarios import load_scenarios

    domain = args.domain
    count = args.count or 20

    # Load graph for node list
    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Group nodes by L1 category
    nodes_by_category: dict[str, list[str]] = {}
    for nid, attrs in G.nodes(data=True):
        cat = attrs.get("category", "uncategorized")
        nodes_by_category.setdefault(cat, []).append(nid)

    node_list_text = ""
    for cat in sorted(nodes_by_category):
        nodes = sorted(nodes_by_category[cat])
        name = ALL_L1S.get(cat, cat)
        node_list_text += f"\n### {cat} — {name}\n"
        node_list_text += ", ".join(nodes) + "\n"

    # Load existing scenario IDs to avoid duplicates
    try:
        existing = load_scenarios()
        existing_ids = {s["id"] for s in existing}
    except Exception:
        existing_ids = set()

    # Optional headlines file
    headlines = ""
    if args.headlines:
        headlines_path = Path(args.headlines)
        if headlines_path.exists():
            headlines = f"\n## Recent Headlines (for inspiration):\n{headlines_path.read_text()}\n"

    prompt = f"""You are generating test scenarios for an Indian citizen impact knowledge graph.

## Available Node IDs (grouped by L1 category):
{node_list_text}

## Existing Scenario IDs (do NOT duplicate these):
{', '.join(sorted(existing_ids)) if existing_ids else '(none)'}
{headlines}
## Task
Generate {count} NEW test scenarios for the domain "{domain}".

## Scenario Types:
- Type A (path_exists): Test if a causal path exists from trigger to target node
  Fields: id, description, domain, type: A, trigger_node, target_node, max_hops (2-6), expected (REACHABLE or UNREACHABLE)
- Type B (reachability): Test if trigger reaches multiple target nodes
  Fields: id, description, domain, type: B, trigger_node, target_nodes (list), direction (1 or -1), threshold (float)
- Type C (score_threshold): Test if target is reachable with score >= min_score
  Fields: id, description, domain, type: C, trigger_node, target_node, direction (1 or -1), min_score (float)

## Rules:
1. Use ONLY node IDs from the provided list above
2. Mix types: ~60% A, ~25% B, ~15% C
3. Include ~10% negative tests (expected: UNREACHABLE for Type A)
4. Vary max_hops (2-6)
5. Ground in real Indian news scenarios
6. Cover both intra-world (I→I) and cross-world (T→I) chains
7. ID format: {{domain}}_{{descriptive_name}} in snake_case
8. Domain must be: {domain}

## Output Format (YAML only):
```yaml
scenarios:
  - id: {domain}_example
    description: "Description of the scenario"
    domain: {domain}
    type: A
    trigger_node: node_id_here
    target_node: other_node_id
    max_hops: 4
    expected: REACHABLE
```"""

    print(f"Generating {count} scenarios for domain '{domain}'...")
    gemini = GraphGemini()
    response = gemini.call(prompt, temperature=0.5, thinking_budget=16000)

    try:
        data = parse_yaml_from_response(response)
    except Exception as e:
        print(f"ERROR: Failed to parse YAML: {e}")
        print(response[:2000])
        return 1

    new_scenarios = data.get("scenarios", [])

    # Validate node refs
    known_nodes = set(G.nodes())
    valid = []
    invalid = 0
    for sc in new_scenarios:
        refs_ok = True
        for field in ("trigger_node", "target_node"):
            nid = sc.get(field)
            if nid and nid not in known_nodes:
                print(f"  WARNING: {sc.get('id', '?')}.{field} '{nid}' not in graph — skipping")
                refs_ok = False
        for nid in sc.get("target_nodes", []) or []:
            if nid not in known_nodes:
                print(f"  WARNING: {sc.get('id', '?')}.target_nodes '{nid}' not in graph — skipping")
                refs_ok = False
        if refs_ok:
            valid.append(sc)
        else:
            invalid += 1

    # Write staging file
    staging_path = TAXONOMY_DIR / f"scenarios_staging_{domain}.yaml"
    staging_path.write_text(
        yaml.dump({"scenarios": valid}, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    print(f"\nGenerated {len(valid)} valid scenarios ({invalid} skipped)")
    print(f"Written to {staging_path}")
    print("Review, then merge into taxonomy/scenarios.yaml")

    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    """Diagnose failed scenarios and generate patch recipe."""
    import json
    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults

    input_path = Path(args.input) if args.input else PROJECT_ROOT / "data" / "failed_scenarios.json"
    output_path = Path(args.output) if args.output else TAXONOMY_DIR / "patches" / "patch_recipe.yaml"

    if not input_path.exists():
        print(f"ERROR: No failures file at {input_path}")
        print("Run 'test --export' first to generate failures.")
        return 1

    failures = json.loads(input_path.read_text())
    if not failures:
        print("No failures to diagnose.")
        return 0

    print(f"Diagnosing {len(failures)} failed scenario(s)...")

    # Load graph
    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()
    apply_defaults(G)
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    constitution = load_constitution()
    gemini = GraphGemini()

    # Map Phase: diagnose each failure
    all_new_nodes = []
    all_new_edges = []
    scenarios_fixed = []

    for failure in failures:
        sid = failure.get("id", "?")
        stype = failure.get("type", "?")
        detail = failure.get("detail", "")

        # Extract relevant nodes from failure
        # We need to rebuild from the scenario — failures only have id/type/status/detail
        # Load scenario data to get trigger/target
        from graph.scenarios import load_scenarios
        all_scenarios = load_scenarios()
        scenario = next((s for s in all_scenarios if s.get("id") == sid), None)
        if not scenario:
            print(f"  SKIP {sid}: scenario definition not found")
            continue

        src = scenario.get("trigger_node", "")
        dst = scenario.get("target_node", "")
        if not src:
            print(f"  SKIP {sid}: no trigger_node")
            continue

        # Build neighborhood subgraph (BFS radius 2 from src and dst)
        neighborhood_nodes = set()
        for start in [src, dst] if dst else [src]:
            if not G.has_node(start):
                continue
            # BFS radius 2
            visited = {start}
            frontier = [start]
            for _ in range(2):
                next_frontier = []
                for n in frontier:
                    for neighbor in list(G.successors(n)) + list(G.predecessors(n)):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            next_frontier.append(neighbor)
                frontier = next_frontier
            neighborhood_nodes.update(visited)

        # Also add nodes from same L1 categories
        src_cat = G.nodes[src].get("category", "") if G.has_node(src) else ""
        dst_cat = G.nodes[dst].get("category", "") if dst and G.has_node(dst) else ""
        for nid, attrs in G.nodes(data=True):
            if attrs.get("category") in (src_cat, dst_cat) and src_cat:
                neighborhood_nodes.add(nid)

        # Build neighborhood YAML (capped at 8000 chars)
        neighborhood = {"nodes": [], "edges": []}
        for nid in sorted(neighborhood_nodes):
            if G.has_node(nid):
                attrs = dict(G.nodes[nid])
                neighborhood["nodes"].append({"id": nid, **{k: v for k, v in attrs.items() if k != "source_file"}})
        for u, v, attrs in G.edges(data=True):
            if u in neighborhood_nodes and v in neighborhood_nodes:
                neighborhood["edges"].append({
                    "from": u, "to": v,
                    **{k: v2 for k, v2 in attrs.items() if k != "source_file"}
                })

        neighborhood_yaml = yaml.dump(neighborhood, default_flow_style=False, sort_keys=False, allow_unicode=True)
        if len(neighborhood_yaml) > 8000:
            # Truncate to prioritize nodes closer to src/dst
            neighborhood_yaml = neighborhood_yaml[:8000] + "\n# ... (truncated)"

        prompt = f"""You are diagnosing a failed scenario test in the Indian citizen impact knowledge graph.

## Constitution (graph rules):
{constitution[:3000]}

## Failed Scenario:
- ID: {sid}
- Type: {stype}
- Trigger: {src}
- Target: {dst}
- Detail: {detail}
- Scenario: {yaml.dump(scenario, default_flow_style=False)}

## Neighborhood Subgraph (BFS radius 2 from src/dst):
```yaml
{neighborhood_yaml}
```

## Valid edge types: {', '.join(CANONICAL_EDGE_TYPES)}

## Graph Architecture (CRITICAL — read carefully):

The graph has two worlds:
- **Trigger world** (T1–T5): systemic forces — energy, policy, markets, infra, social
- **Impact world** (I1–I11): citizen-facing outcomes — food, housing, transport, jobs, etc.

Hierarchy levels: L1 (category) → L2 (subcategory) → L3 (leaf) → L4 (specific).
L1/L2 nodes are structural parents. L3/L4 nodes carry most causal edges.
CONTAINS edges connect parents to children: L1→L2→L3→L4.

**The traversal engine follows CONTAINS edges downward.** This means:
- An edge targeting an L2 node automatically propagates to ALL its L3/L4 children.
- You do NOT need to create separate edges for each child.
- Example: one edge `gst_council → food_and_nutrition` (L1) propagates to rice, tomato, biscuits, etc.

## Routing Rules (MANDATORY — violations will be rejected):

### Rule 1: Cross-world edges must target L1 or L2 only
Any edge crossing from T→I or I→T MUST target an L1 or L2 node, NEVER an L3 or L4.
CONTAINS propagation handles the downward reach.

BAD:  `gst_council (T2) → biscuits_and_snacks (I1/L4)` — too specific, won't scale
GOOD: `gst_council (T2) → packaged_and_processed_foods (I1/L2)` — propagates to all packaged food children

BAD:  `nifty_50 (T3) → nps_portfolio (I5/L4)` — direct shortcut
GOOD: `nifty_50 (T3) → investment_returns (I5/L2)` — propagates to NPS, mutual funds, etc.

### Rule 2: Every causal edge must represent ONE direct mechanism
If A affects B only through intermediate C, the graph needs A→C and C→B, NOT A→B.
Ask: "Does A DIRECTLY cause B, or does it go through something?"

BAD:  `outdoor_heat → retail_rice` — heat doesn't directly change rice prices
GOOD: `outdoor_heat → rice_crop_yield` + `rice_crop_yield → retail_rice`

### Rule 3: No speculative or weak causal links
Every edge must represent a well-established, direct causal mechanism.
If the connection requires 2+ sentences to justify, it's probably indirect — decompose it.

BAD:  `voter_turnout → consumer_confidence` — speculative
BAD:  `aadhaar_authentication → senior_citizen_savings_scheme` — operational, not causal

### Rule 4: Prefer existing intermediate nodes
Before creating a new node, check the neighborhood subgraph for existing nodes that could
serve as the intermediate step. The graph already has 700+ nodes.

## Task:
1. Classify the gap:
   - Type 1 (missing node): A necessary intermediate node doesn't exist
   - Type 2 (missing edge): Nodes exist but no causal edge connects them
   - Type 3 (missing path): Multiple hops missing, needs decomposition

2. Propose the MINIMAL fix. Output YAML:

```yaml
gap_type: 1|2|3
diagnosis: "Brief explanation of what's missing"

new_nodes:
  - id: new_node_id
    aliases: [alias1, alias2]
    category: T1|T2|...|I11
    level: 2|3
    parent: parent_node_id

new_edges:
  - from: source_node
    to: target_node
    type: AFFECTS|PRODUCES|etc
    weight: 0.1-1.0
    polarity: 1|-1
    delay: IMMEDIATE|SHORT_TERM|MEDIUM_TERM|LONG_TERM
    description: "One sentence: the direct causal mechanism"
```

Rules:
- Node IDs must be snake_case
- Prefer existing nodes over creating new ones
- Every new node needs a parent (generates CONTAINS edge)
- Edge descriptions must explain the DIRECT causal mechanism in one sentence
- Keep fixes MINIMAL — don't add unnecessary nodes/edges
- Cross-world edges (T↔I) MUST target L1 or L2 — NEVER L3/L4
- Same-world edges must represent direct, single-step causation
- If a scenario requires a chain of 3+ new edges, that's fine — build the chain through intermediaries"""

        print(f"  Diagnosing {sid}...")
        try:
            response = gemini.call(prompt, temperature=0.1, thinking_budget=16000)
            patch_data = parse_yaml_from_response(response)
        except Exception as e:
            print(f"  WARNING: Failed to diagnose {sid}: {e}")
            continue

        new_nodes = patch_data.get("new_nodes", [])
        new_edges = patch_data.get("new_edges", [])

        if new_nodes or new_edges:
            scenarios_fixed.append(sid)
            # Tag edges with scenario source
            for edge in new_edges:
                edge["scenario_id"] = sid
            all_new_nodes.extend(new_nodes)
            all_new_edges.extend(new_edges)
            print(f"    +{len(new_nodes)} nodes, +{len(new_edges)} edges")
        else:
            print(f"    No fix proposed")

    # Reduce Phase: deduplicate
    seen_nodes = set()
    deduped_nodes = []
    for node in all_new_nodes:
        nid = node.get("id", "")
        if nid not in seen_nodes:
            seen_nodes.add(nid)
            deduped_nodes.append(node)

    seen_edges = set()
    deduped_edges = []
    for edge in all_new_edges:
        pair = (edge.get("from", ""), edge.get("to", ""))
        if pair not in seen_edges:
            seen_edges.add(pair)
            deduped_edges.append(edge)

    # Write patch recipe
    from datetime import datetime, timezone
    recipe = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scenarios_fixed": scenarios_fixed,
            "failures_diagnosed": len(failures),
        },
        "new_nodes": deduped_nodes,
        "new_edges": deduped_edges,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.dump(recipe, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    print(f"\nPatch recipe: {len(deduped_nodes)} nodes, {len(deduped_edges)} edges")
    print(f"Scenarios addressed: {len(scenarios_fixed)}")
    print(f"Written to {output_path}")

    return 0


def cmd_patch(args: argparse.Namespace) -> int:
    """Apply a patch recipe to the graph."""
    import networkx as nx

    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults
    from graph.scenarios import load_scenarios, run_all, print_results

    recipe_path = Path(args.recipe)
    if not recipe_path.exists():
        print(f"ERROR: Recipe not found: {recipe_path}")
        return 1

    recipe = yaml.safe_load(recipe_path.read_text())
    new_nodes = recipe.get("new_nodes", [])
    new_edges = recipe.get("new_edges", [])

    print(f"Patch recipe: {len(new_nodes)} nodes, {len(new_edges)} edges")
    if recipe.get("metadata", {}).get("scenarios_fixed"):
        print(f"Targets scenarios: {', '.join(recipe['metadata']['scenarios_fixed'])}")

    # Validate
    issues = []
    for node in new_nodes:
        nid = node.get("id", "")
        if not NODE_ID_RE.match(nid):
            issues.append(f"Bad node ID format: '{nid}'")
        cat = node.get("category", "")
        if cat and cat not in ALL_L1S:
            issues.append(f"Unknown category '{cat}' for node '{nid}'")
        if not node.get("parent"):
            issues.append(f"Node '{nid}' has no parent")

    new_node_ids = {n.get("id") for n in new_nodes}

    # Load graph for cross-world level validation
    merger_val = TaxonomyMerger(root=PROJECT_ROOT)
    G_val = merger_val.merge()

    for edge in new_edges:
        etype = edge.get("type", "")
        if etype not in CANONICAL_EDGE_TYPES:
            issues.append(f"Non-canonical edge type '{etype}': {edge.get('from')} -> {edge.get('to')}")

        # Cross-world level check: T↔I edges must target L1 or L2
        src_id = edge.get("from", "")
        dst_id = edge.get("to", "")
        src_cat = G_val.nodes[src_id].get("category", "") if G_val.has_node(src_id) else ""
        dst_cat = G_val.nodes[dst_id].get("category", "") if G_val.has_node(dst_id) else ""
        # Check new nodes too
        for nn in new_nodes:
            if nn.get("id") == src_id:
                src_cat = nn.get("category", src_cat)
            if nn.get("id") == dst_id:
                dst_cat = nn.get("category", dst_cat)

        src_is_trigger = src_cat.startswith("T")
        dst_is_trigger = dst_cat.startswith("T")
        is_cross_world = src_cat and dst_cat and (src_is_trigger != dst_is_trigger)

        if is_cross_world:
            # Determine target level — for T→I the target is dst, for I→T the target is src
            # Actually, the "target" in the cross-world sense is whichever is in the other world
            target_id = dst_id if src_is_trigger else src_id
            target_level = None
            if G_val.has_node(target_id):
                target_level = G_val.nodes[target_id].get("level")
            for nn in new_nodes:
                if nn.get("id") == target_id:
                    target_level = nn.get("level", target_level)

            if target_level is not None and target_level > 2:
                issues.append(
                    f"Cross-world edge targets L{target_level} node: "
                    f"{src_id} -> {dst_id} (must target L1/L2 for CONTAINS propagation)"
                )

    if issues:
        print(f"\nValidation issues ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")
        if not args.force:
            print("\nUse --force to apply anyway.")
            return 1

    # Dry run
    if args.dry_run:
        print("\n--- DRY RUN ---")
        if new_nodes:
            print(f"\nWould add {len(new_nodes)} nodes:")
            for node in new_nodes:
                print(f"  {node['id']} (cat={node.get('category')}, parent={node.get('parent')})")
        if new_edges:
            print(f"\nWould add {len(new_edges)} edges:")
            for edge in new_edges:
                print(f"  {edge['from']} --[{edge.get('type')}]--> {edge['to']}")
        return 0

    # Apply nodes — add to the appropriate L1 YAML file
    nodes_added = 0
    for node in new_nodes:
        nid = node["id"]
        cat = node.get("category", "")
        parent = node.get("parent", "")

        # Determine target file from category
        if not cat:
            print(f"  SKIP node '{nid}': no category")
            continue

        data = load_l1_yaml(cat)
        if not data:
            print(f"  SKIP node '{nid}': {cat}.yaml not found")
            continue

        # Check if node already exists
        existing_ids = {n["id"] for n in data.get("nodes", [])}
        if nid in existing_ids:
            print(f"  SKIP node '{nid}': already exists in {cat}.yaml")
            continue

        # Add node
        node_entry = {
            "id": nid,
            "aliases": node.get("aliases", []),
            "category": cat,
            "level": node.get("level", 3),
        }
        data.setdefault("nodes", []).append(node_entry)

        # Add CONTAINS edge from parent
        if parent:
            contains_edge = {
                "from": parent,
                "to": nid,
                "type": "CONTAINS",
                "weight": 0.9,
                "polarity": 1,
                "delay": "IMMEDIATE",
                "description": f"Contains {nid}",
            }
            data.setdefault("edges", []).append(contains_edge)

        save_l1_yaml(cat, data)
        nodes_added += 1
        print(f"  Added node '{nid}' to {cat}.yaml")

    # Apply edges — same-world to source L1 file, cross-world to bridge_edges.yaml
    edges_added = 0
    bridge_edges_to_add = []

    # Load graph to determine node categories
    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()

    for edge in new_edges:
        src = edge["from"]
        dst = edge["to"]

        src_cat = G.nodes[src].get("category", "") if G.has_node(src) else ""
        dst_cat = G.nodes[dst].get("category", "") if G.has_node(dst) else ""

        # Cross-world: one is T*, other is I*
        src_is_trigger = src_cat.startswith("T")
        dst_is_trigger = dst_cat.startswith("T")
        cross_world = src_is_trigger != dst_is_trigger

        edge_entry = {
            "from": src,
            "to": dst,
            "type": edge.get("type", "AFFECTS"),
            "weight": edge.get("weight", 0.5),
            "polarity": edge.get("polarity", 1),
            "delay": edge.get("delay", "SHORT_TERM"),
            "description": edge.get("description", ""),
        }

        if cross_world:
            bridge_edges_to_add.append(edge_entry)
        else:
            # Add to source node's L1 file
            if not src_cat:
                print(f"  SKIP edge {src} -> {dst}: source category unknown")
                continue
            data = load_l1_yaml(src_cat)
            if not data:
                print(f"  SKIP edge {src} -> {dst}: {src_cat}.yaml not found")
                continue
            data.setdefault("edges", []).append(edge_entry)
            save_l1_yaml(src_cat, data)
            edges_added += 1

    # Write bridge edges
    if bridge_edges_to_add:
        bridge_path = TAXONOMY_DIR / "bridge_edges.yaml"
        if bridge_path.exists():
            bridge_data = yaml.safe_load(bridge_path.read_text()) or {}
        else:
            bridge_data = {"nodes": [], "edges": []}
        bridge_data.setdefault("edges", []).extend(bridge_edges_to_add)
        bridge_path.write_text(
            yaml.dump(bridge_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        )
        edges_added += len(bridge_edges_to_add)
        print(f"  Added {len(bridge_edges_to_add)} bridge edge(s) to bridge_edges.yaml")

    print(f"\nApplied: {nodes_added} nodes, {edges_added} edges")

    # Post-patch: rebuild and run full test suite
    print("\n--- Post-patch validation ---")
    merger2 = TaxonomyMerger(root=PROJECT_ROOT)
    G2 = merger2.merge()
    apply_defaults(G2)

    # Check connectivity
    wcc = nx.number_weakly_connected_components(G2)
    orphans = sum(1 for n in G2.nodes() if G2.degree(n) == 0)
    print(f"Graph: {G2.number_of_nodes()} nodes, {G2.number_of_edges()} edges")
    print(f"Components: {wcc}, Orphans: {orphans}")

    # Run scenario tests
    try:
        scenarios = load_scenarios()
        results = run_all(G2, scenarios)
        print_results(results)

        passed = sum(1 for r in results if r["status"] == "PASS")
        failed_count = sum(1 for r in results if r["status"] in ("FAIL", "ERROR"))
        print(f"\nPost-patch: {passed}/{len(results)} passing")

        if failed_count > 0:
            print(f"WARNING: {failed_count} scenario(s) still failing")
    except Exception as e:
        print(f"WARNING: Could not run post-patch tests: {e}")

    return 0


# ---------------------------------------------------------------------------
# Phase 1-2: Bridge Redesign Commands
# ---------------------------------------------------------------------------


def _load_bridge_edges() -> tuple[list[dict], Path]:
    """Load bridge_edges.yaml and return (edges, path)."""
    path = TAXONOMY_DIR / "bridge_edges.yaml"
    if not path.exists():
        return [], path
    data = yaml.safe_load(path.read_text()) or {}
    return data.get("edges", []), path


def _save_bridge_edges(edges: list[dict], path: Path) -> None:
    """Save edges back to bridge_edges.yaml."""
    data = {"edges": edges}
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )


def _get_node_category(G, node_id: str) -> str:
    """Get node category from graph."""
    if G.has_node(node_id):
        return G.nodes[node_id].get("category", "")
    return ""


def cmd_convert_regulatory(args: argparse.Namespace) -> int:
    """Phase 1: Convert REGULATES/MANAGES cross-world edges to node metadata.

    Extracts regulatory edges, stores as regulated_by/managed_by properties
    on target nodes in their L1 YAML files, and removes from bridge_edges.yaml.
    """
    from graph.merge import TaxonomyMerger

    # Load graph for node lookups
    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()

    edges, bridge_path = _load_bridge_edges()
    if not edges:
        print("No bridge edges found.")
        return 1

    # Classify edges
    regulatory = []
    remaining = []
    for e in edges:
        src = e.get("from", "")
        dst = e.get("to", "")
        etype = e.get("type", "")
        src_cat = _get_node_category(G, src)
        dst_cat = _get_node_category(G, dst)
        src_is_t = src_cat.startswith("T")
        dst_is_t = dst_cat.startswith("T")
        is_cross = (src_is_t and not dst_is_t) or (not src_is_t and dst_is_t)

        if is_cross and etype in ("REGULATES", "MANAGES"):
            regulatory.append(e)
        else:
            remaining.append(e)

    if not regulatory:
        print("No REGULATES/MANAGES cross-world edges found.")
        return 0

    print(f"Found {len(regulatory)} REGULATES/MANAGES cross-world edges")

    if args.dry_run:
        print("\n--- DRY RUN ---")
        for e in regulatory:
            prop = "regulated_by" if e["type"] == "REGULATES" else "managed_by"
            print(f"  {e['from']} --[{e['type']}]--> {e['to']}  →  {e['to']}.{prop} += {e['from']}")
        print(f"\nWould remove {len(regulatory)} edges, {len(remaining)} remaining")
        return 0

    # Group by target node's L1 category
    metadata_by_l1: dict[str, dict[str, list[str]]] = {}  # L1 -> {node_id -> [source_ids]}
    for e in regulatory:
        dst = e["to"]
        src = e["from"]
        etype = e["type"]
        dst_cat = _get_node_category(G, dst)
        if not dst_cat:
            print(f"  WARNING: target '{dst}' has no category, skipping")
            continue

        prop = "regulated_by" if etype == "REGULATES" else "managed_by"
        metadata_by_l1.setdefault(dst_cat, {}).setdefault(dst, []).append(
            f"{src}:{prop}"
        )

    # Apply metadata to L1 YAML files
    modified_files = set()
    for l1_id, node_metadata in sorted(metadata_by_l1.items()):
        data = load_l1_yaml(l1_id)
        if not data:
            print(f"  WARNING: {l1_id}.yaml not found, skipping")
            continue

        for node in data.get("nodes", []):
            nid = node["id"]
            if nid in node_metadata:
                for entry in node_metadata[nid]:
                    src_id, prop = entry.split(":")
                    existing = node.get(prop, [])
                    if src_id not in existing:
                        existing.append(src_id)
                    node[prop] = existing

        save_l1_yaml(l1_id, data)
        modified_files.add(l1_id)
        print(f"  {l1_id}: updated {len(node_metadata)} node(s) with metadata")

    # Remove regulatory edges from bridge_edges.yaml
    _save_bridge_edges(remaining, bridge_path)
    print(f"\nRemoved {len(regulatory)} regulatory edges from bridge_edges.yaml")
    print(f"Remaining edges: {len(remaining)}")
    print(f"Modified L1 files: {', '.join(sorted(modified_files))}")

    return 0


def cmd_remove_feedback(args: argparse.Namespace) -> int:
    """Phase 2a: Remove I→T feedback edges from bridge_edges.yaml.

    Identifies edges where source is I-world and target is T-world,
    removes them, and reports which I-world nodes had outgoing T-world edges.
    """
    from graph.merge import TaxonomyMerger

    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()

    edges, bridge_path = _load_bridge_edges()
    if not edges:
        print("No bridge edges found.")
        return 1

    feedback = []
    remaining = []
    for e in edges:
        src = e.get("from", "")
        dst = e.get("to", "")
        src_cat = _get_node_category(G, src)
        dst_cat = _get_node_category(G, dst)
        src_is_i = src_cat.startswith("I")
        dst_is_t = dst_cat.startswith("T")

        if src_is_i and dst_is_t:
            feedback.append(e)
        else:
            remaining.append(e)

    if not feedback:
        print("No I→T feedback edges found.")
        return 0

    print(f"Found {len(feedback)} I→T feedback edges")

    # Report unique I-world source nodes
    from collections import Counter
    i_sources = Counter(e["from"] for e in feedback)
    print(f"\nUnique I-world nodes with T-world outgoing edges: {len(i_sources)}")
    for nid, count in i_sources.most_common(20):
        cat = _get_node_category(G, nid)
        level = G.nodes[nid].get("level", "?") if G.has_node(nid) else "?"
        aliases = G.nodes[nid].get("aliases", [])[:2] if G.has_node(nid) else []
        alias_str = f" ({', '.join(aliases)})" if aliases else ""
        print(f"  {nid} [{cat}/L{level}]{alias_str}: {count} edge(s)")

    if args.dry_run:
        print(f"\n--- DRY RUN --- Would remove {len(feedback)} edges, {len(remaining)} remaining")
        return 0

    _save_bridge_edges(remaining, bridge_path)
    print(f"\nRemoved {len(feedback)} feedback edges from bridge_edges.yaml")
    print(f"Remaining edges: {len(remaining)}")

    return 0


def cmd_audit_nodes(args: argparse.Namespace) -> int:
    """Phase 2b: Audit I-world nodes for possible T-world migration.

    Examines I-world nodes that had outgoing T-world edges (feedback edges)
    and evaluates whether they are aggregate/macro statistics that belong
    in T-world rather than I-world.
    """
    from graph.merge import TaxonomyMerger

    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()

    # Find I-world nodes that have (or had) characteristics of aggregate stats
    # Heuristic markers: names containing "rate", "index", "aggregate", "deficit", "surplus",
    # "gdp", "inflation", "unemployment", "supply", "demand", "market", "trade"
    AGGREGATE_MARKERS = {
        "rate", "index", "aggregate", "deficit", "surplus", "inflation",
        "unemployment", "supply", "demand", "trade", "gdp", "export",
        "import", "production", "output", "consumption", "wage",
    }

    candidates = []
    for nid, attrs in G.nodes(data=True):
        cat = attrs.get("category", "")
        if not cat.startswith("I"):
            continue
        level = attrs.get("level", 0)
        if level < 3:  # L1/L2 are structural, skip
            continue

        # Check name against markers
        name_parts = set(nid.split("_"))
        markers_found = name_parts & AGGREGATE_MARKERS
        if not markers_found:
            continue

        # Check if it has outgoing edges to T-world
        t_targets = []
        for succ in G.successors(nid):
            succ_cat = G.nodes[succ].get("category", "") if G.has_node(succ) else ""
            if succ_cat.startswith("T"):
                t_targets.append(succ)

        # Check aliases for aggregate-like terms
        aliases = attrs.get("aliases", [])

        candidates.append({
            "id": nid,
            "category": cat,
            "level": level,
            "aliases": aliases[:3],
            "markers": sorted(markers_found),
            "t_world_targets": t_targets,
            "recommendation": "REVIEW",
        })

    print(f"Found {len(candidates)} I-world nodes with aggregate characteristics")

    if not candidates:
        return 0

    # Write migration report
    output_path = PROJECT_ROOT / "data" / "node_migration_report.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "metadata": {
            "total_candidates": len(candidates),
            "description": "I-world nodes with aggregate/macro characteristics that may belong in T-world",
            "action_required": "Human review — mark recommendation as MIGRATE or KEEP for each node",
        },
        "candidates": candidates,
    }

    output_path.write_text(
        yaml.dump(report, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    print(f"\nMigration report written to {output_path}")
    for c in candidates:
        markers = ", ".join(c["markers"])
        print(f"  {c['id']} [{c['category']}/L{c['level']}] markers=[{markers}]")

    return 0


def cmd_classify_bridges(args: argparse.Namespace) -> int:
    """Phase 3 prep: Classify remaining T→I edges by (src_L2, dst_L2) parent pairs.

    Groups leaf-to-leaf T→I edges by their L2 ancestor pairs to identify
    which L2→L2 bridges would replace them.
    """
    from collections import defaultdict
    from graph.merge import TaxonomyMerger

    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()

    edges, _ = _load_bridge_edges()

    # Build parent lookup: node -> L2 ancestor
    def get_l2_ancestor(nid: str) -> str | None:
        """Walk up CONTAINS edges to find L2 ancestor."""
        if not G.has_node(nid):
            return None
        level = G.nodes[nid].get("level", 0)
        if level <= 2:
            return nid if level == 2 else None

        # Find parent via incoming CONTAINS edge
        for pred in G.predecessors(nid):
            if G.edges[pred, nid].get("type") == "CONTAINS":
                pred_level = G.nodes[pred].get("level", 0)
                if pred_level == 2:
                    return pred
                elif pred_level > 2:
                    return get_l2_ancestor(pred)
        return None

    # Classify T→I edges
    t_to_i = []
    for e in edges:
        src_cat = _get_node_category(G, e["from"])
        dst_cat = _get_node_category(G, e["to"])
        if src_cat.startswith("T") and dst_cat.startswith("I"):
            t_to_i.append(e)

    print(f"T→I causal edges: {len(t_to_i)}")

    # Group by L2 pairs
    l2_pairs: dict[tuple[str, str], list[dict]] = defaultdict(list)
    unmapped = []
    for e in t_to_i:
        src_l2 = get_l2_ancestor(e["from"])
        dst_l2 = get_l2_ancestor(e["to"])
        if src_l2 and dst_l2:
            l2_pairs[(src_l2, dst_l2)].append(e)
        else:
            unmapped.append(e)

    print(f"Unique L2 parent pairs: {len(l2_pairs)}")
    print(f"Unmapped edges: {len(unmapped)}")

    print(f"\nL2 pair → leaf edge count (sorted by count):")
    for (src_l2, dst_l2), pair_edges in sorted(l2_pairs.items(), key=lambda x: -len(x[1])):
        src_cat = _get_node_category(G, src_l2)
        dst_cat = _get_node_category(G, dst_l2)
        print(f"  {src_l2} ({src_cat}) → {dst_l2} ({dst_cat}): {len(pair_edges)} edge(s)")
        if args.verbose:
            for e in pair_edges:
                print(f"    {e['from']} --[{e['type']}]--> {e['to']}")

    # Write classification
    output_path = TAXONOMY_DIR / "patches" / "bridge_classification.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    classification = {
        "metadata": {
            "total_t_to_i": len(t_to_i),
            "unique_l2_pairs": len(l2_pairs),
            "unmapped": len(unmapped),
        },
        "l2_pairs": [
            {
                "src_l2": src_l2,
                "src_cat": _get_node_category(G, src_l2),
                "dst_l2": dst_l2,
                "dst_cat": _get_node_category(G, dst_l2),
                "leaf_edge_count": len(pair_edges),
                "leaf_edges": [
                    {"from": e["from"], "to": e["to"], "type": e.get("type", "")}
                    for e in pair_edges
                ],
            }
            for (src_l2, dst_l2), pair_edges in sorted(l2_pairs.items(), key=lambda x: -len(x[1]))
        ],
        "unmapped": [
            {"from": e["from"], "to": e["to"], "type": e.get("type", "")}
            for e in unmapped
        ],
    }

    output_path.write_text(
        yaml.dump(classification, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )
    print(f"\nClassification written to {output_path}")

    return 0


def cmd_generate_l2_bridges(args: argparse.Namespace) -> int:
    """Phase 3: Generate L2→L2 T→I bridge matrix using Gemini.

    For each T-L1, presents all T-L2 nodes and all I-L2 nodes to Gemini,
    asks which pairs have direct causal mechanisms.
    """
    from graph.merge import TaxonomyMerger

    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()

    # Collect L2 nodes by world
    t_l2_by_l1: dict[str, list[dict]] = {}
    i_l2_by_l1: dict[str, list[dict]] = {}

    for nid, attrs in G.nodes(data=True):
        level = attrs.get("level", 0)
        if level != 2:
            continue
        cat = attrs.get("category", "")
        aliases = attrs.get("aliases", [])

        # Get children (L3+)
        children = []
        for succ in G.successors(nid):
            if G.edges[nid, succ].get("type") == "CONTAINS":
                children.append(succ)

        entry = {"id": nid, "aliases": aliases[:3], "children": children}

        if cat.startswith("T"):
            t_l2_by_l1.setdefault(cat, []).append(entry)
        elif cat.startswith("I"):
            i_l2_by_l1.setdefault(cat, []).append(entry)

    # Build I-world reference text (same for all calls)
    i_world_text = ""
    for i_id in sorted(i_l2_by_l1):
        i_name = IMPACT_L1S.get(i_id, i_id)
        i_world_text += f"\n### {i_id}: {i_name}\n"
        for l2 in i_l2_by_l1[i_id]:
            children_str = ", ".join(l2["children"][:8])
            if len(l2["children"]) > 8:
                children_str += f", ... (+{len(l2['children']) - 8} more)"
            i_world_text += f"  - **{l2['id']}** ({', '.join(l2['aliases'][:2])}): [{children_str}]\n"

    constitution = load_constitution()
    gemini = GraphGemini()
    all_bridges = []

    # Load existing bridge classification if available
    class_path = TAXONOMY_DIR / "patches" / "bridge_classification.yaml"
    existing_pairs_text = ""
    if class_path.exists():
        class_data = yaml.safe_load(class_path.read_text()) or {}
        existing_pairs = class_data.get("l2_pairs", [])
        if existing_pairs:
            existing_pairs_text = "\n## Existing leaf-level bridges (grouped by L2 pair):\n"
            for pair in existing_pairs[:30]:
                existing_pairs_text += f"  - {pair['src_l2']} → {pair['dst_l2']}: {pair['leaf_edge_count']} existing leaf edges\n"

    # Per T-L1 Gemini call
    for t_id in sorted(t_l2_by_l1):
        t_name = TRIGGER_L1S.get(t_id, t_id)
        t_l2s = t_l2_by_l1[t_id]

        t_section = f"## {t_id}: {t_name}\n"
        for l2 in t_l2s:
            children_str = ", ".join(l2["children"][:10])
            if len(l2["children"]) > 10:
                children_str += f", ... (+{len(l2['children']) - 10} more)"
            t_section += f"  - **{l2['id']}** ({', '.join(l2['aliases'][:2])}): [{children_str}]\n"

        prompt = f"""You are designing the L2→L2 bridge layer for an Indian citizen impact knowledge graph.

## Constitution:
{constitution[:4000]}

## Architecture Context
The graph has two worlds:
- **Trigger world** (T1-T5): systemic forces that drive change
- **Impact world** (I1-I11): citizen-facing outcomes

Previously, all T→I bridges were leaf-to-leaf (L3/L4→L3/L4). We are redesigning to use
L2→L2 bridges. The traversal engine follows CONTAINS edges downward, so one L2→L2 edge
automatically propagates to ALL children of the target L2.

## Current Trigger L1 — {t_id}: {t_name}
{t_section}

## All Impact L2 subcategories:
{i_world_text}
{existing_pairs_text}
## Task
For each T-L2 in {t_id}, evaluate EVERY I-L2 pair. Rate each:
- **strong**: Direct causal mechanism applies to MOST children of the I-L2. Include as bridge.
- **moderate**: Mechanism exists but only for SOME children. Include with lower weight.
- **none**: No direct causal mechanism. Skip.

## Rules
1. Each bridge must represent ONE direct causal mechanism
2. The mechanism must apply to most/all children of the target I-L2
3. If it only affects 1-2 specific children, it's a leaf edge, not an L2 bridge
4. Use appropriate edge types: AFFECTS, PRODUCES, DISRUPTS, SUPPLIES, DEPENDS_ON, FUNDS
5. Do NOT use REGULATES or MANAGES (those are metadata now)
6. Weight: strong=0.7-0.9, moderate=0.4-0.6
7. Polarity: +1 (positive correlation) or -1 (inverse)
8. Delay: IMMEDIATE, SHORT_TERM, MEDIUM_TERM, LONG_TERM

## Output Format (YAML only):
```yaml
bridges:
  - from: t_l2_node_id
    to: i_l2_node_id
    type: AFFECTS
    weight: 0.8
    polarity: -1
    delay: MEDIUM_TERM
    strength: strong
    description: "One sentence explaining the direct causal mechanism"
```"""

        print(f"\nGenerating L2 bridges: {t_id} ({t_name}) → all Impact L2s...")
        try:
            response = gemini.call(prompt, temperature=0.1, thinking_budget=32000, max_output_tokens=16000)
            data = parse_yaml_from_response(response)
        except Exception as e:
            print(f"  WARNING: Failed for {t_id}: {e}")
            continue

        bridges = data.get("bridges", [])
        # Tag with source
        for b in bridges:
            b["source_t_l1"] = t_id

        all_bridges.extend(bridges)
        strong = sum(1 for b in bridges if b.get("strength") == "strong")
        moderate = sum(1 for b in bridges if b.get("strength") == "moderate")
        print(f"  {t_id}: {len(bridges)} bridges ({strong} strong, {moderate} moderate)")

    # Write bridge matrix
    output_path = TAXONOMY_DIR / "patches" / "bridge_matrix.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    matrix = {
        "metadata": {
            "total_bridges": len(all_bridges),
            "strong": sum(1 for b in all_bridges if b.get("strength") == "strong"),
            "moderate": sum(1 for b in all_bridges if b.get("strength") == "moderate"),
            "description": "L2→L2 T→I bridge matrix for human review",
        },
        "bridges": all_bridges,
    }

    output_path.write_text(
        yaml.dump(matrix, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    print(f"\nTotal L2 bridges: {len(all_bridges)}")
    print(f"Written to {output_path}")
    print("Review the matrix, then run 'apply-l2-bridges' to apply.")

    return 0


def cmd_apply_l2_bridges(args: argparse.Namespace) -> int:
    """Phase 4: Apply approved L2 bridges and remove redundant leaf edges."""
    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults

    matrix_path = Path(args.matrix) if args.matrix else TAXONOMY_DIR / "patches" / "bridge_matrix.yaml"
    if not matrix_path.exists():
        print(f"ERROR: Bridge matrix not found at {matrix_path}")
        print("Run 'generate-l2-bridges' first.")
        return 1

    matrix = yaml.safe_load(matrix_path.read_text()) or {}
    new_bridges = matrix.get("bridges", [])
    if not new_bridges:
        print("No bridges in matrix.")
        return 0

    # Load graph for parent lookups
    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()

    # Build L2 ancestor lookup
    def get_l2_ancestor(nid: str) -> str | None:
        if not G.has_node(nid):
            return None
        level = G.nodes[nid].get("level", 0)
        if level <= 2:
            return nid if level == 2 else None
        for pred in G.predecessors(nid):
            if G.edges[pred, nid].get("type") == "CONTAINS":
                pred_level = G.nodes[pred].get("level", 0)
                if pred_level == 2:
                    return pred
                elif pred_level > 2:
                    return get_l2_ancestor(pred)
        return None

    # Get the L2 pairs covered by new bridges
    covered_pairs = set()
    for b in new_bridges:
        covered_pairs.add((b["from"], b["to"]))

    # Load existing bridge edges
    edges, bridge_path = _load_bridge_edges()

    # Separate: keep edges NOT covered by L2 bridges
    kept = []
    removed = []
    for e in edges:
        src_cat = _get_node_category(G, e["from"])
        dst_cat = _get_node_category(G, e["to"])
        if not (src_cat.startswith("T") and dst_cat.startswith("I")):
            kept.append(e)
            continue

        src_l2 = get_l2_ancestor(e["from"])
        dst_l2 = get_l2_ancestor(e["to"])
        if src_l2 and dst_l2 and (src_l2, dst_l2) in covered_pairs:
            removed.append(e)
        else:
            kept.append(e)  # Keep narrow edges not covered by L2 bridges

    print(f"Existing T→I leaf edges removed (covered by L2): {len(removed)}")
    print(f"Existing edges kept (narrow or non-T→I): {len(kept)}")

    if args.dry_run:
        print(f"\n--- DRY RUN ---")
        print(f"Would add {len(new_bridges)} L2 bridges")
        print(f"Would remove {len(removed)} redundant leaf edges")
        return 0

    # Build new bridge_edges.yaml: kept edges + new L2 bridges
    l2_bridge_edges = []
    for b in new_bridges:
        l2_bridge_edges.append({
            "from": b["from"],
            "to": b["to"],
            "type": b.get("type", "AFFECTS"),
            "weight": b.get("weight", 0.5),
            "polarity": b.get("polarity", 1),
            "delay": b.get("delay", "SHORT_TERM"),
            "description": b.get("description", ""),
        })

    final_edges = kept + l2_bridge_edges
    _save_bridge_edges(final_edges, bridge_path)

    print(f"\nNew bridge_edges.yaml: {len(final_edges)} edges")
    print(f"  Kept from old: {len(kept)}")
    print(f"  New L2 bridges: {len(l2_bridge_edges)}")

    # Post-apply validation
    print("\n--- Post-apply validation ---")
    merger2 = TaxonomyMerger(root=PROJECT_ROOT)
    G2 = merger2.merge()
    apply_defaults(G2)
    print(f"Graph: {G2.number_of_nodes()} nodes, {G2.number_of_edges()} edges")

    return 0


def cmd_generate_l2_laterals(args: argparse.Namespace) -> int:
    """Phase 5: Generate same-world L2→L2 lateral edges using Gemini."""
    from graph.merge import TaxonomyMerger

    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()

    world = args.world
    if world not in ("impact", "trigger"):
        print("ERROR: --world must be 'impact' or 'trigger'")
        return 1

    l1s = IMPACT_L1S if world == "impact" else TRIGGER_L1S

    # Collect L2 nodes by L1
    l2_by_l1: dict[str, list[dict]] = {}
    for nid, attrs in G.nodes(data=True):
        level = attrs.get("level", 0)
        cat = attrs.get("category", "")
        if level != 2 or cat not in l1s:
            continue
        children = [
            succ for succ in G.successors(nid)
            if G.edges[nid, succ].get("type") == "CONTAINS"
        ]
        l2_by_l1.setdefault(cat, []).append({
            "id": nid,
            "aliases": attrs.get("aliases", [])[:3],
            "children": children,
        })

    # Build full world text
    world_text = ""
    for l1_id in sorted(l2_by_l1):
        l1_name = l1s.get(l1_id, l1_id)
        world_text += f"\n### {l1_id}: {l1_name}\n"
        for l2 in l2_by_l1[l1_id]:
            children_str = ", ".join(l2["children"][:8])
            if len(l2["children"]) > 8:
                children_str += f", ... (+{len(l2['children']) - 8} more)"
            world_text += f"  - **{l2['id']}** ({', '.join(l2['aliases'][:2])}): [{children_str}]\n"

    constitution = load_constitution()
    gemini = GraphGemini()

    # Get L1 pairs to evaluate
    l1_ids = sorted(l2_by_l1.keys())
    all_laterals = []

    for i, src_l1 in enumerate(l1_ids):
        for dst_l1 in l1_ids[i + 1:]:
            src_name = l1s[src_l1]
            dst_name = l1s[dst_l1]

            prompt = f"""You are designing L2→L2 lateral edges within the {world} world of an Indian citizen impact knowledge graph.

## Context
The graph has L2 subcategories under each L1. We need lateral (same-world) edges connecting
L2 nodes across different L1s where direct causal mechanisms exist.

The traversal engine follows CONTAINS edges downward, so one L2→L2 edge
automatically propagates to ALL children.

## {world.title()} World L2 Subcategories:
{world_text}

## Task
Find L2→L2 causal connections between {src_l1} ({src_name}) and {dst_l1} ({dst_name}).
Consider BOTH directions: {src_l1}→{dst_l1} AND {dst_l1}→{src_l1}.

## Rules
1. Each edge must represent ONE direct causal mechanism
2. Mechanism must apply to most/all children of the target L2
3. Use edge types: AFFECTS, PRODUCES, DISRUPTS, SUPPLIES, DEPENDS_ON, FUNDS, COMPETES_WITH
4. Weight: 0.4-0.9
5. Polarity: +1 or -1
6. Be selective — only include strong, well-established causal links

## Output Format (YAML only):
```yaml
laterals:
  - from: src_l2_id
    to: dst_l2_id
    type: AFFECTS
    weight: 0.7
    polarity: 1
    delay: SHORT_TERM
    description: "Direct causal mechanism"
```

If no strong connections exist between these two L1s, output:
```yaml
laterals: []
```"""

            print(f"  {src_l1}↔{dst_l1}...", end=" ", flush=True)
            try:
                response = gemini.call(prompt, temperature=0.1, thinking_budget=16000)
                data = parse_yaml_from_response(response)
                laterals = data.get("laterals", [])
                for lat in laterals:
                    lat["source_pair"] = f"{src_l1}↔{dst_l1}"
                all_laterals.extend(laterals)
                print(f"{len(laterals)} edges")
            except Exception as e:
                print(f"FAILED: {e}")
                continue

    # Write laterals
    output_path = TAXONOMY_DIR / "patches" / f"l2_laterals_{world}.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "metadata": {
            "world": world,
            "total_laterals": len(all_laterals),
        },
        "laterals": all_laterals,
    }

    output_path.write_text(
        yaml.dump(output, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    print(f"\nTotal {world} L2 laterals: {len(all_laterals)}")
    print(f"Written to {output_path}")

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
    p_bridges = sub.add_parser("generate-bridges", help="Generate T->I bridge + I->T feedback edges")
    p_bridges.add_argument("--append", action="store_true", help="Add to existing bridge_edges.yaml instead of overwriting")
    p_bridges.add_argument("--per-impact", action="store_true", dest="per_impact", help="Run per-Impact-L1 instead of per-Trigger-L1")

    # generate-feedback
    sub.add_parser("generate-feedback", help="(Included in generate-bridges)")

    # full-review
    sub.add_parser("full-review", help="End-to-end validation with Gemini")

    # test
    p = sub.add_parser("test", help="Run scenario tests against the graph")
    p.add_argument("--domain", help="Filter by domain (e.g., energy, monetary)")
    p.add_argument("--id", help="Run a single scenario by ID")
    p.add_argument("--export", help="Export failures to this path")
    p.add_argument("--scenarios", help="Path to scenarios YAML (default: taxonomy/scenarios.yaml)")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # diagnose
    p = sub.add_parser("diagnose", help="Diagnose failed scenarios and generate patch recipe")
    p.add_argument("--input", help="Path to failed_scenarios.json (default: data/failed_scenarios.json)")
    p.add_argument("--output", help="Path for patch recipe output (default: taxonomy/patches/patch_recipe.yaml)")

    # generate-scenarios
    p = sub.add_parser("generate-scenarios", help="Generate test scenarios via Gemini")
    p.add_argument("--domain", required=True, help="Domain (energy, monetary, tech, climate, employment, trade, social, governance)")
    p.add_argument("--headlines", help="Path to headlines file for grounding")
    p.add_argument("--count", type=int, default=20, help="Number of scenarios to generate")

    # patch
    p = sub.add_parser("patch", help="Apply a patch recipe to the graph")
    p.add_argument("recipe", help="Path to patch recipe YAML")
    p.add_argument("--dry-run", action="store_true", help="Print changes without applying")
    p.add_argument("--force", action="store_true", help="Apply despite validation issues")

    # --- Bridge Redesign Commands ---

    # convert-regulatory (Phase 1)
    p = sub.add_parser("convert-regulatory", help="Convert REGULATES/MANAGES cross-world edges to node metadata")
    p.add_argument("--dry-run", action="store_true", help="Preview without modifying files")

    # remove-feedback (Phase 2a)
    p = sub.add_parser("remove-feedback", help="Remove I→T feedback edges from bridge_edges.yaml")
    p.add_argument("--dry-run", action="store_true", help="Preview without modifying files")

    # audit-nodes (Phase 2b)
    sub.add_parser("audit-nodes", help="Audit I-world nodes for T-world migration candidates")

    # classify-bridges (Phase 3 prep)
    p = sub.add_parser("classify-bridges", help="Classify T→I edges by L2 parent pairs")
    p.add_argument("--verbose", "-v", action="store_true", help="Show individual edges per pair")

    # generate-l2-bridges (Phase 3)
    sub.add_parser("generate-l2-bridges", help="Generate L2→L2 T→I bridge matrix via Gemini")

    # apply-l2-bridges (Phase 4)
    p = sub.add_parser("apply-l2-bridges", help="Apply L2 bridges and remove redundant leaf edges")
    p.add_argument("--matrix", help="Path to bridge matrix YAML (default: taxonomy/patches/bridge_matrix.yaml)")
    p.add_argument("--dry-run", action="store_true", help="Preview without modifying files")

    # generate-l2-laterals (Phase 5)
    p = sub.add_parser("generate-l2-laterals", help="Generate same-world L2→L2 lateral edges via Gemini")
    p.add_argument("--world", required=True, choices=["impact", "trigger"])

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
        "test": cmd_test,
        "diagnose": cmd_diagnose,
        "generate-scenarios": cmd_generate_scenarios,
        "patch": cmd_patch,
        # Bridge redesign commands
        "convert-regulatory": cmd_convert_regulatory,
        "remove-feedback": cmd_remove_feedback,
        "audit-nodes": cmd_audit_nodes,
        "classify-bridges": cmd_classify_bridges,
        "generate-l2-bridges": cmd_generate_l2_bridges,
        "apply-l2-bridges": cmd_apply_l2_bridges,
        "generate-l2-laterals": cmd_generate_l2_laterals,
    }

    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
