"""Review generated lateral edges with Gemini 3.1 Pro.

Sends all intra-L1 (or cross-L1) lateral edges to Gemini for
quality review against the taxonomy constitution.

Usage:
    python -m audit.review_laterals intra    # review intra-L1 laterals
    python -m audit.review_laterals cross    # review cross-L1 portals (future)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import yaml

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
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["intra", "cross"], help="Which lateral set to review")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        sys.exit(1)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Load edges
    lateral_dir = Path("taxonomy/laterals")
    all_edges = {}
    total = 0
    for f in sorted(lateral_dir.glob("i*_laterals.yaml")):
        l1 = f.stem.replace("_laterals", "").upper()
        edges = yaml.safe_load(f.read_text()) or []
        all_edges[l1] = edges
        total += len(edges)

    # Load taxonomy rules for context
    taxonomy_text = Path("taxonomy/TAXONOMY.md").read_text()

    # Format edges for prompt
    edges_text = ""
    for l1, edges in sorted(all_edges.items()):
        edges_text += f"\n## {l1} ({len(edges)} edges)\n\n"
        for e in edges:
            edges_text += f"- {e['from']} → {e['to']} ({e['type']}, w={e.get('weight','?')}, p={e.get('polarity','?')}, d={e.get('delay','?')})\n"
            edges_text += f"  \"{e.get('description','')}\"\n"

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
    # TURN 1: Context + full edge review
    # =========================================================================
    msg1 = f"""You are reviewing the quality of machine-generated lateral edges for a causal knowledge graph.

## What this system does

Impact News is a causal news personalization engine for India. It ingests news articles, extracts what each article affects, and traces impact chains through a knowledge graph to determine how macro events affect individual citizens.

The graph has two worlds:
- **Trigger world (T1-T5):** System-level entities (crude oil, RBI, monsoon, infrastructure)
- **Impact world (I1-I11):** Citizen-level entities (tomato price, EMI, commute, hospital beds)

Edges flow: T→T (within trigger world) → T→I (bridges to impact) → I→I (citizen cascades).

We currently have T→T and T→I edges built. We just generated the **I→I intra-L1 lateral edges** using Gemini 3.1 Pro — these are causal edges WITHIN each Impact L1 tree (e.g., within I1 Food, within I5 Finance).

## The edges to review ({total} edges across 11 L1s)

{edges_text}

## Key rules these edges must follow

1. **Rule 20: Never target L2 nodes** (organizational categories). Target L3 by default, L4 only for exceptions.
2. **Rule 12b: Edge type priority** — PRODUCES > SUPPLIES > FUNDS > DISRUPTS > DEPENDS_ON > AFFECTS (fallback). AFFECTS should be minority.
3. **Rule 15: Description must explain mechanism**, not restate the edge.
4. **Rule 14: No cycles** within the same world.
5. **Rule 1: Polarity** describes covariation of entity axes (+1 = same direction, -1 = opposite).
6. **Weight** = causal pass-through strength (how much of a 10% shock in A reaches B), not global importance.

## Your task

For each L1 batch, evaluate:

1. **INVALID edges** — wrong polarity, wrong edge type, L2 target, factually incorrect mechanism, or cycle-creating. These should be REMOVED.
2. **QUESTIONABLE edges** — defensible but debatable weight/polarity/type. Flag with reasoning.
3. **MISSING edges** — obvious intra-L1 causal chains that Gemini overlooked.
4. **Overall quality score** per L1 (1-10).

Be specific. Quote edge IDs (from→to). For invalid edges, explain exactly what's wrong."""

    a1, t1 = send_message(chat, msg1, 1)
    transcript.append({"turn": 1, "role": "user", "message": msg1[:200] + "...[truncated]"})
    transcript.append({"turn": 1, "role": "gemini", "thinking": t1, "answer": a1})
    print(f"\n--- GEMINI TURN 1 ---\n{a1[:3000]}...\n")

    # =========================================================================
    # Save
    # =========================================================================
    OUTPUT_DIR.mkdir(exist_ok=True)
    md_path = OUTPUT_DIR / f"laterals_{args.mode}_review.md"
    md_content = f"# Lateral Edge Review ({args.mode}) — Gemini 3.1 Pro\n\n"
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

    json_path = OUTPUT_DIR / f"laterals_{args.mode}_review.json"
    json_path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False))
    print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
