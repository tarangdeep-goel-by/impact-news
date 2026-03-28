"""Consult Gemini on PPR ranking tuning strategy.

Usage:
    python3 scripts/ranking_tuning_review.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.graph_builder import GraphGemini

PROMPT = """You are a graph algorithm expert advising on a causal knowledge graph scoring engine for an Indian news impact system.

## Current Scoring Architecture

We use Personalized PageRank (PPR) with a 3-layer scoring system:

### Layer 1: PPR Probability
- Standard PPR with restart_prob=0.20
- Multi-seed: trigger node + ancestors (CONTAINS parents) with exponential decay
- Edge weights are row-normalized per node for transition probabilities

### Layer 2: Magnitude (path-based)
For each reached node, we find the "dominant path" (highest probability path from seed to node) and compute:
```
magnitude = product of (edge_weight × hub_penalty) along path
hub_penalty = 1/log2(out_degree + 1)  // per node along the path
```

### Layer 3: CIS (Citizen Impact Score) — final ranking
```
CIS = probability × magnitude × world_boost × leaf_boost
```
- world_boost: I-world nodes get a boost (citizen-facing)
- leaf_boost: L4 nodes boosted over L3/L2 category nodes
- Results sorted by CIS descending

## The Problem: Hub Penalty is Crushing Multi-Hop Citizen Impacts

### Evidence from 10 failing canary smoke tests:

**Example 1: southwest_monsoon (8 outgoing edges)**
Expected: retail_rice, retail_onion in top 10
Actual: top 10 is ALL 1-hop targets (traffic_congestion, stagnant_water, road_potholes)
- Hub penalty for monsoon: 1/log2(9) = 0.316
- Any 2-hop path magnitude: 0.316 × 0.316 × weights = ~0.05
- 1-hop path magnitude: 0.316 × weight = ~0.08
- 1-hop targets always dominate, even if citizen impact is lower

**Example 2: cyclonic_storm_systems (7 outgoing edges) → domestic_flight_ticket**
Expected: top 10. Actual: rank #22
Path: cyclone → commercial_airports → domestic_flight_ticket
Hub penalty: 1/log2(8) = 0.333 per hop → magnitude ~0.067
Meanwhile, 1-hop targets like structural_collapse rank #1 with magnitude 0.256

**Example 3: rbi → home_loan_emi**
Expected: top 5. Actual: rank #6
Path: rbi → monetary_policy_committee → home_loan_emi
RBI → india_forex_reserves (1-hop, MANAGES edge) ranks #1 with CIS=0.114
RBI → MPC → home_loan_emi (2-hop) gets CIS=0.019
The forex_reserves path is technically correct but irrelevant to citizens — citizens care about their EMI, not the central bank's reserves.

**Example 4: brent_crude → cab_aggregator_fare**
Expected: top 5. Actual: rank #20
Path: brent → retail_diesel → cab_aggregator_fare
Diesel has many outgoing edges → second hub penalty crushes the fare signal

### The Root Issue
PPR correctly distributes probability across paths. But the magnitude calculation DOUBLE-PENALIZES hubs:
1. PPR already dilutes probability across outgoing edges (proportional to weight)
2. Hub penalty in magnitude FURTHER reduces the signal for paths through hubs
3. Result: multi-hop paths through hub nodes (which are the most important connectors) get systematically suppressed
4. 1-hop infrastructure/intermediate targets dominate the ranking over 2-3 hop citizen-facing targets

## Additional Problem: Wrong Chains

We also have a structural issue: `agricultural_crop_damage → global_food_grain_supply → wheat_flour → retail_rice` is a bad chain. Indian retail rice prices are driven by DOMESTIC crop production, not "global food grain supply" (which is a T3 international commodity market node). The chain should be: crop_damage → domestic_food_supply → retail_rice. But no domestic supply node exists.

Similarly, there's no path from crop_damage to retail_onion — onion prices in India are entirely driven by domestic production (Maharashtra/Karnataka growing seasons), not global markets.

## Options We're Considering

### Option A: Soften hub penalty
Change from `1/log2(out_degree+1)` to something gentler:
- `1/log10(out_degree+1)`
- `1/sqrt(out_degree)` with a floor of 0.5
- Remove hub penalty entirely from magnitude (let PPR handle distribution)

### Option B: Remove magnitude from ranking entirely
Just rank by PPR probability. CIS = probability × world_boost × leaf_boost.
Magnitude only used for display, not ranking.

### Option C: Change magnitude calculation
Instead of product-along-path, use max-edge-weight or mean-edge-weight along path. This prevents multi-hop decay.

### Option D: Different CIS formula
Instead of prob × magnitude, use something like:
- prob^0.6 × magnitude^0.4 (reduce magnitude influence)
- prob + α×magnitude (additive instead of multiplicative)
- prob × (1 + magnitude) (magnitude as bonus, not multiplier)

### Option E: Hop-count boost
Add a term that BOOSTS shorter paths to citizen-facing (I-world) nodes, counteracting the natural decay.

## Questions for You

1. What is the theoretically correct approach for this type of causal propagation graph?
2. Is the hub penalty fundamentally wrong, or just miscalibrated?
3. Should magnitude factor into ranking at all, or should it be metadata only?
4. For the crop_damage → retail_rice chain: should we create a `domestic_food_supply` node, or should crop_damage have DIRECT edges to retail food items (which feels like a Rule 21 violation)?
5. What's the simplest change that would fix the most canaries without breaking the ones that already pass?

Provide a specific recommendation with the formula/code change, not just the concept.
"""


def main():
    print(f"Prompt length: {len(PROMPT)} chars")
    print("Calling Gemini 3.1 Pro Preview...")

    gemini = GraphGemini()
    response = gemini.call(PROMPT, thinking_budget=32000, max_output_tokens=65000)

    out_path = PROJECT_ROOT / "taxonomy" / "eval_results" / "ranking_tuning_review.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(response)
    print(f"\nResponse saved to {out_path}")
    print("\n" + response)


if __name__ == "__main__":
    main()
