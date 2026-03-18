# Taxonomy Review — Gemini 3.1 Pro

## Turn 1 (User)

You are reviewing the constitution of a causal knowledge graph for a news impact analysis system focused on India. This graph traces how macro events (oil price hikes, monsoons, policy changes) cascad...[truncated]

## Turn 1 (Gemini)

<details><summary>Thinking (3997 chars)</summary>

**Taxonomy Document Review: Deep Dive & Analysis**

Okay, let's get into this taxonomy document. My focus is sharp: I'm dissecting this causal knowledge graph (Taxonomy v4.1) meticulously, keeping the specific areas for review top of mind – especially those seven prompts I was given. This model is all about how big events shape citizen outcomes in India, so the goal is to pinpoint every contradiction, gap, inconsistency, and possible improvement.

First, I went through the entire document to get the big picture. Rules 1-6 seem pretty solid: definitions are clear, the Trigger/Impact split is clean, and the level 1 trees with leaf tests are fine. Rule 7, with its lateral edge and explicit “No I→T feedback edges” stance, feels solid too. Rules 8-11 are fine. Rules 12-16 are well considered. Rule 17 feels appropriate. I'm noting the general India-first scoping and the metadata tagging. Rules 18-20, those are the new ones, I'm already eyeing them with a little suspicion. Also, I looked through the graph statistics, the example causal chains and the PPR algorithm, which looks pretty solid. So far, the document shows a good understanding of causal principles and a robust architecture.

Now, let's hit those prompts directly.

**Prompt 1: Contradictions between Targeting Rules**

This is where things get interesting. I see a definite **CONTRADICTION**. Rule 20, which says "NEVER TARGET L2" for I→I edges, directly conflicts with Rule 7, which states, "Portal edges can connect nodes at *any level*". Portal edges include I→I edges across trees, and Rule 19 says "L2->L2 laterals are fine when appropriate". This contradiction throws a wrench into the system, and it is a significant issue.

**Prompt 2: PPR Algorithm Consistency**

There’s some **INCONSISTENCY** here, or at least a potential one. The PPR Phase 3 CONTAINS propagation is *intended* to work in line with Rule 20, but it gets complicated because of the T→I bridge rule (18). Since Rule 20 prohibits all L2 targeting, PPR Phase 3 will never trigger an I→I cascade from an L2. However, it *will* target L2s *reached* via T→I bridges (allowed by Rule 18). So the intent is there, but the wording leads to mechanical issues.

**Prompt 3: Validity of Example Causal Chains**

Here, I see some issues.

*   *Chain 1:* The jump from `Brent Crude` to `Oil Marketing Policy` is fine because of the cross-world T→T edges allowed. However, using the name `Retail Tomato Price` violates Rule 1 - the node should be named for the *entity* (e.g., `retail_tomato`).
*   *Chain 2:* I see a similar issue here: `Respiratory Hospital Admissions` (feels more like a *metric*) – the entity should be more along the lines of `hospital_beds` (axis: occupancy) or `respiratory_health`, and likewise with `Inhaler Demand`.
*   *Chain 3:* Again, `Toll Plaza Wait Times` violates Rule 1, it should be `toll_plaza`. Also, `Gig Worker Earnings` can be borderline – the L1 table has `gig_worker_payouts` which is probably fine.

**Prompt 4: Missing Edge Type Governance**

The priority list in Rule 12b is *very* solid. However, I see several **GAPS**:

*   No explicit verb for *physical consumption* (`CONSUMES`) in this table. This is important: e.g. a `thermal_plant` CONSUMES `coal`.
*   Lack of a clear edge type for *financial flow* (e.g., `FUNDS`). A rule like "the causal subgraph contains the 10 causal edge types" may be technically correct, but the text is *unclear*. The text is clear on the priorities, however.
*   The absence of `IS_A` from graph stats, even though Rule 6 defines it.

**Prompt 5: Build Phase Contradiction**

I need to be polite here, because the user might have an older version in mind. *The provided text* is clear: the Build Phases table shows "T→I only" for bridge edges. So, **this is a non-issue based on the current document**. However, I have noticed some issues with the wording elsewhere that may cause confusion.

**Prompt 6: North Star Metrics Discrepancy**

Same issue as above – I'll gently correct

