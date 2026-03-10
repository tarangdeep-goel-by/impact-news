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


TOPICS = {
    "weights": research_weights,
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
