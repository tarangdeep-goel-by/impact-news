# CIS Plan Review — Gemini 3.1 Pro

<details><summary>Thinking (3989 chars)</summary>

**Citizen Impact Score (CIS) Redesign: A Critical Review**

Alright, let's break down this proposed CIS redesign. As a senior ML/graph engineer, my initial thought is: we're dealing with a classic graph problem: PPR, by its nature, emphasizes centrality, which isn't always synonymous with user value in this context. The core issue is the probability soak in T-world and the dilution in the I-world, particularly at the leaf nodes. My assessment is as follows:

**Diagnosis Assessment:** The diagnosis is fundamentally sound. PPR excels at identifying hubs, the engine is functioning *correctly* from a graph-theoretic perspective. However, this perfectly working system is misaligned with the intended *citizen-impact* goals. The proposed post-hoc re-ranking is a pragmatic approach. Modifying the PPR walks (edge weighting, teleportation) is mathematically cleaner but more complex.

**Formula Review (CIS):**  The proposed formula, `CIS = probability * magnitude * world_boost * leaf_boost`, is a reasonable heuristic. It's essentially a clever way to re-weight the raw PPR scores with domain-specific knowledge. It counterbalances the hub bias in PPR with the magnitude factor, which incorporates a hub penalty. The World and Leaf boosts incorporate semantic metadata, which is valuable. The linear multiplier is the crux of the issue; it is simple, and therefore tunable, but non-linear relationships could be better.

**Default Values:** The default boost/penalty values (2.0/0.3/1.5/1.0) seem like a good starting point for a grid search. This helps to mitigate the risk of these defaults. I like the use of a grid search; the 10x range is aggressive but appropriate given the goal of re-prioritizing citizen impact. However, there's a risk of the 10x over-correcting, potentially pushing irrelevant I-world nodes above relevant T-world nodes.

**Risks & Edge Cases:** The "Category Penalty" (0.3) is my main concern. There’s a high risk of burying relevant, broad impacts when specific leaf nodes are missing from the graph. For instance, if a weather event affects "agriculture" but the graph lacks explicit edges to "wheat" or "rice," penalizing "agriculture" means the user may receive *no* insight on the agriculture sector. D-type scenario tests will break, and changing the tests to match the new code is a tautology risk; we have to validate against ground truth. Magnitude scaling if magnitude is highly variable.

**Alternative Approaches:** While post-hoc ranking is the simplest fix, I’d consider these alternatives for future iterations:

*   **Weighted PPR:** Modify the transition matrix, e.g., make T->I edges heavier, or make CONTAINS edges distribute weight differently. If the node is a category, reduce incoming edge weights.
*   **Two-List Approach:** Given the tension in mixing T-world and I-world in a single ranked list, consider separating the outputs into "Macro Effects" and "Citizen Impacts." The UI/API often needs this separation anyway. This avoids the need for a single, scalar score.

**Scope Assessment:** Deferring graph coverage fixes is a sensible decision. However, the tuning script (`tune_cis.py`) should *absolutely* be bundled with this work.

**Verdict:** The proposed CIS redesign is an *Approve with Changes* scenario. The proposed formula is a useful quick-fix, and the approach is reasonable, given the constraint of *no LLM*. Here are the changes:

*   **Category Penalty Safety Floor:** Introduce a safety floor for the category penalty. Ensure a meaningful representation of broad impacts, even if specific leaf nodes are missing.
*   **Ground Truth Validation:** Ensure test rewrites are rigorously validated against ground truth data, not just the new code.
*   **Future Iteration: Weighted PPR:** Strongly consider weighted PPR (modified transition matrix, like Node2Vec-style edge weighting) or two-list approach (separate macro and micro impact lists) for a future iteration. These offer mathematically cleaner solutions.





</details>

## Response

Here is a critical review of the proposed Citizen Impact Score (CIS) redesign, from the perspective of a senior ML/graph engineer.

### Diagnosis Assessment
**The diagnosis is spot on, but highlights a fundamental mismatch between algorithm and product goal.** 
PPR is mathematically designed to find structural centrality—it will *always* pool probability in high-degree hubs and nodes close to the restart triggers. Your product, however, defines value through **semantic specificity** (citizen-level leaf nodes). 

The 4 root causes you identified (T-world soak, Category accumulation, CONTAINS dilution, and Hub penalty isolation) perfectly explain why a purely structural algorithm is failing a semantic requirement. Post-hoc reranking is a pragmatic, fast-to-implement fix that avoids the complexity of altering the Markov transition matrix, though it does sacrifice the pure probabilistic interpretation of the final score.

### Formula Review
**The CIS formula is a classic, effective heuristic overlay, but it has a mathematical vulnerability.**
`CIS = probability × magnitude × world_boost × leaf_boost`