</details>

This is an exceptionally well-engineered taxonomy document. The integration of causal polarity, the 3-phase PPR scoring algorithm, and the strict Trigger/Impact locus test show a high level of maturity. 

However, as requested, a deep review reveals several structural clashes—primarily where newer, highly specific rules (like Rules 18 and 20) collide with older, general rules (like Rules 7 and 19). 

Here is the detailed review, categorized by your specific prompts and additional findings.

---

### 1. Do Rules 18 and 20 contradict each other or Rule 7?
**CONTRADICTION**

There is a direct, multi-point collision regarding what taxonomic levels can be targeted by lateral edges.

*   **Rule 20 (I→I Targeting)** explicitly states: *"NEVER TARGET L2. Impact L2 nodes are organizational groupings, not causal entities."*
*   **Rule 19 (Patch Protocol, Point 3)** contradicts this: *"L2→L2 laterals are fine when appropriate..."*
*   **Rule 7 (Lateral Edges)** contradicts Rule 20: *"Portal edges can connect nodes at **any level** — an L3 in one tree can link to an L2 in another."*

**Resolution:** You must decide if Impact L2s are causal entities or just folders. If they are just folders (as Rule 20 suggests), you must update Rule 7 and Rule 19 to explicitly forbid targeting I-world L2s. 

### 2. Is the PPR algorithm consistent with the rules?
**INCONSISTENCY / GAP**

The PPR Phase 3 (Downward CONTAINS Propagation) is mechanically sound, but its interaction with Rule 20 creates a logical inconsistency.

*   **The Issue:** PPR Phase 3 states: *"For each category node reached by PPR, propagate scores down through CONTAINS edges..."* 
*   **The Inconsistency:** If Rule 20 is strictly enforced ("NEVER TARGET L2" for I→I edges), then an I→I causal cascade will *never* hit an L2 node. Therefore, Phase 3 CONTAINS propagation will only ever execute for **T→I bridges** (where Rule 18 allows L2 targeting) or if an L3 propagates to an L4. 
*   **GAP:** The PPR section does not define what happens if a leaf node is reached directly by PPR, but its parent was *not* reached. Does the score propagate *upward* to siblings? (Phase 1 handles upward seeding for the *trigger*, but not for downstream impacts). 

### 3. Are the example causal chains valid under current rules?
**CONTRADICTION**

Two of your three example chains violate **Rule 1 (Entity Principle)**.

*   **Rule 1 states:** *"Nodes are entities (things that exist), not events or changes... `crude_oil_price_hike` is NOT [a node]."*
*   **Chain 1 Violation:** `[I1] Retail Tomato Price` is listed as a node. "Price" is an axis/property, not an entity. It should be `retail_tomato`.
*   **Chain 3 Violation:** `[I3] Toll Plaza Wait Times` is listed as a node. "Wait times" is a metric/state. The entity is `toll_plaza` (axis: congestion/wait time).
*   **Chain 2 Borderline:** `[I6] Respiratory Hospital Admissions` leans heavily toward being an event/metric rather than an entity. `hospital_beds` (axis: occupancy) or `respiratory_health` would be strictly Rule 1 compliant.

### 4. Are there missing rules for edge types?
**GAP / IMPROVEMENT**

Rule 12b's priority list is excellent, but it has two notable gaps:

*   **GAP (Multigraphs):** The rules do not state whether two nodes can have *multiple* lateral edges between them. For example, can `rbi` both `REGULATES` and `FUNDS` a specific banking entity? If the graph is a simple directed graph (not a multigraph), you must add a rule: *"Maximum one lateral edge between any two nodes. Use the highest-priority edge type from Rule 12b."*
*   **IMPROVEMENT (Missing Verbs):** You have `PRODUCES` and `SUPPLIES`, but no equivalent for consumption or depletion. If a `thermal_power_plant` uses `coal`, how is that modeled? `DEPENDS_ON` (Priority 5) works structurally, but `CONSUMES` is a very common physical relationship in supply chains (T3/T4) that might warrant being Priority 3.

### 5. Build phases table: "Feedback edges" vs Rule 7?
**INCONSISTENCY (in your prompt vs. the text)**

You asked: *"The build phases table still shows 'Bridge + Feedback edges (T→I and I→T)' in Phase 3, but Rule 7 says 'No I→T feedback edges' — is this a contradiction?"*

