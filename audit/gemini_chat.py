"""Multi-turn conversation with Gemini 3.1 Pro for research.

Usage:
    GEMINI_API_KEY=xxx python -m audit.gemini_chat <topic>

Topics:
    weights    — Research edge weight assignment strategies
"""

import json
import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

OUTPUT_DIR = Path("taxonomy/eval_results")


def send_message(client, chat, message: str, turn: int) -> str:
    """Send a message and return the response text."""
    print(f"\n{'='*60}")
    print(f"TURN {turn} — Sending ({len(message)} chars)...")
    print(f"{'='*60}")

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = chat.send_message(message)
            break
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e):
                wait = 30 * (attempt + 1)
                print(f"  Retry {attempt + 1}/{max_retries} — waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    else:
        print(f"  FAILED after {max_retries} retries")
        return ""

    answer = ""
    thinking = ""
    for part in response.candidates[0].content.parts:
        if part.thought:
            thinking += part.text + "\n"
        else:
            answer += part.text + "\n"

    usage = response.usage_metadata
    print(f"  Thinking: {usage.thoughts_token_count} tokens")
    print(f"  Output: {usage.candidates_token_count} tokens")
    print(f"  Total: {usage.total_token_count} tokens")

    return answer.strip(), thinking.strip()


def research_weights(client):
    """Multi-turn conversation about edge weight assignment."""

    # Load graph stats for context
    from graph.merge import TaxonomyMerger
    G = TaxonomyMerger().merge(apply_patches=True)

    # Gather edge samples
    from collections import Counter
    edge_types = Counter()
    sample_edges = []
    for s, d, a in G.edges(data=True):
        etype = a.get("type", "")
        edge_types[etype] += 1
        if etype in ("AFFECTS", "PRODUCES", "REGULATES") and len(sample_edges) < 60:
            desc = a.get("description", "")
            if desc:
                sample_edges.append({"from": s, "to": d, "type": etype, "description": desc})

    graph_context = f"""
Graph stats: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges
Edge type distribution: {dict(edge_types.most_common())}

Sample causal edges (with descriptions):
{json.dumps(sample_edges[:40], indent=2)}
"""

    chat = client.chats.create(
        model="gemini-3.1-pro-preview",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level="high",
                include_thoughts=True,
            ),
            temperature=0.3,
        ),
    )

    transcript = []

    # =========================================================================
    # TURN 1: Frame the problem
    # =========================================================================
    msg1 = f"""I'm building a NEWS IMPACT ANALYSIS system for India. The system has a causal knowledge graph where edges represent relationships like crude_oil --AFFECTS--> petrol_price --AFFECTS--> transport_costs --AFFECTS--> food_delivery_prices.

When a news headline fires (e.g., "Crude oil hits $100"), I do BFS from the trigger node and trace all downstream impacts. The problem: with 1,600+ nodes, a 4-hop BFS lights up the entire graph. Everything connects to everything in an economy.

I need EDGE WEIGHTS (0.0 to 1.0) to represent "impact strength" so I can prune low-signal paths. When traversing, I multiply weights along the path and drop paths below a threshold.

Here's my graph context:
{graph_context}

Before we discuss solutions, I need you to help me think through the FUNDAMENTAL QUESTIONS:

1. What exactly should the weight represent? Options I see:
   a) Probability that A affects B (but causal links are certain — crude oil ALWAYS affects petrol)
   b) Magnitude of impact (how MUCH does A change B?)
   c) Speed/directness of transmission (how quickly does A's change reach B?)
   d) Relevance to daily life (how much does a citizen CARE about this link?)
   e) Some combination?

2. Should weights be static (assigned once) or dynamic (change based on current conditions)?
   - Crude oil → petrol is always strong, but crude oil → solar panel adoption is stronger during an energy crisis

3. What's the difference between edge weight and edge polarity (direct/inverse correlation)?
   - Are these orthogonal properties or interrelated?

Think deeply about this. What does the academic literature say? What do real-world impact analysis systems use?"""

    a1, t1 = send_message(client, chat, msg1, 1)
    transcript.append({"turn": 1, "role": "user", "message": msg1[:200] + "...[truncated]"})
    transcript.append({"turn": 1, "role": "gemini", "thinking": t1, "answer": a1})
    print(f"\n--- GEMINI TURN 1 ---\n{a1[:500]}...\n")

    # =========================================================================
    # TURN 2: Dig into weight semantics based on response
    # =========================================================================
    msg2 = f"""Good. Now let's get concrete about the weight assignment problem.

I have ~1,800 causal edges. I CANNOT manually assign weights to each one — that's not scalable. I need a SYSTEMATIC approach.

Here are the approaches I can think of:

**Approach A: Category-based defaults**
Assign weights by edge type and node category:
- PRODUCES edges: 0.9 (strong direct causation)
- AFFECTS edges: 0.6 (default)
- REGULATES edges: 0.7 (policy has strong but delayed effect)
- DISRUPTS edges: 0.8 (disruptions are high-impact)
Then adjust based on domain knowledge.

**Approach B: LLM-assisted assignment**
Send edges in batches to Gemini with context and ask it to assign weights.
Pro: Captures nuance. Con: Consistency? Hallucination?

**Approach C: Structural heuristics**
- Edges between nodes in the same domain: higher weight (tighter coupling)
- Cross-domain edges: lower weight (more indirect)
- Edges with detailed descriptions: use description to infer weight
- Fan-out penalty: if a node has 20 outgoing edges, each gets lower weight

**Approach D: Empirical/data-driven**
- Use historical news data to calibrate (when crude oil moved 10%, how much did petrol move?)
- Pro: Ground truth. Con: Need data, complex.

**Approach E: Hybrid tiers**
Assign edges to tiers (HIGH=0.9, MEDIUM=0.6, LOW=0.3) based on simple rules, then let LLM refine within tiers.

Which approach (or combination) would you recommend for a solo developer? What are the failure modes of each? And critically — what GRANULARITY of weight matters? Is there a meaningful difference between 0.7 and 0.75, or should I just use 3-5 tiers?"""

    a2, t2 = send_message(client, chat, msg2, 2)
    transcript.append({"turn": 2, "role": "user", "message": msg2[:200] + "...[truncated]"})
    transcript.append({"turn": 2, "role": "gemini", "thinking": t2, "answer": a2})
    print(f"\n--- GEMINI TURN 2 ---\n{a2[:500]}...\n")

    # =========================================================================
    # TURN 3: Get into the actual weight schema
    # =========================================================================
    msg3 = """Now let's design the actual weight schema. I want you to propose:

1. **The exact properties each edge should have** (weight, polarity, delay, confidence — whatever you think is needed). For each property, give me:
   - Name
   - Type (float, enum, etc.)
   - Value range
   - What it means
   - Example values for 5 real edges from my graph

2. **The assignment algorithm** — step by step, how do I assign these properties to 1,800 edges? Be specific:
   - What can be rule-based (automated)?
   - What needs LLM assistance?
   - What needs human review?
   - What's the prompt for the LLM batches?

3. **The traversal algorithm** — given these properties, how exactly does BFS/Dijkstra use them?
   - How do I compute path score?
   - What's the pruning threshold?
   - How does polarity propagate? (positive × positive = positive, positive × negative = negative)
   - How do I handle cycles?

4. **Validation** — how do I know the weights are reasonable?
   - What test cases should I run?
   - How do I catch systematic bias (e.g., all weights too high)?

Be extremely concrete. I want to be able to implement this directly from your response."""

    a3, t3 = send_message(client, chat, msg3, 3)
    transcript.append({"turn": 3, "role": "user", "message": msg3[:200] + "...[truncated]"})
    transcript.append({"turn": 3, "role": "gemini", "thinking": t3, "answer": a3})
    print(f"\n--- GEMINI TURN 3 ---\n{a3[:500]}...\n")

    # =========================================================================
    # TURN 4: Stress test with real scenarios
    # =========================================================================
    msg4 = """Let me stress-test your proposal with real Indian news scenarios. For EACH scenario below, walk me through:
- Which node fires
- The traversal path (with weights at each hop)
- The cumulative score at each node
- Where pruning kicks in
- The final impact report the system would generate

**Scenario 1: "RBI hikes repo rate by 25 basis points"**
Expected impacts: home loan EMIs up, FD rates up, stock market dips, rupee strengthens, real estate slows

**Scenario 2: "Southwest monsoon 20% below normal"**
Expected impacts: kharif crop failure, food prices spike, rural demand drops, government may ban rice exports, water rationing in cities

**Scenario 3: "Crude oil crosses $100/barrel"**
Expected impacts: petrol/diesel up, transport costs up, airline fares up, inflation up, fiscal deficit widens, rupee weakens

**Scenario 4: "Major IT company lays off 10,000 employees"**
Expected impacts: Bangalore real estate dips, startup funding tightens, H1B visa concerns, consumer spending drops in tech hubs

For each scenario, tell me:
1. Does the weight schema capture the right paths?
2. Are there paths that SHOULD be captured but would be pruned too early?
3. Are there spurious paths that SHOULDN'T be captured but survive pruning?
4. What's missing from my graph that these scenarios expose?"""

    a4, t4 = send_message(client, chat, msg4, 4)
    transcript.append({"turn": 4, "role": "user", "message": msg4[:200] + "...[truncated]"})
    transcript.append({"turn": 4, "role": "gemini", "thinking": t4, "answer": a4})
    print(f"\n--- GEMINI TURN 4 ---\n{a4[:500]}...\n")

    # =========================================================================
    # TURN 5: Final implementation plan
    # =========================================================================
    msg5 = """Based on everything we've discussed, give me the FINAL IMPLEMENTATION PLAN.

I need:

1. **Data model changes** — exact YAML schema for edges with new properties. Show me what edge_patches.yaml should look like after migration.

2. **Migration script spec** — what the script does step by step:
   - How it assigns default weights based on rules
   - How it batches edges for LLM refinement
   - How it validates results

3. **Traversal engine spec** — pseudocode for the impact propagation algorithm:
   - Input: trigger_node, event_direction (up/down/neutral)
   - Output: list of (impacted_node, cumulative_score, polarity, path)
   - Include the IS_A elevator logic for taxonomy leaves

4. **Priority order** — what to implement first, second, third. What gives me 80% of the value with 20% of the effort?

5. **Risk assessment** — what could go wrong? Where might this design fail? What's the fallback?

Format this as an actionable implementation plan I can follow step by step. Include estimated effort for a solo developer (hours, not days — be realistic)."""

    a5, t5 = send_message(client, chat, msg5, 5)
    transcript.append({"turn": 5, "role": "user", "message": msg5[:200] + "...[truncated]"})
    transcript.append({"turn": 5, "role": "gemini", "thinking": t5, "answer": a5})
    print(f"\n--- GEMINI TURN 5 ---\n{a5[:500]}...\n")

    # =========================================================================
    # Save full transcript
    # =========================================================================
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "weight_research_chat.md"

    with open(out_path, "w") as f:
        f.write("# Edge Weight Assignment — Gemini Research Chat\n\n")
        f.write(f"Model: gemini-3.1-pro-preview | Thinking: high | Temperature: 0.3\n\n")

        for entry in transcript:
            turn = entry["turn"]
            role = entry["role"]
            if role == "user":
                f.write(f"---\n\n## Turn {turn} — User\n\n")
                # Write full message for user turns
                f.write(f"{entry['message']}\n\n")
            else:
                f.write(f"## Turn {turn} — Gemini\n\n")
                if entry.get("thinking"):
                    f.write(f"<details><summary>Thinking</summary>\n\n{entry['thinking']}\n\n</details>\n\n")
                f.write(f"{entry['answer']}\n\n")

    # Also save raw JSON for programmatic access
    raw_path = OUTPUT_DIR / "weight_research_chat.json"
    with open(raw_path, "w") as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)

    print(f"\nTranscript saved to {out_path}")
    print(f"Raw JSON saved to {raw_path}")