*   **The Good:** It cleanly separates structural graph metrics (`probability`, `magnitude`) from semantic business logic (`world_boost`, `leaf_boost`). Multiplying `probability` (which favors hubs) by `magnitude` (which penalizes hubs via `1/log2(out_degree+1)`) creates a naturally balanced base score before semantic boosting.
*   **The Vulnerability:** It relies on linear scalar multipliers. Because PPR probabilities follow a power-law distribution, a 3.0x maximum boost (2.0 world × 1.5 leaf) might be insufficient to rescue an L4 node that is 4 hops away, but simultaneously *over-boost* an irrelevant L4 node that happens to be 1 hop away from a trigger. 
*   **Alternative Consideration:** Instead of a flat `category_penalty`, consider a **dynamic penalty based on child coverage**. If a category node has no L4 children in the graph, penalizing it by 0.3 might bury the only signal you have for that impact. 

### Default Values
**The defaults create a massive 10x relative swing, which is aggressive but likely necessary.**
*   Max boost (I-world L4): `2.0 × 1.5 = 3.0`
*   Max penalty (T-world Category): `1.0 × 0.3 = 0.3`
*   Relative difference: `10x`

Given the evidence that T-world nodes currently hold up to 80% of the probability mass, a 10x swing is mathematically required to invert the ranking. The defaults are sensible starting points for your proposed grid search. 

*One tweak:* I recommend setting `leaf_boost_l3 = 1.2` (instead of 1.0). If L3 is a non-category specific node, it is still a highly valuable citizen impact, and keeping it at 1.0 leaves it too close to the T-world baseline.

### Risks & Edge Cases
1.  **The "Empty Folder" Erasure:** If an event impacts a category (e.g., `staple_grains`), but your graph is missing the edges to the L4 leaves (`retail_rice`, `retail_wheat`), applying a 0.3 penalty to `staple_grains` will drop it out of the top 20 entirely. The user will see *zero* food impacts. 
2.  **Test Tautology:** You noted that 3 of 4 D-type scenarios will break and need updating. The risk here is rewriting the tests to match the new algorithm's output rather than ground-truth reality. You must verify that `home_loan_emi > india_trade_deficit` is actually the *correct product behavior* before changing the test.
3.  **Magnitude Domination:** If the `magnitude` factor has a wider variance than `probability`, it could dominate the CIS. Ensure `magnitude` is bounded (e.g., [0, 1]) so the semantic multipliers behave predictably.

### Alternative Approaches
Before committing to post-hoc reranking, consider these alternatives:

1.  **Biased Random Walk (Weighted Adjacency Matrix):** Instead of fixing the score after the walk, fix the walk itself. Modify the transition probabilities so that `T -> I` edges have a higher transition weight than `T -> T` edges. If a walk is at a category node, weight the `CONTAINS` edges to children higher than outgoing causal edges. This keeps the math pure (probabilities still sum to 1) and naturally pushes mass to the leaves.
2.  **Two-Phase PPR (The "Blast Radius" approach):** 
    *   *Phase 1:* Run PPR on T-world only to find the macro blast radius.
    *   *Phase 2:* Use the top T-world nodes as the restart distribution for a second PPR run restricted *only* to I-world nodes.
3.  **UI/API Separation (The simplest fix):** Does the user actually want macro and micro events mixed in one list? Often, products are better served by returning two distinct lists: `Top Macro Drivers` (filtered to T-world) and `Direct Citizen Impacts` (filtered to I-world). This eliminates the need to mathematically balance them against each other.

### Scope Assessment
**Explicitly deferring graph coverage fixes is the right call.** 
If you add missing edges and change the scoring formula in the same PR, you will have no idea which change caused the NDCG improvement (or regression). Fix the lens (scoring) first, then fix the subject (the graph).

However, **bundling the `tune_cis.py` script into this scope is mandatory.** Do not merge the CIS formula with guessed defaults. The grid search must be part of the implementation PR to prove the NDCG actually crosses the 0.35 threshold.

### Verdict
**APPROVE WITH CHANGES**

The plan is highly pragmatic, well-reasoned, and respects system constraints. Proceed with implementation, but incorporate the following changes in priority order:

1.  **Add a "Childless Category" safeguard:** In `_compute_cis`, if `is_category` is true but the node has out-degree == 0 (no children), bypass the `category_penalty` and treat it as `leaf_boost_l3`. Do not penalize categories if they are the end of the line.
2.  **Adjust L3 Default:** Change `leaf_boost_l3` from `1.0` to `1.2` to ensure non-category L3s still beat T-world baselines.
3.  **Validate D-Type changes with Product/Domain experts:** Do not just flip the assertions to make the CI pass. Document *why* the new ranking is the correct ground truth.
4.  **Include `tune_cis.py` in the initial PR:** The grid search is a critical dependency for this feature's success, not a fast-follow.