*   **Correction:** The text you provided for the review actually says: `Phase 3 | Bridge edges (T→I only) | Any lateral type | Full connected graph`. 
*   **Conclusion:** The document is perfectly consistent here. It seems you may have fixed this in the text but remembered the older version, or the prompt contained a slight misread. Rule 7 and the Phase 3 table are in perfect alignment.

### 6. North Star Metrics: 300-350 nodes vs 738 actual?
**INCONSISTENCY (in your prompt vs. the text)**

You asked: *"North Star Metrics says 300-350 total nodes but the graph already has 738 — is this outdated?"*

*   **Correction:** The North Star Metrics table in the provided text actually says: `Total nodes (incl. categories) | 700-850`. 
*   **Conclusion:** The document is already updated and perfectly aligns with your current graph stats (738 nodes). 

### 7. Other Contradictions, Gaps, and Inconsistencies

**A. The TCS Classification (INCONSISTENCY)**
*   The Stress Test table lists `tcs (corporation)` as **T3: Macroeconomic & Global Markets**. 
*   However, the definition of T3 is *"Aggregate economic variables, global commodity markets..."* A single corporation is not an aggregate. If TCS is treated as an institution, it should be T2. If it's treated as an employer experienced by a citizen, it should be I4 (Livelihood). 

**B. IS_A Edges are Missing in Action (GAP)**
*   Rule 6 explicitly defines `IS_A` edges for within-level specialization.
*   However, the "Current graph stats" at the bottom show: `Edge types: {'CONTAINS': 722, 'AFFECTS': 310...}`. There are **zero** `IS_A` edges in the graph. 
*   **Improvement:** If `IS_A` edges aren't being used, deprecate them. They complicate the PPR walk and CONTAINS propagation. A strict MECE tree using only `CONTAINS` is much easier to maintain.

**C. Hub Penalty Math (IMPROVEMENT)**
*   In the 3-Layer Scoring section, the Hub penalty is defined as: `1 / log2(out_degree + 1) for nodes with out_degree > 1`.
*   This is mathematically safe because of the `> 1` condition (preventing division by zero if out_degree was 0). However, if a node has an out_degree of 2, the penalty is `1 / log2(3) = 0.63`. If out_degree is 10, it's `1 / log2(11) = 0.28`. This is a very aggressive penalty. Ensure this doesn't prematurely kill legitimate macro-triggers (like `brent_crude`) that naturally have high out-degrees.

**D. Rule 18 vs Rule 12b on REGULATES (IMPROVEMENT - Praise)**
*   *Note of praise:* Often, rule sets contradict themselves on cross-world edges. But your Rule 18 explicitly bans cross-world `REGULATES/MANAGES`, and your Rule 12b table explicitly tags them as `(same-world only)`. This is airtight governance.

---

### Summary of Required Actions:
1. **Rewrite Rule 7 and Rule 19.3** to explicitly defer to Rule 20 regarding the ban on targeting L2 Impact nodes.
2. **Fix the Example Causal Chains** to remove "Price", "Wait Times", and "Admissions" to comply with Rule 1's Entity Principle.
3. **Clarify Multigraph status** in Rule 12 (can A and B have more than one edge?).
4. **Re-evaluate `tcs`** in the stress test table to ensure it matches L1 definitions.
5. **Decide the fate of `IS_A` edges** — either use them or remove them from Rule 6 to match the reality of your graph stats.

## Turn 2 (User)

Good analysis. Now focus specifically on what needs to change for the I→I lateral edge generation phase we're about to start.

We currently have:
- 738 nodes in 16 CONTAINS trees
- 291 T→T lateral edg...[truncated]

## Turn 2 (Gemini)

<details><summary>Thinking (3696 chars)</summary>

**Actionable Insights for I->I Edge Generation**

Okay, let's break this down. I've been tasked with generating specific, actionable advice regarding the new I->I (Impact-to-Impact) lateral edges in our India-focused news impact system, keeping in mind the existing rules and PPR engine. Here's my thought process and the concrete answers I'm formulating:

First, let's tackle the issue of missing L3s in the I-world L1s. Rule 20 currently defaults to targeting L3. If an L1 only has L2 directly linked to L4, that's a problem. Taxonomy depth parity suggests this is valid sometimes, so we can't always expect an L3. My solution? We absolutely *must* allow L4->L4 targeting in such instances. Furthermore, we should *mandate* it when no L3 exists. I'll update Rule 20 to explicitly say: "If an L2 directly contains L4 leaves without an intervening L3, target the specific L4 leaves." This clarifies and ensures we don't accidentally ignore direct impacts.

Next, we address the potential issue of L3 targeting vs. CONTAINS propagation to L4. The premise is that if we target an L3, Phase 3 propagates the score to *all* L4 children. However, what if the impact only affects *one* specific L4? This is a crucial area. The key is the "Homogeneity Test" from Rule 18/20. If an L3 is targeted, it should mean the causal effect is universal across *all* L4 children. If not, targeting the L3 is a bug, creating false paths. Therefore, we should rely on the Homogeneity Test (Rule 20d). If the effect is universal, target the L3. If only one or some L4s are affected, we *bypass* the L3 and target the specific L4(s) directly. This perfectly aligns with existing rule 20c. My key takeaway for the LLM prompt is to emphasize that L3 targeting is a *shortcut for universal L4 impact*. It keeps things aligned with the Homogeneity Principle.

Now, for edge type selection in the I->I context. We need specific guidance for the LLM on selecting edge types like `SUPPLIES`, `AFFECTS`, `PRODUCES`, etc. We need to create a decision tree, tailored to the citizen layer. Rule 12b has a priority list. So my approach is to formulate a decision tree. I'm thinking:
*   **PRODUCES:** Rare in I->I. Think literal creation. Maybe `rooftop_solar` -> `electricity`.
*   **SUPPLIES:** Think physical goods/labor moving. Example: `wholesale_market` -> `retail_tomato`.
*   **FUNDS:** Paying for things. Very common in I5 (Finance) -> other I-worlds.
*   **DISRUPTS:** Breaking/blocking. Common in I9 (Environment) -> I3 (Transport) or I6 (Health).
*   **DEPENDS_ON:** Structural requirement. `swiggy` -> `mobile_internet`.
*   **COMPETES_WITH:** Market share. Example: `metro` vs `ola`.
*   **AFFECTS:** The fallback, when others don't apply. Price/quality changes.

Finally, regarding weight assignment for I->I versus T->I edges: the question is, should I->I be weaker because they're secondary, or purely reflect causal strength? My conclusion is clear: Weight *must* purely reflect the *local causal strength* between the two nodes, whether it's T->I or I->I. The PPR algorithm uses path product (weight times hub penalty). Artificially lowering I->I weights creates a double-penalty, artificially impacting propagation down the line. Our existing algorithm already handles cascade decay via path math. Therefore, if A dictates B, the weight is 0.9-1.0. If A is a minor factor in B, the weight is 0.1-0.3. The math handles it.

I've reviewed this to ensure it's direct, actionable for prompt writing, and consistent with the existing constitution (v4.1). No contradictions exist. The "Homogeneity" principle and the math of the PPR algorithm all work perfectly. Let's move forward and get these lateral edges right!

</details>

Here is the concrete, actionable guidance for your I→I edge generation phase. Since you are using Gemini to generate these edges, these answers are formatted so you can directly adapt them into your LLM prompting instructions.

### 1. Missing L3s: What if an L1 only has L2→L4?
**Action:** You **must** target the L4 leaves directly. 

**Rationale:** Rule 20a strictly forbids targeting L2s in the Impact world. If an L2 skips L3 and goes straight to L4, the L4s are the highest valid causal entities in that branch. 
**LLM Prompt Instruction:** *"If the target taxonomy branch has no L3 nodes (i.e., L4 leaves are attached directly to an L2 category), you must target the specific L4 leaves. Never target the L2."*

### 2. L3 Targeting vs. CONTAINS Propagation to L4
**Action:** Targeting L3 is **only** correct if the effect is universally true for ALL its L4 children. If it is not, you must bypass the L3 and target the specific L4s.

