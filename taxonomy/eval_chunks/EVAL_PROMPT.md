# Graph Evaluation Prompt

Use this prompt with any LLM. Attach ONE domain chunk file at a time (e.g., `energy.json`, `financial.json`).

---

## Prompt

```
You are an expert on Indian economics, governance, and daily life. You are evaluating a causal knowledge graph used to determine how news events impact people's daily lives.

The attached JSON contains one domain of the graph with:
- **nodes**: Things that exist (e.g., crude_oil, repo_rate, monsoon)
- **edges**: Causal relationships between them (from → to, with type and description)
- **cross-domain edges**: Marked with "cross" field showing the external category

Evaluate the graph on these criteria and provide a structured report:

### 1. MISSING CRITICAL EDGES (High Priority)
List causal relationships that SHOULD exist but are missing. For each:
- from: <node_id>
- to: <node_id>
- type: AFFECTS|PRODUCES|REGULATES|DISRUPTS|DEPENDS_ON|SUPPLIES
- description: Why this edge matters
- severity: P0 (system broken without it) / P1 (important) / P2 (nice to have)

Focus on edges that would break causal chains for an Indian user trying to understand "how does X affect my life?"

### 2. INCORRECT/MISLEADING EDGES
List any edges where:
- The causal direction is wrong (A doesn't actually cause B)
- The relationship type is wrong
- The description is factually incorrect
- The relationship is too indirect to be useful (should be 2+ edges instead)

### 3. MISSING NODES
Important concepts in this domain that have no node but should. For each:
- id: suggested_snake_case_id
- aliases: ["common name 1", "common name 2"]
- category: <domain>
- why: Brief justification

### 4. DUPLICATE/REDUNDANT NODES
Node pairs that represent the same concept and should be merged.

### 5. DESCRIPTION QUALITY
- How many edges have no description?
- Are existing descriptions accurate and specific?
- Flag any descriptions that are vague, wrong, or misleading.

### 6. CROSS-DOMAIN COVERAGE
- Are there enough edges connecting this domain to other domains?
- What critical cross-domain links are missing?

### 7. OVERALL SCORE
Rate 1-10 on:
- Completeness (are all important causal chains present?)
- Accuracy (are the relationships correct?)
- Granularity (right level of detail — not too coarse, not too fine?)
- India-specificity (does it capture India-specific dynamics?)

### OUTPUT FORMAT
Return your findings as structured YAML that can be directly used as patches:

```yaml
missing_edges:
  - from: node_a
    to: node_b
    type: AFFECTS
    description: "..."
    severity: P0

incorrect_edges:
  - from: node_a
    to: node_b
    issue: "Direction should be reversed"

missing_nodes:
  - id: suggested_id
    aliases: ["..."]
    category: "..."

scores:
  completeness: 7
  accuracy: 8
  granularity: 7
  india_specificity: 8
  overall: 7.5
```
```

---

## Evaluation Order (recommended)

Run these domains first — they're the backbone:

1. **energy.json** (142 nodes) — crude oil, electricity, coal, gas cascades
2. **financial.json** (279 nodes) — RBI, rates, markets, banking
3. **food_agriculture.json** (252 nodes) — monsoon, crops, food prices
4. **macro_geopolitics.json** (88 nodes) — cross-domain bridges, global factors

Then these for coverage:

5. **employment.json** (168 nodes) — IT, startups, sectors
6. **governance.json** (199 nodes) — water, municipal, disaster
7. **infrastructure.json** (162 nodes) — transport, utilities
8. **consumer_life.json** (394 nodes) — housing, health, education

---

## After Evaluation

The LLM's `missing_edges` YAML output can be directly appended to `taxonomy/edge_patches.yaml` under the `edges:` key. No format conversion needed.
