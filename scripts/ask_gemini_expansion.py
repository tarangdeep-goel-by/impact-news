"""One-off: ask Gemini 3.1-pro about graph expansion architecture."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

client = genai.Client(api_key=settings.gemini_api_key)

PROMPT = """You are the architect of a causal knowledge graph for Impact News — a system that traces how macro events affect individual citizens in India.

## Current Graph Structure

The graph has two worlds:
- **Trigger world** (5 L1s: T1-T5) — system-level entities (governments, markets, climate systems)
- **Impact world** (11 L1s: I1-I11) — citizen-level entities (food prices, EMI, health, education)

Each L1 has a vertical tree: L1 → L2 categories → L3 leaf nodes (sometimes L4).
Within each world, nodes connect horizontally via lateral edges (intra-L1) and portal edges (cross-L1).
Between worlds: bridge edges (T→I) and feedback edges (I→T, delay >= MEDIUM_TERM).

Current stats: 738 nodes, 1831 edges, 1 connected component, 0 orphans.

## The Problem

We ran a full review with 30 real-world scenario traces. 12 were COMPLETE, 10 PARTIAL, 5 BROKEN. The broken/partial scenarios reveal gaps — but the gaps are heterogeneous:

**Type 1 — Missing leaf node:** No node exists to represent something in the causal chain. E.g., no intermediary between GST Council (T2) and retail snack prices (I1). The real chain is: GST Council → GST rate slab (missing?) → packaged food prices → household budget.

**Type 2 — Missing edge between existing nodes:** Both endpoints exist but aren't connected. E.g., smartphone_device (I10) and upi_transaction_success (I10) both exist but no DEPENDS_ON edge.

**Type 3 — Missing intermediary path:** The start and end exist but the chain needs intermediary nodes AND edges. E.g., union_budget_framework (T2) → ??? → lpg_cylinder (I2). The real chain goes through petroleum subsidy allocation, oil marketing companies, etc.

## Design Constraints

1. This must be **repeatable and deterministic** — we can't just hand-edit YAML. We need a pipeline command.
2. The graph will keep evolving. New scenarios will reveal new gaps. The expansion mechanism must be a first-class tool, not a one-off fix.
3. The Constitution (17 rules) must be respected — entity principle, trigger/impact classification, DAG constraint, etc.
4. When we identify one gap, we should examine the neighborhood — what else around it is missing?
5. Adding a node means: structural insertion (CONTAINS edges), then lateral wiring (I-I or T-T), then bridge wiring (T-I, I-T). Running the full 16x16 L1 cycle is too expensive for single-node additions.

## Our Current Thinking

A two-phase approach:

**Phase A: Diagnose**
```
graph_builder.py diagnose <scenario_or_gap_description>
```
- Feed Gemini the broken scenario + the relevant subgraph neighborhood (the L1s involved, their full trees, existing edges)
- Gemini classifies the gap (Type 1/2/3) and proposes:
  - For Type 1: new node(s) with L1/L2 placement, aliases
  - For Type 2: missing edge(s) with full properties
  - For Type 3: intermediary chain with nodes + edges
- Gemini also examines the neighborhood: "if GST to FMCG is broken, what about GST to restaurants, GST to textiles?"

**Phase B: Patch**
```
graph_builder.py patch <diagnosis_output>
```
- Inserts new nodes structurally (CONTAINS up hierarchy)
- Runs scoped edge generation (only affected L1s, not full 16x16)
- Validates DAG, no cycles, connectivity

## Questions for You

Think deeply about this. Consider:

1. **Is the diagnose then patch two-phase approach sound?** Or should it be structured differently?
2. **How should we scope the edge generation after inserting a node?** Running all T-I/I-T/I-I for just one new node is wasteful. What's the minimum neighborhood?
3. **Should diagnosis be per-scenario or batched?** 10 PARTIAL + 5 BROKEN = 15 scenarios. Some may share root causes (e.g., multiple scenarios broken because GST intermediaries are missing).
4. **How do we handle Type 3 (intermediary paths)?** These are the hardest — we might need to add nodes to BOTH worlds to complete a chain. What's the right decomposition?
5. **What about the review cycle?** After patching, how do we verify the fix actually closes the scenario without regressing others?
6. **Any alternative architecture you'd propose?** Maybe we're overcomplicating this. What would you do differently?

Be opinionated. Think about what will work at scale as this graph grows from 738 to 1000+ nodes over time.
"""

response = client.models.generate_content(
    model="gemini-3.1-pro-preview",
    contents=PROMPT,
    config=genai.types.GenerateContentConfig(
        temperature=0.3,
        thinking_config=genai.types.ThinkingConfig(thinking_budget=32000),
        max_output_tokens=16000,
    ),
)
print(response.text)
