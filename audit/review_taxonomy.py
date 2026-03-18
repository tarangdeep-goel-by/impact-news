"""Review TAXONOMY.md with Gemini 3.1 Pro.

Sends the full taxonomy constitution + algorithm to Gemini for
consistency review, gap detection, and contradiction analysis.

Usage:
    python -m audit.review_taxonomy
"""

import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import types

OUTPUT_DIR = Path("taxonomy/eval_results")


def send_message(chat, message: str, turn: int) -> tuple[str, str]:
    """Send a message and return (answer, thinking)."""
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
        return "", ""

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


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        return

    client = genai.Client(api_key=api_key)

    # Load taxonomy
    taxonomy_path = Path("taxonomy/TAXONOMY.md")
    taxonomy_text = taxonomy_path.read_text()

    # Load graph stats for context
    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults
    from collections import Counter

    m = TaxonomyMerger()
    G = m.merge()
    apply_defaults(G)

    edge_types = Counter()
    for u, v, d in G.edges(data=True):
        edge_types[d.get("type", "")] += 1

    cat_counts = Counter()
    for n, d in G.nodes(data=True):
        cat_counts[d.get("category", "")] += 1

    graph_stats = f"""Current graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges
Edge types: {dict(edge_types.most_common())}
Nodes per L1: {dict(sorted(cat_counts.items()))}
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
    # TURN 1: Full taxonomy review
    # =========================================================================
    msg1 = f"""You are reviewing the constitution of a causal knowledge graph for a news impact analysis system focused on India. This graph traces how macro events (oil price hikes, monsoons, policy changes) cascade through to citizen-level impacts (your EMI, your food costs, your commute).

Here is the full taxonomy document — the rules, categories, algorithm, and build phases:

---
{taxonomy_text}
---

Current graph stats:
{graph_stats}

Please perform a deep review. For each issue found, classify as:
- **CONTRADICTION**: Two rules say incompatible things
- **GAP**: Something important is unaddressed
- **INCONSISTENCY**: Rule says X but example/stress-test shows Y
- **IMPROVEMENT**: Not wrong, but could be clearer or stronger

Focus especially on:
1. Do Rules 18 (Bridge Targeting) and 20 (I→I Targeting) contradict each other or Rule 7?
2. Is the PPR algorithm section consistent with the rules (e.g., does Phase 3 CONTAINS propagation conflict with Rule 20's "never target L2" constraint)?
3. Are the example causal chains valid under the current rules?
4. Are there missing rules for edge types that need governance (e.g., when to use SUPPLIES vs AFFECTS vs PRODUCES)?
5. The build phases table still shows "Bridge + Feedback edges (T→I and I→T)" in Phase 3, but Rule 7 says "No I→T feedback edges" — is this a contradiction?
6. North Star Metrics says 300-350 total nodes but the graph already has 738 — is this outdated?
7. Any other contradictions, gaps, or inconsistencies.

Be thorough and specific. Quote the exact conflicting text when flagging issues."""

    a1, t1 = send_message(chat, msg1, 1)
    transcript.append({"turn": 1, "role": "user", "message": msg1[:200] + "...[truncated]"})
    transcript.append({"turn": 1, "role": "gemini", "thinking": t1, "answer": a1})
    print(f"\n--- GEMINI TURN 1 ---\n{a1[:2000]}...\n")

    # =========================================================================
    # TURN 2: Follow up on critical issues
    # =========================================================================
    msg2 = """Good analysis. Now focus specifically on what needs to change for the I→I lateral edge generation phase we're about to start.

We currently have:
- 738 nodes in 16 CONTAINS trees
- 291 T→T lateral edges (authored in T1-T5.yaml)
- 305 T→I bridge edges (in bridge_edges.yaml)
- 0 I→I lateral edges (clean slate — we stripped all previous ones due to quality issues)
- Multi-seed PPR engine (committed, working)

We're about to generate I→I edges domain by domain using Gemini, following Rule 20.

Questions:
1. Given Rule 20 says "target L3 by default", what happens when an I-world L1 has no L3 nodes (only L2→L4)? Should we allow L4→L4 I→I edges in that case?
2. Rule 20 says "never target L2" but Phase 3 CONTAINS propagation pushes scores DOWN from L2/L3 to children. If we target L3, propagation gives the score to all L4 children. Is this always correct? What about cases where only one L4 child is affected?
3. How should we handle the edge type selection for I→I edges? We have 10 causal types but no guidance on when to use SUPPLIES vs AFFECTS vs PRODUCES for I→I connections. Can you propose a decision tree?
4. For weight assignment: should I→I edges generally be weaker (lower weight) than T→I bridges since they represent secondary cascades? Or should weight purely reflect the causal strength regardless of edge category?

Be concrete and actionable — we're implementing this today."""

    a2, t2 = send_message(chat, msg2, 2)
    transcript.append({"turn": 2, "role": "user", "message": msg2[:200] + "...[truncated]"})
    transcript.append({"turn": 2, "role": "gemini", "thinking": t2, "answer": a2})
    print(f"\n--- GEMINI TURN 2 ---\n{a2[:2000]}...\n")

    # =========================================================================
    # Save results
    # =========================================================================
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Save markdown
    md_path = OUTPUT_DIR / "taxonomy_review.md"
    md_content = f"# Taxonomy Review — Gemini 3.1 Pro\n\n"
    for entry in transcript:
        if entry["role"] == "user":
            md_content += f"## Turn {entry['turn']} (User)\n\n{entry['message']}\n\n"
        else:
            md_content += f"## Turn {entry['turn']} (Gemini)\n\n"
            if entry.get("thinking"):
                md_content += f"<details><summary>Thinking ({len(entry['thinking'])} chars)</summary>\n\n{entry['thinking']}\n\n</details>\n\n"
            md_content += f"{entry['answer']}\n\n"
    md_path.write_text(md_content)
    print(f"\nSaved: {md_path}")

    # Save JSON
    json_path = OUTPUT_DIR / "taxonomy_review.json"
    json_path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False))
    print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