def research_markov(client):
    """Multi-turn conversation about Markov chain approach for impact scoring."""

    # Load graph stats for context
    from graph.merge import TaxonomyMerger
    from collections import Counter
    G = TaxonomyMerger().merge(apply_patches=True)

    edge_types = Counter()
    weight_dist = []
    sample_bridges = []
    sample_causal = []
    for s, d, a in G.edges(data=True):
        etype = a.get("type", "")
        edge_types[etype] += 1
        w = a.get("weight", 1.0)
        if etype not in ("CONTAINS", "IS_A"):
            weight_dist.append(w)
        if etype in ("AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS") and len(sample_causal) < 30:
            sample_causal.append({
                "from": s, "to": d, "type": etype,
                "weight": a.get("weight", 1.0),
                "polarity": a.get("polarity", 0),
                "delay": a.get("delay", "SHORT_TERM"),
                "description": a.get("description", "")[:100],
            })
        if "bridge" in a.get("description", "").lower() and len(sample_bridges) < 15:
            sample_bridges.append({"from": s, "to": d, "type": etype, "weight": w})

    # Fan-out stats
    fan_out = {}
    for node in G.nodes():
        causal_out = sum(1 for _, _, a in G.out_edges(node, data=True) if a.get("type") in ("AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES", "DEPENDS_ON", "FUNDS", "COMPETES_WITH", "EMPLOYS", "MANAGES"))
        if causal_out > 0:
            fan_out[node] = causal_out
    top_fan_out = sorted(fan_out.items(), key=lambda x: x[1], reverse=True)[:15]

    import statistics
    graph_context = f"""
Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges
Edge types: {dict(edge_types.most_common())}
Causal edge weights — mean: {statistics.mean(weight_dist):.3f}, median: {statistics.median(weight_dist):.3f}, stdev: {statistics.stdev(weight_dist):.3f}
Weight bands: <0.3: {sum(1 for w in weight_dist if w < 0.3)}, 0.3-0.6: {sum(1 for w in weight_dist if 0.3 <= w < 0.6)}, 0.6-0.9: {sum(1 for w in weight_dist if 0.6 <= w < 0.9)}, >=0.9: {sum(1 for w in weight_dist if w >= 0.9)}
Top fan-out nodes: {top_fan_out}

Architecture:
- Trigger world (5 L1s): system-level entities (crude_oil, rbi_repo_rate, monsoon)
- Impact world (11 L1s): citizen-level entities (home_loan_emi, grocery_bill, commute_time)
- Vertical: CONTAINS (L1→L2→L3→L4) + IS_A (within-level)
- Lateral: causal edges within world + bridge edges (Trigger→Impact, Impact→Trigger)
- Each edge has: weight (0-1), polarity (±1), delay (IMMEDIATE/SHORT_TERM/MEDIUM_TERM/LONG_TERM)

Current traversal: Modified Dijkstra (max-product paths), 0.05 threshold, max 6 hops.
Problem: weights clustered 0.6-0.9, single trigger reaches ~90% of graph.

Sample causal edges:
{json.dumps(sample_causal[:20], indent=2)}

Top fan-out nodes (causal edges only):
{json.dumps(top_fan_out, indent=2)}
"""

    chat = client.chats.create(
        model="gemini-3.1-pro-preview",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level="high",
                include_thoughts=True,
            ),
            temperature=0.3,
        ),
    )

    transcript = []

    # =========================================================================
    # TURN 1: Frame — is this a Markov chain? What does it buy us?
    # =========================================================================
    msg1 = f"""I'm building an impact news system for India. I have a causal knowledge graph that traces how macro events affect a citizen's daily life. Example chain: crude_oil → petrol_price → transport_costs → food_delivery_prices → grocery_bill.

I realized my graph is structurally close to a Markov chain. I want to explore whether formalizing it as one gives me better tools for three specific questions:

1. **PROBABILITY**: Given trigger X fires, what's the probability the shock reaches personal node Y?
2. **TIMING**: When does it hit — immediate, short-term, medium-term, long-term?
3. **MAGNITUDE**: How HIGH is the impact — a 2% price change or a 20% price change?

Current system: Modified Dijkstra with max-product paths, manual 0.3x hop decay. Weights are clustered 0.6-0.9, so everything connects to everything.

Here's my graph:
{graph_context}

Key structural features:
- TWO worlds: Trigger (system-level, 5 L1 categories) and Impact (citizen-level, 11 L1 categories)
- Bridges connect them (T→I and I→T feedback)
- Vertical hierarchy: L1→L2→L3→L4 via CONTAINS edges
- Each edge already has weight, polarity (±1), and delay labels

My hypothesis: If I normalize outgoing weights per node (row normalization), I get transition probabilities. Then:
- Absorbing Markov chains (user's personal nodes as absorbing states) → absorption probability = answer to Q1
- Semi-Markov chains (transition delays on edges) → answer to Q2
- Keep raw weights separately as causal strength → answer to Q3

But I'm not sure if this is the right formalization, or if there's something better. Specifically:
- Does Markov's memoryless property hurt me? (Causal chains ARE path-dependent — oil→petrol→transport is different from oil→plastics→packaging)
- Is my graph too sparse for matrix methods to work well?
- Are absorbing chains the right framework, or should I use PageRank, random walks with restart, or something else?

Think deeply. What does the literature say about applying Markov models to causal/economic impact graphs?"""

    a1, t1 = send_message(client, chat, msg1, 1)
    transcript.append({"turn": 1, "role": "user", "message": msg1[:200] + "...[truncated]"})
    transcript.append({"turn": 1, "role": "gemini", "thinking": t1, "answer": a1})
    print(f"\n--- GEMINI TURN 1 ---\n{a1[:500]}...\n")

    # =========================================================================
    # TURN 2: Dual-weight model — probability vs magnitude
    # =========================================================================
    msg2 = """Good. Now let's solve the CORE design problem: I need THREE outputs per trigger→personal-node pair:

1. **Probability** (0-1): Will this shock reach me?
2. **Term** (enum): When — IMMEDIATE / SHORT_TERM / MEDIUM_TERM / LONG_TERM?
3. **Impact magnitude** (0-1 or qualitative): How much will it affect me?

My proposed dual-weight architecture:

**Layer 1 — Transition Matrix P (for probability):**
- Take raw edge weights, normalize per node so outgoing edges sum to 1
- Compute absorption probabilities using fundamental matrix N = (I - Q)^(-1)
- User's personal nodes are absorbing states

**Layer 2 — Strength Matrix W (for magnitude):**
- Keep raw edge weights unchanged (0-1 causal strength)
- Multiply along the highest-probability path to get path_strength
- This captures "how much of the shock transmits" vs "which way does it go"

**Layer 3 — Delay aggregation (for timing):**
- Each edge has delay label (IMMEDIATE/SHORT_TERM/MEDIUM_TERM/LONG_TERM)
- Along the highest-probability path, take the MAX delay (slowest link determines timing)
- OR: use semi-Markov expected holding times for a more rigorous answer

**Combined score:**
```
impact = absorption_probability × path_strength × polarity_product
timing = max(delay along highest-prob path)
```

Questions for you:
1. Is this dual-weight architecture sound? Am I losing information by separating probability from magnitude?
2. How exactly should I normalize? Standard row normalization, or should I weight by edge type (CONTAINS vs AFFECTS vs bridge)?
3. Should CONTAINS edges (hierarchy) be part of the Markov chain, or should I "flatten" the graph first and only include causal edges?
4. The absorbing chain framework assumes the walk WILL eventually be absorbed. But in my graph, cycles exist (feedback loops). How do I handle this?
5. Is there a better way to compute magnitude than multiplying raw weights along a path? That still has the "everything is 0.8" problem."""

    a2, t2 = send_message(client, chat, msg2, 2)
    transcript.append({"turn": 2, "role": "user", "message": msg2[:200] + "...[truncated]"})
    transcript.append({"turn": 2, "role": "gemini", "thinking": t2, "answer": a2})
    print(f"\n--- GEMINI TURN 2 ---\n{a2[:500]}...\n")

    # =========================================================================
    # TURN 3: Implementation — matrix construction and computation
    # =========================================================================
    msg3 = """Now let's get into the EXACT implementation. I'm using Python with NetworkX and NumPy.

Current traversal code uses modified Dijkstra with max-product paths. I want to replace it.

Give me the CONCRETE implementation plan:

**1. Graph preprocessing:**
- Which edges go into the transition matrix? (CONTAINS? IS_A? Causal? Bridges? All?)
- How do I handle the elevator pattern? (Trigger leaf → walk up CONTAINS → find causal entry point)
- How do I handle bidirectional edges? (A→B and B→A with different weights)

**2. Matrix construction:**
- Exact normalization procedure (handling nodes with 0 outgoing, nodes with only CONTAINS out-edges)
- How to partition nodes into transient (T) and absorbing (A) states
- The user provides ~15-20 personal nodes. These become absorbing states. Everything else is transient.
- Matrix dimensions: ~800 nodes. Is N = (I-Q)^(-1) tractable? Memory? Time?

**3. Computing the three outputs:**
For a trigger event (e.g., "crude oil price increases"):
- Step A: Identify trigger node(s) in the graph
- Step B: Compute absorption probabilities to each personal node
- Step C: Find the dominant path for timing/delay
- Step D: Compute magnitude along that path
- Step E: Apply polarity chain

**4. Handling the "everything affects everything" problem:**
- With normalized weights, does a high fan-out node (20 outgoing edges) naturally dilute?
- What if fan-out varies wildly? (Some nodes have 2 edges, some have 20)
- Do I need a restart probability (like PageRank) as an additional dampening factor?

**5. Performance:**
- Pre-compute N = (I-Q)^(-1) once at startup? Or per-query?
- What if the user changes their personal nodes (re-onboarding)? Recompute N?
- Sparse matrix operations — what NumPy/SciPy tools?

Be extremely specific. Give me pseudocode I can translate directly into Python."""

    a3, t3 = send_message(client, chat, msg3, 3)
    transcript.append({"turn": 3, "role": "user", "message": msg3[:200] + "...[truncated]"})
    transcript.append({"turn": 3, "role": "gemini", "thinking": t3, "answer": a3})
    print(f"\n--- GEMINI TURN 3 ---\n{a3[:500]}...\n")

    # =========================================================================
    # TURN 4: Stress test with Indian news scenarios
    # =========================================================================
    msg4 = """Stress test the Markov approach with real Indian scenarios. For EACH scenario:

1. Walk through the transition matrix computation
2. Show absorption probabilities for a sample user profile:
   - Personal nodes: home_loan_emi, grocery_bill, commute_time, it_sector_salary, school_fees, electricity_bill, mutual_fund_returns
3. Show the timing derivation
4. Show the magnitude computation
5. Compare the output quality vs the current Dijkstra approach

**Scenario A: "RBI hikes repo rate by 50 basis points"**
- Expected: HIGH probability to home_loan_emi (direct), MEDIUM to mutual_fund_returns, LOW to grocery_bill
- Expected timing: home_loan_emi = IMMEDIATE, mutual_fund_returns = SHORT_TERM

**Scenario B: "Crude oil crosses $120/barrel"**
- Expected: HIGH to commute_time cost, MEDIUM to grocery_bill (transport costs), LOW to school_fees
- Expected timing: commute = SHORT_TERM, grocery = MEDIUM_TERM

**Scenario C: "Major drought — monsoon 30% deficit"**
- Expected: HIGH to grocery_bill, MEDIUM to electricity_bill (hydropower), LOW to home_loan_emi
- Expected timing: grocery = MEDIUM_TERM (crops take time)

**Scenario D: "AI automation wave — 100k tech jobs displaced"**
- Expected: HIGH to it_sector_salary, MEDIUM to home_loan_emi (stress), LOW to school_fees
- Expected timing: salary = SHORT_TERM, home_loan = MEDIUM_TERM

For each: does the Markov model produce the intuitively correct ranking? Where does it fail? What adjustments are needed?

Also: does the Markov approach NATURALLY solve the "everything affects everything" problem that the current Dijkstra has, or do we still need additional dampening?"""

    a4, t4 = send_message(client, chat, msg4, 4)
    transcript.append({"turn": 4, "role": "user", "message": msg4[:200] + "...[truncated]"})
    transcript.append({"turn": 4, "role": "gemini", "thinking": t4, "answer": a4})
    print(f"\n--- GEMINI TURN 4 ---\n{a4[:500]}...\n")

    # =========================================================================
    # TURN 5: Final architecture — what exactly changes, what stays
    # =========================================================================
    msg5 = """Final turn. Give me the COMPLETE architecture recommendation.

Current codebase:
- graph/graph.py — loads YAML into NetworkX DiGraph
- graph/traverse.py — Dijkstra with max-product, scoped elevator, upward aggregation, CONTAINS propagation
- pipeline/matcher.py — tag extraction (Gemini) → FAISS match → impact scoring → user relevance
- user/inference.py — onboarding answers → personal graph nodes
- Edge properties: weight (0-1), polarity (±1), delay (enum), type (12 types)

Tell me EXACTLY:

1. **What new code to write:**
   - New module? New class? What methods?
   - Transition matrix construction
   - Absorption probability computation
   - Path reconstruction for timing/polarity
   - Magnitude computation

2. **What existing code changes:**
   - graph.py — what changes at load time?
   - traverse.py — replace Dijkstra? Keep as fallback?
   - matcher.py — how does scoring change?

3. **What stays the same:**
   - YAML format? Edge properties?
   - Embedding matching?
   - User profiling?

4. **Migration path:**
   - Can I run both (Dijkstra and Markov) in parallel to compare?
   - What's the minimum viable Markov implementation to test the hypothesis?
   - Should I do weight recalibration BEFORE or AFTER switching to Markov? (My hypothesis: Markov normalization makes recalibration unnecessary)

5. **What this does NOT solve:**
   - What limitations remain even with Markov?
   - When would I need to go beyond Markov (e.g., Bayesian networks, structural causal models)?

Give me an actionable plan ordered by impact/effort ratio. I want to prototype the core in one session."""

    a5, t5 = send_message(client, chat, msg5, 5)
    transcript.append({"turn": 5, "role": "user", "message": msg5[:200] + "...[truncated]"})
    transcript.append({"turn": 5, "role": "gemini", "thinking": t5, "answer": a5})
    print(f"\n--- GEMINI TURN 5 ---\n{a5[:500]}...\n")

    # =========================================================================
    # Save full transcript
    # =========================================================================
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "markov_research_chat.md"

    with open(out_path, "w") as f:
        f.write("# Markov Chain Impact Scoring — Gemini Research Chat\n\n")
        f.write(f"Model: gemini-3.1-pro-preview | Thinking: high | Temperature: 0.3\n\n")

        for entry in transcript:
            turn = entry["turn"]
            role = entry["role"]
            if role == "user":
                f.write(f"---\n\n## Turn {turn} — User\n\n")
                f.write(f"{entry['message']}\n\n")
            else:
                f.write(f"## Turn {turn} — Gemini\n\n")
                if entry.get("thinking"):
                    f.write(f"<details><summary>Thinking</summary>\n\n{entry['thinking']}\n\n</details>\n\n")
                f.write(f"{entry['answer']}\n\n")

    raw_path = OUTPUT_DIR / "markov_research_chat.json"
    with open(raw_path, "w") as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)

    print(f"\nTranscript saved to {out_path}")
    print(f"Raw JSON saved to {raw_path}")