**Rationale:** Because Phase 3 pushes scores down, an edge to an L3 is mathematically identical to drawing edges to *every single one* of its L4 children. 
*   **Correct L3 Target:** `retail_petrol` (I3) → `two_wheeler_running_cost` (I3-L3). This is correct because petrol prices affect *all* L4 children under it (scooters, motorcycles, mopeds) equally.
*   **Incorrect L3 Target:** `urban_flooding` (I9) → `public_transit` (I3-L3). This is a bug. Flooding severely disrupts `city_buses` (L4) but might not disrupt `underground_metro` (L4). 
**LLM Prompt Instruction:** *"Apply the Homogeneity Test: If the causal effect applies to ALL L4 children of an L3 equally, target the L3. If it only affects specific L4 children, you MUST target those specific L4s and leave the others alone."*

### 3. Edge Type Decision Tree for I→I Edges
**Action:** Give Gemini this exact decision tree. Since I-world is about the citizen's lived experience, the verbs have specific semantic flavors here compared to the T-world.

**LLM Prompt Instruction:** *"Evaluate edge types in this exact order. Pick the FIRST one that is true:"*
1.  **`DISRUPTS`**: Does Node A physically break, block, or halt Node B? *(Highly common from I9 Environment or I6 Health. e.g., `urban_flooding` DISRUPTS `daily_commute`; `dengue` DISRUPTS `livelihood_wages`)*
2.  **`FUNDS`**: Is Node A the money used to pay for Node B? *(Highly common from I5 Finance/I4 Livelihood. e.g., `personal_savings` FUNDS `medical_expenses`)*
3.  **`DEPENDS_ON`**: Is Node B a digital/service layer that literally cannot function without Node A? *(Common in I10 Digital. e.g., `upi_transactions` DEPENDS_ON `mobile_internet`)*
4.  **`COMPETES_WITH`**: Are A and B substitutes for the citizen's time or money? *(Must be unidirectional. e.g., `quick_commerce` COMPETES_WITH `local_kirana`)*
5.  **`PRODUCES`**: Does Node A literally generate Node B? *(Rare in I-world, but applies to self-sufficiency. e.g., `rooftop_solar` PRODUCES `household_electricity`)*
6.  **`SUPPLIES`**: Does Node A provide the physical input for Node B? *(e.g., `municipal_water` SUPPLIES `household_sanitation`)*
7.  **`AFFECTS`**: **(Fallback)** Does Node A just change the price, frequency, or quality of Node B? *(e.g., `retail_diesel` AFFECTS `freight_costs`)*

*(Note: `REGULATES`, `MANAGES`, and `EMPLOYS` are almost exclusively T-world or T→I verbs. Exclude them from the I→I prompt to prevent LLM hallucinations).*

### 4. Weight Assignment: Weaker for I→I?
**Action:** Weight must purely reflect the **local causal strength** between the two nodes. Do **not** artificially lower I→I weights.

**Rationale:** Your scoring engine uses a path product `∏(weight × hub_penalty)`. 
If a macro event (T) causes a local event (I1) with a weight of 0.8, and that local event (I1) *completely dictates* a secondary impact (I2), the I1→I2 edge should be 1.0. 
The algorithm will calculate the final cascade as `0.8 * 1.0 = 0.8`. 
If you artificially lower the I1→I2 weight to 0.5 "because it's a secondary cascade," the algorithm will calculate `0.8 * 0.5 = 0.4`. You will have double-penalized the cascade and killed the signal.

**LLM Prompt Instruction:** *"Assign weights (0.1 to 1.0) based ONLY on the isolated relationship between Node A and Node B. Assume Node A has already experienced a massive shock. How strongly does Node B react? 1.0 = B is completely dictated by A. 0.5 = A is one of several major factors. 0.2 = A is a minor contributing factor. Do not discount weights just because they are downstream."*

### Summary Checklist for your Gemini Prompt today:
*   [ ] Pass the Homogeneity Test definition (Rule 20d).
*   [ ] Explicitly ban targeting L2s (Rule 20a).
*   [ ] Explicitly allow targeting L4s if L3 is missing or if the effect is heterogeneous.
*   [ ] Provide the 7-step I→I verb decision tree.
*   [ ] Instruct it to score weights locally, not globally.
*   [ ] Remind it of Rule 1: Polarity (+1/-1) is about the *math* of the axes, not the sentiment of the verb. (e.g., `solar` DISRUPTS `grid_dependency` with polarity -1).

