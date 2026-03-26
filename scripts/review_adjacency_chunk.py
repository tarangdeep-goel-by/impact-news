"""Review an adjacency chunk via Gemini 3.1 Pro Preview.

Combined Phase 4c (edge quality) + 4d (weight re-rating) in one call.

Usage:
    python3 scripts/review_adjacency_chunk.py <chunk_number>
    python3 scripts/review_adjacency_chunk.py 1    # Review chunk_01
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.graph_builder import GraphGemini

TAXONOMY_MD = PROJECT_ROOT / "taxonomy" / "TAXONOMY.md"
CHUNKS_DIR = PROJECT_ROOT / "taxonomy" / "eval_results" / "adjacency_chunks"
OUTPUT_DIR = PROJECT_ROOT / "taxonomy" / "eval_results"

CONSTITUTION_EXCERPT = """
### Rule 12b: Edge Type Semantics

When assigning an edge type, evaluate in this priority order. Pick the **first** that fits:

| Priority | Type | Test |
|----------|------|------|
| 1 | PRODUCES | Does A literally create or generate B? |
| 2 | SUPPLIES | Does A provide physical goods, data, or labor to B? |
| 3 | FUNDS | Does A directly pay for or financially back B? |
| 4 | DISRUPTS | Does A physically or systematically block, break, or halt B? |
| 5 | DEPENDS_ON | Is B structurally unable to function without A? |
| 6 | REGULATES | Does A set rules/constraints that B must operate within? (same-world only) |
| 7 | MANAGES | Does A have administrative authority over B? (same-world only) |
| 8 | EMPLOYS | Does A hire/engage B as labor? |
| 9 | COMPETES_WITH | Does A take market share from B? |
| 10 | AFFECTS | **Fallback.** A changes the price, frequency, or quality of B. |

AFFECTS is the fallback, not the default. If a more specific verb applies, use it.

Cross-world restriction: REGULATES and MANAGES must NOT cross the T→I boundary.

### Rule 21: Direct Causation Principle (No Bypassing)

Every causal edge must represent a direct causal mechanism. Do not draw an edge from A to C if the causal signal must pass through an intermediate node B.

The Bypassing Test: Before creating an edge A→B, articulate the exact physical, economic, or behavioral mechanism. If your explanation requires a third entity that exists (or should exist) in the taxonomy, the edge is invalid.

### Rule 20: I→I Lateral Edge Targeting

NEVER TARGET L2. Impact L2 nodes are organizational groupings, not causal entities.

### Weight Calibration Guidelines

Weight represents causal strength 0.0-1.0. Consider:
- Mechanism directness: how tight is the coupling?
- Typical magnitude in India: how large is the effect in practice?
- Conditional probability: when A changes, how often does B actually change?
- Time lag: faster transmission = higher weight

Reference ranges:
- 0.9-1.0: Near-deterministic (monsoon→crop damage, RBI rate→EMI)
- 0.7-0.85: Strong, reliable mechanism (crude oil→petrol price)
- 0.5-0.65: Moderate, conditional (smog→asthma, unemployment→crime)
- 0.3-0.45: Weak or indirect (festival→traffic, urbanization→noise)
- Below 0.3: Questionable — should the edge exist?
"""

PROMPT_TEMPLATE = """You are auditing edge quality and weights in an Indian causal impact knowledge graph.

## Constitution (Key Rules)
{constitution}

## Chunk to Review
{chunk}

## Instructions

For EACH outgoing edge on EACH node in this chunk, do TWO things:

### 1. Quality Check
- **Rule 21**: Does A→B pass the bypassing test? Is the mechanism direct?
- **Edge Type**: Is AFFECTS used where PRODUCES/SUPPLIES/FUNDS/DISRUPTS fits better?
- **Polarity**: Is the direction correct? (+1 = A increases → B increases; -1 = A increases → B decreases)
- **Description**: Does it prove the direct mechanism?

### 2. Weight Re-Rating
Rate the causal strength 0.0-1.0 based on: mechanism directness, typical magnitude in India, conditional probability, time lag. Use the reference ranges above.

## Output Format

For each node, output ONE of these per edge:

**PASS** from→to w=X.XX (current=Y.YY) — Edge valid. [brief reason if weight changed significantly]

**FIX** from→to — type should be NEW_TYPE (was OLD_TYPE). w=X.XX (current=Y.YY). Reason: ...

**KILL** from→to — Rule 21 violation. Intermediary: node_C. [or: weight too low, edge shouldn't exist]

**ADD** from→to type=TYPE w=X.XX pol=N delay=DELAY — Missing direct edge. Description: ...

Group output by node. Skip nodes where all edges pass unchanged.

After all nodes, provide:
## SUMMARY
- Edges reviewed: N
- PASS (unchanged): N
- PASS (weight adjusted): N
- FIX (type change): N
- KILL: N
- ADD: N

## WEIGHT OVERRIDES
List ALL edges with their final weights in YAML format:
```yaml
edges:
- from: X
  to: Y
  weight: 0.XX
```
Only include edges where weight differs from current value by >= 0.05.
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/review_adjacency_chunk.py <chunk_number>")
        sys.exit(1)

    chunk_num = int(sys.argv[1])
    chunk_path = CHUNKS_DIR / f"chunk_{chunk_num:02d}.yaml"

    if not chunk_path.exists():
        print(f"Chunk not found: {chunk_path}")
        sys.exit(1)

    chunk_content = chunk_path.read_text()
    prompt = PROMPT_TEMPLATE.format(
        constitution=CONSTITUTION_EXCERPT,
        chunk=chunk_content,
    )

    print(f"Chunk {chunk_num}: {len(chunk_content)} chars, prompt total: {len(prompt)} chars")
    print("Calling Gemini 3.1 Pro Preview...")

    gemini = GraphGemini()
    response = gemini.call(prompt, thinking_budget=24000, max_output_tokens=65000)

    # Save raw response
    out_path = OUTPUT_DIR / f"review_chunk_{chunk_num:02d}.md"
    out_path.write_text(response)
    print(f"Response saved to {out_path}")

    # Extract weight overrides YAML block if present
    if "```yaml" in response:
        yaml_blocks = response.split("```yaml")
        for block in yaml_blocks[1:]:
            yaml_content = block.split("```")[0].strip()
            if "weight:" in yaml_content:
                weight_path = OUTPUT_DIR / f"rerate_chunk_{chunk_num:02d}_weights.yaml"
                weight_path.write_text(yaml_content)
                print(f"Weight overrides saved to {weight_path}")
                break

    # Print summary section
    if "## SUMMARY" in response:
        summary = response.split("## SUMMARY")[1].split("## WEIGHT")[0]
        print(f"\n{summary.strip()}")


if __name__ == "__main__":
    main()