def research_graph_structure(client):
    """Multi-turn conversation to revalidate graph structure — I→I edges, feedback, bridge design."""

    from graph.merge import TaxonomyMerger
    from collections import Counter, defaultdict
    import networkx as nx

    G = TaxonomyMerger().merge()

    # Gather comprehensive graph stats
    edge_types = Counter()
    direction_counts = defaultdict(int)
    contains_tree = nx.DiGraph()
    for s, d, a in G.edges(data=True):
        etype = a.get("type", "")
        edge_types[etype] += 1
        if etype == "CONTAINS":
            contains_tree.add_edge(s, d)
        sc = G.nodes[s].get("category", "?")
        dc = G.nodes[d].get("category", "?")
        sw = "T" if sc.startswith("T") else ("I" if sc.startswith("I") else "?")
        dw = "T" if dc.startswith("T") else ("I" if dc.startswith("I") else "?")
        direction_counts[f"{sw}→{dw} ({etype})"] += 1

    # Depth analysis
    all_children = set(d for _, d in contains_tree.edges())
    all_parents = set(s for s, _ in contains_tree.edges())
    roots = all_parents - all_children

    depth = {}
    def compute_depth(node, d=0):
        depth[node] = d
        for child in contains_tree.successors(node):
            compute_depth(child, d + 1)
    for r in roots:
        compute_depth(r)
    depth_counts = Counter(depth.values())

    # Category breakdown
    cat_counts = Counter()
    for n, a in G.nodes(data=True):
        cat_counts[a.get("category", "NONE")] += 1

    # Leaf analysis
    leaves = [n for n in G.nodes() if not any(G.edges[n, s].get("type") == "CONTAINS" for s in G.successors(n))]
    leaves_no_lateral = [n for n in leaves if not any(
        G.edges[n, s].get("type") != "CONTAINS" for s in G.successors(n)
    ) and not any(
        G.edges[p, n].get("type") != "CONTAINS" for p in G.predecessors(n)
    )]

    # Failing scenario details
    import yaml
    from pathlib import Path
    scenarios = yaml.safe_load(Path("taxonomy/scenarios.yaml").read_text())

    failing_details = []
    for s in scenarios.get("scenarios", []):
        trigger = s.get("trigger_node", "")
        target = s.get("target_node", "")
        if trigger not in G.nodes or target not in G.nodes:
            continue
        tc = G.nodes[trigger].get("category", "?")
        dc = G.nodes[target].get("category", "?")
        try:
            nx.shortest_path(G, trigger, target)
            has_path = True
        except nx.NetworkXNoPath:
            has_path = False
        if not has_path and s.get("expected") == "REACHABLE":
            failing_details.append({
                "id": s["id"],
                "trigger": f"{trigger} ({tc})",
                "target": f"{target} ({dc})",
                "description": s.get("description", ""),
                "cross_world": tc[0] != dc[0],
                "cross_l1": tc != dc,
            })

    # Sample edges per type for context
    sample_edges = defaultdict(list)
    for s, d, a in G.edges(data=True):
        etype = a.get("type", "")
        if len(sample_edges[etype]) < 5 and etype != "CONTAINS":
            sample_edges[etype].append({
                "from": s, "to": d,
                "weight": a.get("weight", 1.0),
                "polarity": a.get("polarity", 0),
                "delay": a.get("delay", "?"),
                "desc": (a.get("description", "") or "")[:80],
            })

    graph_context = f"""
=== GRAPH OVERVIEW ===
Nodes: {G.number_of_nodes()} | Edges: {G.number_of_edges()} | Density: {nx.density(G):.6f}
Weakly connected components: {len(list(nx.weakly_connected_components(G)))}

=== NODE DEPTH ===
{json.dumps(dict(sorted(depth_counts.items())), indent=2)}
(Depth 0 = L1 roots, Depth 3 = L4 leaves)
L1 roots: {len(roots)} | Total leaves: {len(leaves)} | Leaves with no lateral edges: {len(leaves_no_lateral)}

=== NODES BY CATEGORY ===
{json.dumps(dict(sorted(cat_counts.items())), indent=2)}

=== EDGE TYPE COUNTS ===
{json.dumps(dict(edge_types.most_common()), indent=2)}

=== EDGE DIRECTION × TYPE ===
{json.dumps(dict(sorted(direction_counts.items())), indent=2)}

KEY OBSERVATION: There are ZERO I→I lateral edges and ZERO I→T feedback edges.
All lateral flow is T→T (within triggers) or T→I (bridges). Impact world is a passive receiver.

=== FAILING SCENARIOS (NO PATH EXISTS) ===
{json.dumps(failing_details, indent=2)}

=== SAMPLE EDGES BY TYPE ===
{json.dumps(dict(sample_edges), indent=2)}
"""

    chat = client.chats.create(
        model="gemini-3.1-pro-preview",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level="high",
                include_thoughts=True,
            ),
            temperature=0.3,
        ),
    )

    transcript = []

    # =========================================================================
    # TURN 1: Present the graph and ask for structural critique
    # =========================================================================
    msg1 = f"""I'm building a causal knowledge graph for a news impact system in India. The system traces how macro events (oil price hike, RBI rate change, monsoon failure) causally cascade down to affect a citizen's daily life (EMI, grocery bill, commute cost).

The graph has TWO WORLDS:
- **Trigger world** (5 L1 categories, ~230 nodes): System-level forces — natural disasters, government/institutional, macro-economic, infrastructure, social movements
- **Impact world** (11 L1 categories, ~510 nodes): Citizen-level consequences — food, housing, transport, livelihood, finance, health, education, safety, environment, digital, leisure

Scoring engine: Personalized PageRank from a trigger node. PPR probability = "will this reach me?", hub-penalized path product = "how hard will it hit?", delay sum = "when?"

Here is the full graph structure:
{graph_context}

Please analyze this graph structure critically. Specifically:
1. Is the two-world (Trigger/Impact) separation architecturally sound for a causal impact graph?
2. What are the structural weaknesses you see?
3. Is it correct that 237 of 450 leaf nodes have zero lateral edges — are they dead weight?
4. The Impact world has NO lateral edges (I→I) and NO feedback to Triggers (I→T). What are the consequences?
5. Compare this to how causal graphs are structured in economics, epidemiology, or supply chain analysis."""

    a1, t1 = send_message(client, chat, msg1, 1)
    transcript.append({"turn": 1, "role": "user", "message": msg1[:300] + "...[truncated]"})
    transcript.append({"turn": 1, "role": "gemini", "thinking": t1, "answer": a1})
    print(f"\n--- GEMINI TURN 1 ---\n{a1[:800]}...\n")

    # =========================================================================
    # TURN 2: The I→I edge question
    # =========================================================================
    msg2 = """Now let's focus on the core design question: should Impact nodes connect to each other laterally?

We previously had I→I edges and REMOVED them because:
- Gemini-generated edges had polarity inconsistency (same relationship modeled as +1 and -1)
- AFFECTS was overused (>70% of edges were just AFFECTS)
- Descriptions were thin and generic
- Quality was too low to trust for scoring

Now 11 of 58 test scenarios fail because they need I→I paths. The failing scenarios are real causal chains that exist in citizens' lives:
- ambient_aqi → hospital_beds (pollution → hospitalizations)
- outdoor_heat → informal_and_daily_wage (heat → outdoor labor productivity)
- it_sector_jobs → credit_card_dues (job loss → can't pay credit card)
- retail_tomato → savings_account_balance (food inflation → savings erosion)
- smartphone_device → upi_transaction_success (device → payment success)
- mgnrega_wages → kirana_store_income (rural wages → rural retail spending)

Three options on the table:

**Option A: Keep Impact passive, add more bridges**
Add trigger-side nodes that bridge directly to both endpoints. E.g., for "IT layoffs → credit card stress", add a trigger node "tech_sector_downturn" that bridges to BOTH it_sector_jobs AND credit_card_dues.
- Pro: Simple, no cycles possible in Impact
- Con: Loses the causal chain (magnitude/timing scoring needs the intermediate hop). Semantically dishonest — the trigger doesn't directly cause credit card stress.

**Option B: Add I→I lateral edges back (hand-curated)**
Model real cross-domain citizen impacts: food→finance, health→livelihood, environment→health, etc.
- Pro: Captures real cascades. PPR handles cycles. Better scoring fidelity.
- Con: Complexity. How many edges? At what hierarchy level?

**Option C: Hybrid — I→I only at L2 level**
Only add coarse I→I at L2→L2 boundaries, let CONTAINS propagate downward.
- Pro: Manageable number of edges (~50-100). Captures macro flows.
- Con: May be too coarse for precise scoring.

Which option is architecturally correct? Argue from first principles of causal graph design."""

    a2, t2 = send_message(client, chat, msg2, 2)
    transcript.append({"turn": 2, "role": "user", "message": msg2[:300] + "...[truncated]"})
    transcript.append({"turn": 2, "role": "gemini", "thinking": t2, "answer": a2})
    print(f"\n--- GEMINI TURN 2 ---\n{a2[:800]}...\n")

    # =========================================================================
    # TURN 3: I→T feedback and cycles
    # =========================================================================
    msg3 = """Now let's address feedback loops: should Impact nodes connect BACK to Trigger nodes?

Real-world examples of I→T feedback:
- High unemployment (I4) → social unrest → policy change (T2) → new employment program
- Food inflation (I1) → consumer sentiment drops (T5) → spending behavior changes
- Health crisis (I6) → government emergency response (T2) → hospital funding
- Housing bubble (I2) → RBI tightens lending (T2) → interest rate hike

These are REAL feedback loops in the Indian economy. But they create CYCLES in the graph.

Current state: Our DAG validation check (validate-dag) already found a cycle in the Trigger world:
  municipal_water_grid → sewage_drainage_network → urban_population_density → municipal_water_grid

Our scoring engine (Personalized PageRank) handles cycles naturally — PPR converges via the restart probability. So cycles aren't a technical problem for scoring.

But are they a MODELING problem?

Arguments AGAINST I→T feedback:
1. Feedback loops are SLOW (months/years). For a news alerting system, by the time feedback materializes, there's a new trigger.
2. Risk of "everything connects to everything" — exactly the problem we solved by switching from Dijkstra to PPR.
3. Makes the graph harder to reason about and debug.

Arguments FOR I→T feedback:
1. Without feedback, the graph is a DAG (trigger → impact) which is an incomplete model of reality.
2. Some feedback is fast enough to matter: health crisis → emergency policy → hospital capacity.
3. PPR already handles this correctly — the restart probability naturally dampens long cycles.

What does causal inference literature say about feedback loops in causal graphs? Are they modeling errors (violating DAG assumptions) or necessary features? What would you recommend for this specific use case?"""

    a3, t3 = send_message(client, chat, msg3, 3)
    transcript.append({"turn": 3, "role": "user", "message": msg3[:300] + "...[truncated]"})
    transcript.append({"turn": 3, "role": "gemini", "thinking": t3, "answer": a3})
    print(f"\n--- GEMINI TURN 3 ---\n{a3[:800]}...\n")

    # =========================================================================
    # TURN 4: Bridge architecture — depth targeting
    # =========================================================================
    msg4 = """Now let's talk about bridge architecture. Currently:

- 303 T→I bridge edges
- Bridges land mostly on Impact L2 and L3 nodes
- CONTAINS edges (L2→L3→L4) are supposed to propagate the signal downward
- But 88 port-tagged L4 nodes have NO bridge landing on them or their ancestors
- 5 T→I "REACHABLE" scenarios fail because the bridge doesn't reach deep enough

Examples of failing T→I paths:
- energy_gold_to_loan: international_gold_prices (T3) → gold_loan_interest (I5) — bridge lands on precious_metals but doesn't reach gold_loan_interest
- energy_natgas_to_auto: global_natural_gas (T3) → auto_rickshaw_fare (I3) — no bridge connects gas to auto transport
- energy_coal_to_tariff: international_coal_prices (T3) → electricity_tariff (I2) — bridge exists to household_energy but doesn't reach tariff level

The hierarchy for these:
- gold_loan_interest: i5 → borrowing_and_credit → secured_loans → gold_loan_interest (L4)
- auto_rickshaw_fare: i3 → urban_commute → ride_hailing → auto_rickshaw_fare (L4)
- electricity_tariff: i2 → household_energy → grid_electricity → electricity_tariff (L4)

Questions:
1. Should bridges target L2 (coarse, fewer bridges needed) or L3/L4 (precise, many more bridges)?
2. How should CONTAINS edges interact with PPR? Currently they're treated as causal edges — is this right?
3. Is there a better architecture than CONTAINS for downward propagation? E.g., should we have a "propagation" step that expands L2 hits to their L3/L4 children?
4. What's the right NUMBER of bridges? We have 303. Is that too few for 510 Impact nodes?"""

    a4, t4 = send_message(client, chat, msg4, 4)
    transcript.append({"turn": 4, "role": "user", "message": msg4[:300] + "...[truncated]"})
    transcript.append({"turn": 4, "role": "gemini", "thinking": t4, "answer": a4})
    print(f"\n--- GEMINI TURN 4 ---\n{a4[:800]}...\n")

    # =========================================================================
    # TURN 5: Final recommendation — concrete plan
    # =========================================================================
    msg5 = """Based on everything we've discussed, give me your FINAL STRUCTURAL RECOMMENDATION for the graph.

I need:

1. **I→I edges: Yes or No?** If yes:
   - At what hierarchy level (L2, L3, L4)?
   - How many edges approximately?
   - Which cross-L1 pairs are most important? (11 Impact L1s = 55 possible L1×L1 pairs)
   - Should they be directional or bidirectional?
   - How to ensure quality (what properties must each edge have)?

2. **I→T feedback: Yes or No?** If yes:
   - At what hierarchy level?
   - Minimum delay constraint?
   - How many edges?

3. **Bridge redesign: What changes?**
   - Target depth: L2, L3, or mixed?
   - CONTAINS edge treatment: keep as causal, or separate propagation step?
   - How to handle the 88 orphan port nodes?

4. **Priority order:**
   - What gives maximum scenario pass rate improvement with minimum effort?
   - What's the order of implementation?

5. **Edge budget:**
   - Current: 598 non-CONTAINS edges (303 bridges + 295 T→T lateral)
   - What's the target total? Too many edges = "everything connects to everything"
   - What's the edge density that PPR works best at?

Be concrete — give me numbers, not "it depends." I need to implement this."""

    a5, t5 = send_message(client, chat, msg5, 5)
    transcript.append({"turn": 5, "role": "user", "message": msg5[:300] + "...[truncated]"})
    transcript.append({"turn": 5, "role": "gemini", "thinking": t5, "answer": a5})
    print(f"\n--- GEMINI TURN 5 ---\n{a5[:800]}...\n")

    # =========================================================================
    # Save full transcript
    # =========================================================================
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "graph_structure_chat.md"

    with open(out_path, "w") as f:
        f.write("# Graph Structure Revalidation — Gemini Research Chat\n\n")
        f.write("Model: gemini-3.1-pro-preview | Thinking: high | Temperature: 0.3\n\n")

        for entry in transcript:
            turn = entry["turn"]
            role = entry["role"]
            if role == "user":
                f.write(f"---\n\n## Turn {turn} — User\n\n")
                f.write(f"{entry['message']}\n\n")
            else:
                f.write(f"## Turn {turn} — Gemini\n\n")
                if entry.get("thinking"):
                    f.write(f"<details><summary>Thinking</summary>\n\n{entry['thinking']}\n\n</details>\n\n")
                f.write(f"{entry['answer']}\n\n")

    raw_path = OUTPUT_DIR / "graph_structure_chat.json"
    with open(raw_path, "w") as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)

    print(f"\nTranscript saved to {out_path}")
    print(f"Raw JSON saved to {raw_path}")


