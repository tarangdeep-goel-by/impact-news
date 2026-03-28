"""Push back on Gemini's structural fix proposals with specific concerns.

Usage:
    python3 scripts/pushback_review.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.graph_builder import GraphGemini

TAXONOMY_MD = PROJECT_ROOT / "taxonomy" / "TAXONOMY.md"

PROMPT = """You are a senior taxonomy reviewer doing a second-pass review on proposed graph fixes. The first-pass reviewer (also you, in a prior session) proposed fixes for 20 structural breaks. We have 7 specific concerns about those proposals.

## Constitution
{constitution}

## Your Prior Proposals (Summary)

You proposed 2 new nodes (retail_inflation_cpi, aviation_turbine_fuel), 19 new edges, and 3 canary updates. We are pushing back on 7 specific items. For each, re-evaluate strictly against the constitution and either DEFEND your original proposal or REVISE it.

## Pushback Items

### Pushback 1: agricultural_crop_damage → retail_rice (Break 1)

**Your proposal:** Direct edge, AFFECTS w=0.8
**Our concern:** `global_food_grain_supply` (T3-L3) already exists in the graph. It has children: global_edible_oil_supply, global_food_grain_supply, global_sugar_supply. And `global_food_grain_supply` already connects to `wheat_flour` which connects to rice products.

The killed edge was `southwest_monsoon → global_food_grain_supply` (bypassing via crop yield). Shouldn't the fix be `agricultural_crop_damage → global_food_grain_supply` instead of `agricultural_crop_damage → retail_rice`?

Crop damage reduces supply → global_food_grain_supply captures that supply shock → existing edges propagate to rice/wheat.

Rule 21 check: Does crop_damage → retail_rice bypass global_food_grain_supply?

### Pushback 2: agricultural_crop_damage → mgnrega_wages (Break 16)

**Your proposal:** Direct edge, AFFECTS w=0.8
**Our concern:** The mechanism is: crop failure → farmers lose agricultural income → seek MGNREGA work → wages spike. "Loss of agricultural income" is the intermediary. The crop damage doesn't directly set MGNREGA wages — the unemployment/income loss from crop damage does.

However, "agricultural_income_loss" doesn't exist as a node. Per the taxonomy rule on missing intermediaries: should we create it, or is the direct edge acceptable because the intermediary is too granular?

Counter-argument: `farm_labor_wages` (I4-L4) exists. Crop damage → farm_labor_wages (already an edge) → but farm_labor_wages doesn't connect to mgnrega_wages either.

### Pushback 3: national_unemployment_rate → mgnrega_wages (Break 8)

**Your proposal:** Direct edge, AFFECTS w=0.8
**But in Break 7** you said: "national_unemployment_rate is an aggregate lagging indicator, not a causal driver." You recommended REMOVING the canary for unemployment→IT_jobs because aggregates don't cause specific outcomes.

**Inconsistency:** Why is unemployment→mgnrega_wages direct but unemployment→it_sector_jobs is not? Both are aggregate→specific. If the aggregate metric doesn't cause IT jobs, why does it cause MGNREGA wages?

### Pushback 4: indirect_taxes → biscuits_and_snacks (Break 20)

**Your proposal:** Direct edge, AFFECTS w=0.9
**Our concern:** GST rate changes affect ALL packaged foods equally — not just biscuits_and_snacks. If we only add this one edge, then GST→biscuits works but GST→instant_noodles doesn't. This violates the homogeneity principle.

Rule 18 homogeneity test: Does GST affect all children of `packaged_and_processed_foods` (I1-L2) with the same mechanism? If yes, target L2... but Rule 20 forbids I→I L2 targeting.

Options:
(a) Add edges to EVERY L3 sibling under packaged_and_processed_foods
(b) Target the L2 (violates Rule 20)
(c) Accept the single edge knowing it's incomplete
(d) Don't add the edge — the path gst_council→wpi→kirana_store_income is the right propagation channel

Which option is correct per the constitution?

### Pushback 5: retail_inflation_cpi — underconnection risk

**Your proposal:** New node under inflation_indices (T3-L3), alongside wpi.
**Our concern:** CPI is one of the most connected macro metrics in India. If we create it with only 3 edges (wpi→cpi, cpi→minimum_wage, cpi→consumer_confidence), it's immediately underconnected.

CPI should also connect to:
- monetary_policy_committee (RBI targets CPI, not WPI, for rate decisions since 2016)
- home_loan_emi (via interest rate mechanism)
- kirana_store_income (retail inflation directly affects retail margins)
- aggregate_consumer_confidence (already proposed)
- minimum_wage (already proposed)

Should we:
(a) Create CPI with the full edge set from day 1?
(b) Create CPI with minimal edges and expand later?
(c) Skip CPI and route via existing paths (wpi already reaches MPC and kirana)?

### Pushback 6: Canary removal (unemployment → IT jobs)

**Your proposal:** Remove the canary because unemployment is a lagging indicator.
**Our concern:** The causal chain IS real in India. When unemployment rises, companies freeze hiring, fresh engineering graduates can't find IT jobs. The issue is that `national_unemployment_rate` has only 1 outgoing edge (→skilled_emigration). It's underconnected, not causally invalid.

Should we instead ADD edges from national_unemployment_rate to make it a proper node, rather than remove the canary? E.g.:
- national_unemployment_rate → urban_unemployment_rate (aggregate→component)
- national_unemployment_rate → aggregate_consumer_confidence (unemployment→sentiment)

Or is the canary truly invalid?

### Pushback 7: Missing scenarios for new edges

**The constitution states (Rule on patches):**
> "Every patch needs a scenario. When adding a bridge to fix a gap, add a corresponding scenario to taxonomy/scenarios.yaml that validates the path."

None of the 19 proposed edges come with test scenarios. Should we add scenarios for each, or is the existing canary/scenario coverage sufficient?

## Instructions

For each of the 7 pushbacks:
1. State whether you DEFEND your original proposal or REVISE it
2. Provide the specific correction if revising
3. Cite the constitutional rule that supports your position

Then provide a REVISED COMPLETE SUMMARY with all corrections applied.
"""


def main():
    constitution = TAXONOMY_MD.read_text()
    prompt = PROMPT.format(constitution=constitution)

    print(f"Prompt length: {len(prompt)} chars")
    print("Calling Gemini 3.1 Pro Preview for pushback review...")

    gemini = GraphGemini()
    response = gemini.call(prompt, thinking_budget=32000, max_output_tokens=65000)

    out_path = PROJECT_ROOT / "taxonomy" / "eval_results" / "structural_fixes_pushback.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(response)
    print(f"\nResponse saved to {out_path}")
    print("\n" + response)


if __name__ == "__main__":
    main()
