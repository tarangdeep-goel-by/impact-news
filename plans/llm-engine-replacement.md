# Plan: LLM Impact Engine (v0)

## Context

The impact-news project uses a hand-coded causal graph (738 nodes, 1831 edges) + Causal Shock Propagation engine to score article impacts. This is rigid and expensive to maintain. We want an LLM engine that reasons about impacts directly, using the same taxonomy as a controlled vocabulary.

**Goal:** Build an LLM engine that takes an article, classifies its trigger using T-trees, identifies impacted I-tree leaf nodes, and scores them — then compare side-by-side with the graph engine via golden tests.

**Scope:** v0 comparison only. No caching, no new node proposals, no pipeline integration yet.

**Constraint:** Additive — don't modify existing graph code.

## Architecture

```
Article → Gemini → { trigger: T-node, impacts: [I-leaf nodes with scores] }
                         ↕
              T+I taxonomy as prompt context
```

Gemini gets the full taxonomy (T1-T5, I1-I11, all levels down to leaves) as structured context. It:
1. Classifies the article's trigger to T-node(s)
2. Reasons about causal chains from trigger → impact
3. Outputs impacted I-tree leaf nodes with probability, magnitude, polarity, delay, mechanism

Impacts land on **leaf nodes** unless multiple leaves in the same branch are affected (then the parent).

## File Layout

```
engine/                              # NEW package
├── __init__.py
├── base.py                          # ImpactEngine Protocol
├── llm_engine.py                    # LLMImpactEngine (Gemini calls)
├── taxonomy_context.py              # Load T+I trees, format for prompt
└── prompt.py                        # Prompt template

tests/
├── golden/
│   ├── cases.yaml                   # EXISTING (no changes)
│   └── runner.py                    # NEW: golden test runner for both engines
└── scenario_adapter.py              # NEW: adapter for graph scenarios on LLM engine

config.py                            # MODIFY: add engine_mode setting
```

## Implementation Steps

### Step 1: Taxonomy Context (`engine/taxonomy_context.py`)

Load all T*.yaml and I*.yaml files. Build a structured representation:

```python
class TaxonomyContext:
    def load() -> TaxonomyContext
    def format_t_trees() -> str       # Full T-tree hierarchy for prompt
    def format_i_trees() -> str       # Full I-tree hierarchy for prompt
    def get_all_i_leaf_ids() -> set   # For validating Gemini output
    def get_all_t_node_ids() -> set
    def node_to_l1(node_id) -> str    # Reverse lookup: node → L1 category
```

Formats trees as indented text with node IDs + aliases at every level. Full depth — L1→L2→L3→L4 where they exist.

### Step 2: Engine Protocol (`engine/base.py`)

```python
class ImpactResult(TypedDict):
    node: str           # I-tree node ID
    probability: float  # 0-1, likelihood this is affected
    magnitude: float    # 0-1, how severely
    polarity: int       # +1 or -1
    delay: str          # IMMEDIATE / SHORT_TERM / MEDIUM_TERM / LONG_TERM
    mechanism: str      # 1-line causal chain explanation
    path: list[str]     # [trigger_node, ..., impact_node]

class ImpactEngine(Protocol):
    def evaluate_article(self, title: str, summary: str) -> list[ImpactResult]:
        """Score an article's impacts on I-tree leaf nodes."""
```

### Step 3: LLM Engine (`engine/llm_engine.py`)

```python
class LLMImpactEngine:
    def __init__(self, taxonomy: TaxonomyContext, gemini: GeminiClient):
        ...

    def evaluate_article(self, title: str, summary: str) -> list[ImpactResult]:
        prompt = build_prompt(self.taxonomy, title, summary)
        response = self.gemini.generate(prompt)
        return parse_impacts(response, self.taxonomy)
```

**Prompt structure** (`engine/prompt.py`):
1. System: "You are a causal impact analyst for Indian citizens."
2. T-tree context: "These are trigger categories (macro/system events):"
3. I-tree context: "These are impact dimensions (citizen-level). Pick from these leaf nodes:"
4. Article: title + summary
5. Instructions: "Identify the trigger T-node(s). Then list every I-tree leaf node causally affected. Output JSON."
6. Output schema: `{ trigger: [t_node_ids], impacts: [{node, probability, magnitude, polarity, delay, mechanism}] }`
7. Rules: "Only genuine causal mechanisms. Not vague relatedness. If a whole branch is affected, use the parent node instead of listing every leaf."

**Parsing:** Validate node IDs against taxonomy. Skip unknown nodes. Warn on any.

### Step 4: Graph Engine Adapter

Wrap existing `CausalMarkovEngine` to satisfy the same `ImpactEngine` protocol:

```python
class GraphImpactEngine:
    def evaluate_article(self, title: str, summary: str) -> list[ImpactResult]:
        # Use existing: extract tags → FAISS match → run engine → return results
```

This reuses `matcher.py` tag extraction + FAISS + the graph engine, just wrapped in the protocol interface.

### Step 5: Golden Test Runner (`tests/golden/runner.py`)

```bash
python -m tests.golden.runner                    # Both engines side-by-side
python -m tests.golden.runner --engine graph      # Graph only
python -m tests.golden.runner --engine llm        # LLM only
```

For each golden case:
1. Feed article title/summary to both engines
2. Collect impact results
3. Check `must_hit` / `must_miss` nodes (direct leaf match or ancestor match via taxonomy)
4. Compare: which engine hits more must_hits, fewer must_misses
5. Report side-by-side table with pass/fail per case

### Step 6: Scenario Adapter (`tests/scenario_adapter.py`)

Map existing graph scenarios to LLM engine:
- Type A (structural): SKIP — graph-specific
- Type B/C/D/E: feed trigger as article, check if expected I-nodes appear in output

```bash
python -m tests.scenario_adapter               # LLM engine on applicable scenarios
python -m tests.scenario_adapter --compare      # Side-by-side
```

## Execution Order

```
Step 1 (taxonomy context) ─── Step 3 (LLM engine) ──┐
                                                      ├── Step 5 (golden runner)
Step 2 (protocol) ──────────── Step 4 (graph adapter)─┘
                                                      └── Step 6 (scenario adapter)
```

Steps 1+2 are independent. Steps 3+4 are independent (after 1+2). Steps 5+6 are independent (after 3+4).

## Verification

1. `python -m tests.golden.runner --engine graph` — graph baseline works through new runner
2. `python -m tests.golden.runner --engine llm` — LLM engine produces results
3. `python -m tests.golden.runner` — side-by-side comparison table
4. `python -m tests.scenario_adapter --compare` — scenario pass rates
5. `python -m graph.scenarios` — existing graph tests still pass (no regression)

## Key Risk: LLM False Positives

"Gold price should NOT reach wheat/fuel." Mitigations:
- Prompt: "only genuine causal mechanisms, not vague relatedness"
- Type E isolation scenarios as quality gate
- If persistent: add few-shot examples of correct isolation
