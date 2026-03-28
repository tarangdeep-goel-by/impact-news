"""Consult Gemini on the best scoring architecture for causal impact ranking.

Usage:
    python3 scripts/scoring_architecture_review.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.graph_builder import GraphGemini

PROMPT = """You are a graph algorithm and information retrieval expert advising on the scoring engine for a causal news impact system.

## What the System Does

We have a causal knowledge graph (769 nodes, 1541 edges) modeling how macro events in India affect citizens' daily lives. When a news event occurs (e.g., "RBI hikes repo rate"), we need to rank which citizen-level impacts are most affected (e.g., home_loan_emi > fixed_deposits > cab_fare).

The graph has two worlds:
- **T-world (Trigger)**: System entities — natural systems, institutions, markets, infrastructure, social forces (5 L1 categories)
- **I-world (Impact)**: Citizen-facing outcomes — food prices, housing, transport, employment, finance, health, education, safety, environment, digital, leisure (11 L1 categories)

Typical causal chains are 2-4 hops: T→T→T→I or T→I→I

Edge properties: type (AFFECTS/PRODUCES/SUPPLIES/DISRUPTS/etc.), weight (0-1), polarity (+1/-1), delay (IMMEDIATE to LONG_TERM)

## Current Architecture (PPR-based)

We use Personalized PageRank with:
- restart_prob = 0.20
- Multi-seed: trigger + CONTAINS ancestors with decay
- Edge weights row-normalized as transition probabilities
- Results ranked by CIS = PPR_probability × bottleneck_magnitude × world_boost × leaf_boost

## The Fundamental Problem

PPR models a **random walker choosing ONE path** at each node. But causal shocks propagate along **ALL paths simultaneously**. This creates:

1. **Fan-out penalty**: A trigger with 8 outgoing edges splits probability 8 ways. Each downstream node gets ~12.5% instead of the full signal. In reality, a monsoon failure causes ALL 8 effects at once.

2. **Hop decay**: restart_prob=0.20 means 20% probability leaks back to trigger per hop. After 3 hops (typical T→T→T→I chain), only ~51% of probability remains. 1-hop infrastructure targets always dominate over 2-3 hop citizen impacts.

3. **Results**: Canary smoke tests show infrastructure/intermediate T-world nodes ranking above citizen-facing I-world targets. E.g., for RBI trigger: india_forex_reserves (1-hop, T-world) ranks #1, while home_loan_emi (2-hop, I-world citizen impact) ranks #6.

## Current Performance

- 769 nodes, 1541 edges (all Gemini-reviewed, Rule 21 validated)
- Graph connectivity is solid — 1 weakly connected component
- Scenarios: 66/71 passing (5 structural gaps)
- Canaries: 15/25 passing
- NDCG@10: 0.34 across 16 real-world events
- The 10 failing canaries are ALL ranking issues (targets reached but ranked too low)

## What We've Tried

1. **Hub penalty in magnitude**: Removed (was double-counting PPR's inherent fan-out)
2. **Magnitude = min(edge_weight) along path**: Better than product, but rankings still dominated by PPR probability
3. **Weight re-rating via Gemini**: All 769 edges individually calibrated. Helped marginally.

## Constraints

- Graph structure (nodes + edges) is FIXED. We're only changing the scoring/ranking layer.
- Must work with NetworkX (Python, not a graph database)
- Must be fast enough for real-time news scoring (~100ms per trigger)
- Must produce a ranked list of citizen impacts with scores

## Options We're Considering

### Option A: Tune PPR
- Lower restart_prob to 0.10-0.15
- Change CIS formula to prob^0.5 × mag^0.5 (geometric mean)
- Add hop-count normalization

### Option B: Independent Cascade
- Each edge fires independently with probability = weight
- Run Monte Carlo simulation (1000 trials)
- Score = fraction of trials where node was activated
- No fan-out penalty — all paths fire simultaneously

### Option C: Weighted BFS / Influence Propagation
- Start with trigger influence = 1.0
- At each node, propagate influence × edge_weight to ALL neighbors simultaneously
- No probability splitting — influence duplicates across paths
- Apply decay per hop (e.g., 0.8 per hop) to prevent everything reaching 1.0
- Score = max influence received from any path

### Option D: Hybrid
- Use PPR for reachability/filtering (which nodes can be reached?)
- Use path-based scoring for ranking (bottleneck weight, hop count, world-crossing bonus)

### Option E: Something else entirely

## Questions

1. Given our graph structure (T-world → I-world, 2-4 hop chains, ~800 causal edges), which propagation model is theoretically best for "causal impact ranking"?

2. For the recommended model, provide:
   - The algorithm pseudocode
   - How to handle fan-out (all paths vs single path)
   - How to handle hop decay
   - How to rank results
   - Expected computational complexity

3. Would a simpler model (e.g., just BFS with weight product and a world-crossing boost) outperform PPR for this specific use case?

4. Is there a way to fix PPR specifically for causal propagation (e.g., modifying the transition matrix)?

5. What would you recommend as the simplest change that moves NDCG the most?

Provide a SPECIFIC recommendation with pseudocode, not just concepts. We need to implement this.
"""


def main():
    print(f"Prompt length: {len(PROMPT)} chars")
    print("Calling Gemini 3.1 Pro Preview...")

    gemini = GraphGemini()
    response = gemini.call(PROMPT, thinking_budget=32000, max_output_tokens=65000)

    out_path = PROJECT_ROOT / "taxonomy" / "eval_results" / "scoring_architecture_review.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(response)
    print(f"\nResponse saved to {out_path}")
    print("\n" + response)


if __name__ == "__main__":
    main()