def research_contains_debate(client):
    """Debate: CONTAINS propagation vs direct bridges — scalability and mechanics."""

    from graph.merge import TaxonomyMerger
    from graph.markov_engine import CausalMarkovEngine, get_causal_entry, CAUSAL_TYPES
    from collections import Counter, defaultdict
    import networkx as nx

    G = TaxonomyMerger().merge()

    # Build hierarchy info
    contains_tree = nx.DiGraph()
    for s, d, a in G.edges(data=True):
        if a.get("type") == "CONTAINS":
            contains_tree.add_edge(s, d)

    # Depth map
    all_children = set(d for _, d in contains_tree.edges())
    all_parents = set(s for s, _ in contains_tree.edges())
    roots = all_parents - all_children
    depth = {}
    def compute_depth(node, d=0):
        depth[node] = d
        for child in contains_tree.successors(node):
            compute_depth(child, d + 1)
    for r in roots:
        compute_depth(r)
    depth_counts = Counter(depth.values())

    # Edge stats
    edge_counts = defaultdict(int)
    for s, d, a in G.edges(data=True):
        sc = G.nodes[s].get("category", "?")
        dc = G.nodes[d].get("category", "?")
        sw = "T" if sc.startswith("T") else ("I" if sc.startswith("I") else "?")
        dw = "T" if dc.startswith("T") else ("I" if dc.startswith("I") else "?")
        etype = a.get("type", "?")
        edge_counts[f"{sw}→{dw} {etype}"] += 1

    # Full hierarchy examples
    examples = {}
    for node in ["lpg_cylinder", "brent_crude", "retail_petrol", "hospital_beds",
                  "it_sector_salary", "credit_card_dues", "retail_tomato",
                  "savings_account_balance", "ambient_aqi", "electricity_tariff"]:
        if node not in G.nodes:
            continue
        chain = [node]
        current = node
        while True:
            parents = [p for p in G.predecessors(current) if G.edges[p, current].get("type") == "CONTAINS"]
            if not parents:
                break
            chain.append(parents[0])
            current = parents[0]
        chain.reverse()
        cat = G.nodes[node].get("category", "?")
        examples[node] = {"hierarchy": " → ".join(chain), "category": cat, "depth": f"L{len(chain)}"}

    # Bridges that land on each hierarchy level
    bridge_depth = Counter()
    for s, d, a in G.edges(data=True):
        etype = a.get("type", "?")
        sc = G.nodes[s].get("category", "?")
        dc = G.nodes[d].get("category", "?")
        if sc.startswith("T") and dc.startswith("I") and etype != "CONTAINS":
            d_depth = depth.get(d, -1)
            bridge_depth[f"L{d_depth + 1}"] += 1

    # PPR from brent_crude results
    engine = CausalMarkovEngine(G)
    brent_results = engine.evaluate_impact("brent_crude", event_direction=1)
    brent_summary = [{"node": r["node"], "prob": round(r["probability"], 6),
                       "cat": G.nodes[r["node"]].get("category", "?")}
                      for r in sorted(brent_results, key=lambda x: -x["probability"])[:15]]

    graph_context = f"""
=== GRAPH STRUCTURE ===
738 nodes, 1320 edges total
- 16 L1 roots (5 Trigger: T1-T5, 11 Impact: I1-I11)
- 91 L2 nodes (domain groups)
- 250 L3 nodes (subcategories)
- 381 L4 nodes (leaf-level, concrete items that touch a citizen's life)

Hierarchy: L1 →CONTAINS→ L2 →CONTAINS→ L3 →CONTAINS→ L4
CONTAINS edges: 722 (55% of all edges)
CONTAINS goes DOWNWARD only (parent→child). There is no upward traversal.

=== TRIGGER WORLD (T1-T5, ~230 nodes) ===
T1: Natural Systems (monsoon, earthquakes, hydrology, ecology)
T2: Institutional (RBI, government, judiciary, regulators, unions, religious forces)
T3: Macro-Economic (commodities, trade, GDP, inflation, financial markets, forex)
T4: Infrastructure (power grid, telecom, transport, pipelines, data centers)
T5: Social Forces (demographics, migration, consumer confidence, behavioral shifts)

Each T-L1 has L2→L3→L4 hierarchy. Example:
  t3 (Macro-Economic)
    → global_commodity_markets (L2)
      → energy_commodities (L3)
        → brent_crude (L4)
        → global_natural_gas (L4)
        → international_coal_prices (L4)

T→T lateral edges: 295 (causal links WITHIN trigger world, e.g. brent_crude →AFFECTS→ wpi)

=== IMPACT WORLD (I1-I11, ~510 nodes) ===
I1: Food & Grocery
I2: Housing & Utilities (household energy, water, sanitation, rent)
I3: Transport & Mobility
I4: Livelihood & Employment
I5: Personal Finance
I6: Health & Medical
I7: Education
I8: Safety & Security
I9: Environment & Living Conditions
I10: Digital & Connectivity
I11: Leisure & Lifestyle

Example Impact hierarchy:
  i2 (Housing & Utilities)
    → household_energy (L2)
      → cooking_fuel (L3)
        → lpg_cylinder (L4)    ← what a citizen actually pays for
        → piped_natural_gas (L4)
      → residential_electricity (L3)
        → electricity_tariff (L4)

I→I lateral edges: 0 (NONE — being debated)
I→T feedback edges: 0 (decided: will not add)

=== BRIDGES (T→I, 303 edges) ===
These connect Trigger nodes to Impact nodes via causal edge types (AFFECTS, SUPPLIES, etc.)

Bridge landing depth:
{json.dumps(dict(bridge_depth), indent=2)}

Examples of current bridges:
  energy_commodities (T3/L3) →AFFECTS→ household_energy (I2/L2)
  brent_crude (T3/L4) →AFFECTS→ retail_tomato (I1/L4)
  monetary_policy_committee (T2/L3) →AFFECTS→ home_loan_emi (I5/L4)
  meteorological_systems (T1/L2) →DISRUPTS→ fresh_produce (I1/L2)

=== HOW PPR SCORING WORKS NOW ===
1. PPR starts at trigger node (e.g., brent_crude)
2. "Elevator": if trigger is a leaf with no causal outgoing edges, walk UP the CONTAINS
   hierarchy until finding a node with causal out-edges
3. Run Personalized PageRank on the causal subgraph (all non-IS_A edges, INCLUDING CONTAINS)
4. After PPR converges, propagate scores DOWN via CONTAINS to child nodes
5. Compute magnitude (hub-penalized path product) and timing (delay sum) along dominant path

=== THE IRAN WAR → LPG EXAMPLE ===
Suppose "Iran war disrupts oil supply" fires. In our graph:

Trigger path (works): geopolitical events → global markets → brent_crude
Entry point: brent_crude (T3/L4)

Current PPR from brent_crude reaches 22 nodes:
{json.dumps(brent_summary, indent=2)}

PROBLEM: Zero I2 (Housing) nodes reached. Specifically, lpg_cylinder is NOT reached.

Why? The path SHOULD be:
  brent_crude (T3/L4) → [elevator up?] → energy_commodities (T3/L3) → [bridge] → household_energy (I2/L2) → [CONTAINS down] → cooking_fuel (I3) → [CONTAINS down] → lpg_cylinder (L4)

But brent_crude has its own causal out-edges (AFFECTS wpi, AFFECTS india_trade_deficit, AFFECTS retail_tomato),
so the elevator doesn't activate. And brent_crude has no DIRECT bridge to anything in I2.
The bridge is on its PARENT (energy_commodities), but brent_crude can't walk UP to energy_commodities
because CONTAINS goes downward.

=== SAMPLE NODE HIERARCHIES ===
{json.dumps(examples, indent=2)}
"""

    chat = client.chats.create(
        model="gemini-3.1-pro-preview",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level="high",
                include_thoughts=True,
            ),
            temperature=0.3,
        ),
    )

    transcript = []

    # =========================================================================
    # TURN 1: Present the two approaches
    # =========================================================================
    msg1 = f"""I'm building a causal knowledge graph for a news impact system in India. I need your help resolving a critical architectural decision about how hierarchy (CONTAINS edges) should interact with the scoring engine (Personalized PageRank).

Here is my complete graph structure:
{graph_context}

We are debating TWO approaches:

**Approach A: Remove CONTAINS from PPR, bridge directly to L3/L4**
- PPR only traverses causal edges (AFFECTS, SUPPLIES, DISRUPTS, etc.)
- CONTAINS becomes purely organizational (UI grouping, score aggregation)
- Every leaf node that should be reachable needs its own direct bridge from a Trigger node
- Means retargeting all 303 existing bridges from L2 to L3/L4
- Bridge count jumps from 303 to potentially 700-800+
- Adding a new L4 node means creating new bridges for it

**Approach B: Keep CONTAINS in PPR but add a "propagation" step**
- Bridges can target L2 or L3 (where the real-world mechanism operates)
- When a bridge hits L2, signal automatically propagates DOWN to L3/L4 children
- Propagation uses a fixed weight (e.g., 0.9) and doesn't compete with causal edges for probability mass
- Separate from the causal PPR walk — it's a post-processing expansion
- Adding a new L4 node under an existing L3 parent automatically inherits bridge coverage
- Fewer bridges needed, but risk of "causal bleeding" (coal hitting LPG)

Please analyze both approaches. What are the mathematical implications for PPR? What does graph theory say about mixing hierarchical and causal edges? Which approach scales better as the graph grows from 738 to 2000+ nodes?"""

    a1, t1 = send_message(client, chat, msg1, 1)
    transcript.append({"turn": 1, "role": "user", "message": msg1[:300] + "...[truncated]"})
    transcript.append({"turn": 1, "role": "gemini", "thinking": t1, "answer": a1})
    print(f"\n--- GEMINI TURN 1 ---\n{a1[:800]}...\n")

    # =========================================================================
    # TURN 2: The Iran → LPG worked example
    # =========================================================================
    msg2 = """Let's make this concrete with a real scenario: "Iran war disrupts global oil supply."

In our graph, this would fire at brent_crude (T3/L4). The causal chain a human would trace:
1. Iran war → oil supply disruption → brent crude price spikes
2. Brent crude → Indian crude basket price → refinery input cost
3. Refinery input cost → LPG production cost → LPG cylinder retail price goes up
4. Also: crude → diesel → trucking costs → food delivery costs → grocery prices

In our current graph, brent_crude has these causal out-edges:
  brent_crude →AFFECTS→ wpi (wholesale price index)
  brent_crude →AFFECTS→ india_trade_deficit
  brent_crude →AFFECTS→ retail_tomato (via transport)
  brent_crude →AFFECTS→ tour_package

The bridge energy_commodities →AFFECTS→ household_energy EXISTS, but brent_crude can't reach it because:
- brent_crude is a CHILD of energy_commodities (CONTAINS goes downward)
- brent_crude already has causal out-edges, so the elevator doesn't activate

Walk me through EXACTLY how each approach would handle this:

**Under Approach A (direct L4 bridges):**
- What bridges would need to exist?
- How many new edges are we talking about?
- What happens when someone adds "aviation_turbine_fuel" as a new L4 node?

**Under Approach B (propagation step):**
- How does the signal get from brent_crude to lpg_cylinder?
- How do you prevent coal_prices from also hitting lpg_cylinder?
- What does the propagation math look like?

Also consider: this is a solo developer project. The graph will grow from 738 to ~2000 nodes over time. Which approach means less manual edge maintenance? Which is more robust to node additions?"""

    a2, t2 = send_message(client, chat, msg2, 2)
    transcript.append({"turn": 2, "role": "user", "message": msg2[:300] + "...[truncated]"})
    transcript.append({"turn": 2, "role": "gemini", "thinking": t2, "answer": a2})
    print(f"\n--- GEMINI TURN 2 ---\n{a2[:800]}...\n")

    # =========================================================================
    # TURN 3: Scalability — adding nodes and edges over time
    # =========================================================================
    msg3 = """Now let's stress-test scalability. Our graph will grow. How does each approach handle these real scenarios?

**Scenario 1: Adding a new L4 impact node**
Someone adds "induction_cooktop_electricity" under residential_electricity (I2/L3).
- Approach A: What bridges need to be created? How does the developer know which ones?
- Approach B: Does it automatically inherit from residential_electricity? What about false positives?

**Scenario 2: Adding a new L3 subcategory**
Someone adds "electric_vehicle_charging" as a new L3 under household_energy (I2/L2), with children like "home_ev_charger" and "public_ev_station" (L4).
- Approach A: Needs bridges from what trigger nodes? How many?
- Approach B: Does it inherit household_energy's bridges? Is that correct? (EV charging is affected by electricity tariffs AND oil price drop competition, not cooking fuel or LPG)

**Scenario 3: Graph grows to 2000 nodes**
- Approach A: How many bridges would we expect? Is 2000+ bridges manageable?
- Approach B: Does the CONTAINS propagation scale without causal bleeding?

**Scenario 4: Adding I→I lateral edges**
We're adding ~150-200 I→I lateral edges. How do these interact with each approach?
- With Approach A: Do I→I edges only connect L4→L4? What about L3→L3?
- With Approach B: If I→I edges connect L3 nodes, does propagation automatically cascade to L4?

**The core tension:** Approach A is precise but requires manual bridge maintenance for every new leaf. Approach B is scalable but risks false positives. Is there a synthesis that gives us precision AND scalability?"""

    a3, t3 = send_message(client, chat, msg3, 3)
    transcript.append({"turn": 3, "role": "user", "message": msg3[:300] + "...[truncated]"})
    transcript.append({"turn": 3, "role": "gemini", "thinking": t3, "answer": a3})
    print(f"\n--- GEMINI TURN 3 ---\n{a3[:800]}...\n")

    # =========================================================================
    # TURN 4: The sibling problem and specificity
    # =========================================================================
    msg4 = """Let me push back on both approaches with a specific failure mode: the sibling problem.

Under household_energy (I2/L2):
  cooking_fuel (L3):  lpg_cylinder, piped_natural_gas
  residential_electricity (L3):  electricity_tariff, residential_power_supply

A bridge from energy_commodities →AFFECTS→ household_energy is too broad — coal affects electricity but NOT LPG directly. Oil affects LPG but NOT electricity tariff directly.

But even at L3: cooking_fuel has BOTH lpg_cylinder AND piped_natural_gas. A crude oil shock affects LPG but natural gas prices are set by a different commodity (global_natural_gas), so even an L3 bridge is sometimes too coarse.

This suggests we need L4 bridges everywhere. But that's 381 leaf nodes × ~2 triggers each = 762+ bridges just for the impact side.

Now consider the trigger side. In the trigger world:
  energy_commodities (L3): brent_crude, global_natural_gas, international_coal_prices

When brent_crude fires, the PPR currently can't use the bridge on energy_commodities (its parent) because CONTAINS is downward-only. So either:
1. We duplicate the bridge: brent_crude →AFFECTS→ lpg_cylinder (and also global_natural_gas →AFFECTS→ piped_natural_gas). That's N×M edges.
2. We add upward traversal somehow — let the PPR surfer walk UP CONTAINS from child to parent.

Option 2 is interesting but creates bidirectional CONTAINS, which complicates the hierarchy. What do you think?

Also: is there a THIRD approach that the graph theory literature uses for this exact problem — hierarchical graphs where leaf-to-leaf causal links need to respect the taxonomy?"""

    a4, t4 = send_message(client, chat, msg4, 4)
    transcript.append({"turn": 4, "role": "user", "message": msg4[:300] + "...[truncated]"})
    transcript.append({"turn": 4, "role": "gemini", "thinking": t4, "answer": a4})
    print(f"\n--- GEMINI TURN 4 ---\n{a4[:800]}...\n")

    # =========================================================================
    # TURN 5: Final recommendation — concrete, implementable
    # =========================================================================
    msg5 = """Based on everything we've discussed, I need your FINAL RECOMMENDATION. Be concrete and implementable.

Requirements:
1. Graph currently has 738 nodes (381 L4 leaves). Will grow to ~2000 nodes.
2. Solo developer — edge maintenance must be sustainable.
3. PPR scoring must be mathematically sound (no ecological fallacy, no probability dilution).
4. New node additions should require minimal manual edge work.
5. The Iran→LPG example must work correctly.
6. Coal→electricity must work WITHOUT coal→LPG false positives.

Give me:
1. **The recommended architecture** — what role does CONTAINS play in PPR? Direct traversal, propagation step, bidirectional, or something else?
2. **Bridge strategy** — what level do bridges target? How many total?
3. **I→I edge strategy** — what levels, how they interact with hierarchy
4. **The elevator problem** — how does brent_crude reach energy_commodities' bridges?
5. **Scalability math** — edge growth rate as nodes grow
6. **Implementation priority** — what to change first for maximum impact

Format as an actionable specification I can implement directly."""

    a5, t5 = send_message(client, chat, msg5, 5)
    transcript.append({"turn": 5, "role": "user", "message": msg5[:300] + "...[truncated]"})
    transcript.append({"turn": 5, "role": "gemini", "thinking": t5, "answer": a5})
    print(f"\n--- GEMINI TURN 5 ---\n{a5[:800]}...\n")

    # =========================================================================
    # Save
    # =========================================================================
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "contains_debate_chat.md"

    with open(out_path, "w") as f:
        f.write("# CONTAINS Propagation vs Direct Bridges — Gemini Debate\n\n")
        f.write("Model: gemini-3.1-pro-preview | Thinking: high | Temperature: 0.3\n\n")

        for entry in transcript:
            turn = entry["turn"]
            role = entry["role"]
            if role == "user":
                f.write(f"---\n\n## Turn {turn} — User\n\n")
                f.write(f"{entry['message']}\n\n")
            else:
                f.write(f"## Turn {turn} — Gemini\n\n")
                if entry.get("thinking"):
                    f.write(f"<details><summary>Thinking</summary>\n\n{entry['thinking']}\n\n</details>\n\n")
                f.write(f"{entry['answer']}\n\n")

    raw_path = OUTPUT_DIR / "contains_debate_chat.json"
    with open(raw_path, "w") as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)

    print(f"\nTranscript saved to {out_path}")
    print(f"Raw JSON saved to {raw_path}")


TOPICS = {
    "weights": research_weights,
    "markov": research_markov,
    "structure": research_graph_structure,
    "contains": research_contains_debate,
}


def main():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
        sys.exit(1)

    args = sys.argv[1:]
    if not args or args[0] not in TOPICS:
        print(f"Usage: python -m audit.gemini_chat <topic>")
        print(f"Topics: {list(TOPICS.keys())}")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    TOPICS[args[0]](client)


if __name__ == "__main__":
    main()
