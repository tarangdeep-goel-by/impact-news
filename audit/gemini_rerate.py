"""Re-rate causal edge weights using Gemini 3.1 Pro.

Sends edges in batches grouped by source file, gets calibrated weights
back, and updates the source YAML files in-place.

Usage:
    python -m audit.gemini_rerate all              # Run all 9 batches
    python -m audit.gemini_rerate T1 T2 bridges_1  # Specific batches
    python -m audit.gemini_rerate --list            # List batch IDs and edge counts
    python -m audit.gemini_rerate --apply           # Apply saved weights (skip Gemini)
"""

import argparse
import math
import os
import sys
import time
from pathlib import Path

import yaml

TAXONOMY_DIR = Path("taxonomy")
OUTPUT_DIR = Path("taxonomy/eval_results")

CAUSAL_TYPES = {"AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES",
                "DEPENDS_ON", "FUNDS", "COMPETES_WITH", "EMPLOYS", "MANAGES"}

# Batch definitions: batch_id -> (source_files, filter_fn)
# filter_fn takes (edges, index) and returns the slice for this batch
BATCH_DEFS = {
    "T1": {
        "files": ["taxonomy/T1.yaml"],
        "has_nodes": True,
    },
    "T2": {
        "files": ["taxonomy/T2.yaml"],
        "has_nodes": True,
    },
    "T3": {
        "files": ["taxonomy/T3.yaml"],
        "has_nodes": True,
    },
    "T4_T5": {
        "files": ["taxonomy/T4.yaml", "taxonomy/T5.yaml"],
        "has_nodes": True,
    },
    "bridges_1": {
        "files": ["taxonomy/bridge_edges.yaml"],
        "has_nodes": False,
        "split": (0, 3),  # first third
    },
    "bridges_2": {
        "files": ["taxonomy/bridge_edges.yaml"],
        "has_nodes": False,
        "split": (1, 3),  # second third
    },
    "bridges_3": {
        "files": ["taxonomy/bridge_edges.yaml"],
        "has_nodes": False,
        "split": (2, 3),  # final third
    },
    "laterals_1": {
        "files": ["taxonomy/lateral_edges.yaml"],
        "has_nodes": False,
        "split": (0, 2),  # first half
    },
    "laterals_2": {
        "files": ["taxonomy/lateral_edges.yaml"],
        "has_nodes": False,
        "split": (1, 2),  # second half
    },
}

ALL_BATCH_IDS = list(BATCH_DEFS.keys())


def load_edges_from_file(path: Path) -> list[dict]:
    """Load all edges from a YAML file."""
    data = yaml.safe_load(path.read_text())
    if isinstance(data, dict):
        return data.get("edges", [])
    return []


def filter_causal(edges: list[dict]) -> list[dict]:
    """Keep only causal edges (exclude CONTAINS, IS_A)."""
    return [e for e in edges if e.get("type") in CAUSAL_TYPES]


def get_batch_edges(batch_id: str) -> tuple[list[dict], list[Path]]:
    """Get causal edges and source file paths for a batch.

    Returns (edges, source_paths).
    """
    defn = BATCH_DEFS[batch_id]
    source_paths = [Path(f) for f in defn["files"]]

    all_causal = []
    for path in source_paths:
        edges = load_edges_from_file(path)
        all_causal.extend(filter_causal(edges))

    # Apply split if defined (for bridge/lateral sub-batches)
    if "split" in defn:
        idx, parts = defn["split"]
        chunk_size = math.ceil(len(all_causal) / parts)
        start = idx * chunk_size
        end = min(start + chunk_size, len(all_causal))
        all_causal = all_causal[start:end]

    return all_causal, source_paths


def format_edges_for_prompt(edges: list[dict]) -> str:
    """Format edges as YAML for the prompt."""
    simplified = []
    for e in edges:
        simplified.append({
            "from": e["from"],
            "to": e["to"],
            "type": e.get("type", "AFFECTS"),
            "weight": e.get("weight", 0.5),
            "polarity": e.get("polarity", 1),
            "description": e.get("description", ""),
        })
    return yaml.dump(simplified, default_flow_style=False, sort_keys=False, allow_unicode=True)


def build_prompt(edges_yaml: str) -> str:
    """Build the Gemini re-rating prompt."""
    return f"""You are calibrating edge weights for a causal knowledge graph modeling how macro events affect Indian citizens' daily lives.

Weight = "causal pass-through rate" — if the source entity changes by 10%, what percentage of that change reaches the target?

## Calibration Examples
- brent_crude → retail_diesel: If crude rises 10%, diesel rises ~8%. Weight = 0.80
- brent_crude → retail_tomato: If crude rises 10%, tomato rises ~2%. Weight = 0.20
- monetary_policy_committee → home_loan_emi: If repo rate changes 10%, EMI changes ~7%. Weight = 0.70
- southwest_monsoon → retail_rice: If monsoon deficit is 10%, rice price rises ~5%. Weight = 0.50

## Weight Scale
- 0.85-0.95: Near 1:1 pass-through (wheat_flour → bread price)
- 0.65-0.85: Strong but buffered (interest_rate → EMI)
- 0.40-0.65: Noticeable but diluted (tariff → meal_cost)
- 0.20-0.40: Weak, indirect (distant regulatory → local price)
- Below 0.20: Consider removing (too weak for causal model)

## Think About
- Buffer mechanisms (government subsidies, reserves, imports)
- Time delays and price stickiness
- Alternative sources/substitution effects
- Government intervention and price controls
- Supply chain absorption

## Current Edges to Re-Rate
{edges_yaml}

## Output Format
Return ONLY a YAML array. No commentary, no markdown fences:
- from: source_node_id
  to: target_node_id
  weight: 0.XX
  reasoning: "One sentence explaining the pass-through logic"
"""


def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        sys.exit(1)
    from google import genai
    return genai.Client(api_key=api_key)


def call_gemini(client, prompt: str, batch_id: str) -> tuple[str, str]:
    """Send prompt to Gemini 3.1 Pro with thinking."""
    from google.genai import types

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

    print(f"\n{'='*60}")
    print(f"Re-rating batch {batch_id} ({len(prompt)} chars)...")
    print(f"{'='*60}")

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = chat.send_message(prompt)
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


def parse_yaml_response(response: str) -> list[dict]:
    """Parse YAML edges from Gemini response, handling markdown fences."""
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        edges = yaml.safe_load(text)
        if isinstance(edges, list):
            return edges
        return []
    except yaml.YAMLError as e:
        print(f"  YAML parse error: {e}")
        return []


def match_and_validate(original_edges: list[dict], rerated: list[dict]) -> tuple[list[dict], list[dict]]:
    """Match rerated edges to originals and validate.

    Returns (updates, warnings) where:
    - updates: list of {from, to, old_weight, new_weight, reasoning}
    - warnings: list of {from, to, old_weight, new_weight, reason}
    """
    # Index originals by (from, to)
    orig_map = {}
    for e in original_edges:
        key = (e["from"], e["to"])
        orig_map[key] = e

    updates = []
    warnings = []

    for r in rerated:
        src = r.get("from", "")
        dst = r.get("to", "")
        new_weight = r.get("weight")
        reasoning = r.get("reasoning", "")
        key = (src, dst)

        if key not in orig_map:
            warnings.append({
                "from": src, "to": dst,
                "old_weight": None, "new_weight": new_weight,
                "reason": "NOT FOUND in original edges",
            })
            continue

        if new_weight is None:
            warnings.append({
                "from": src, "to": dst,
                "old_weight": orig_map[key].get("weight"),
                "new_weight": None,
                "reason": "No weight returned",
            })
            continue

        old_weight = orig_map[key].get("weight", 0.5)
        diff = abs(new_weight - old_weight)

        entry = {
            "from": src, "to": dst,
            "old_weight": old_weight, "new_weight": new_weight,
            "reasoning": reasoning,
        }

        if diff > 0.3:
            warnings.append({
                **entry,
                "reason": f"Large delta: {old_weight:.2f} -> {new_weight:.2f} (diff={diff:.2f})",
            })
            # Still include in updates — user can review warnings
            updates.append(entry)
        elif new_weight < 0.15:
            warnings.append({
                **entry,
                "reason": f"Candidate for removal: weight={new_weight:.2f}",
            })
            updates.append(entry)
        else:
            updates.append(entry)

    return updates, warnings


def apply_weights_to_file(path: Path, weight_map: dict[tuple[str, str], float]) -> int:
    """Update edge weights in a source YAML file.

    Args:
        path: Path to YAML file
        weight_map: {(from, to): new_weight}

    Returns number of edges updated.
    """
    data = yaml.safe_load(path.read_text())
    edges = data.get("edges", []) if isinstance(data, dict) else []

    count = 0
    for edge in edges:
        key = (edge.get("from"), edge.get("to"))
        if key in weight_map:
            edge["weight"] = weight_map[key]
            count += 1

    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True))
    return count


def save_raw_response(batch_id: str, answer: str, thinking: str):
    """Save raw Gemini response + thinking to eval_results."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    raw_path = OUTPUT_DIR / f"rerate_{batch_id}_raw.md"
    content = f"# {batch_id} Weight Re-Rating — Gemini 3.1 Pro\n\n"
    content += f"<details><summary>Thinking ({len(thinking)} chars)</summary>\n\n{thinking}\n\n</details>\n\n"
    content += f"## Response\n\n```yaml\n{answer}\n```\n"
    raw_path.write_text(content)
    print(f"  Raw saved: {raw_path}")


def save_weights(batch_id: str, updates: list[dict], warnings: list[dict]):
    """Save validated weights to eval_results."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    weights_path = OUTPUT_DIR / f"rerate_{batch_id}_weights.yaml"
    data = {
        "batch_id": batch_id,
        "updates": updates,
        "warnings": warnings,
    }
    weights_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True))
    print(f"  Weights saved: {weights_path}")


def load_saved_weights(batch_id: str) -> tuple[list[dict], list[dict]]:
    """Load previously saved weights from eval_results."""
    weights_path = OUTPUT_DIR / f"rerate_{batch_id}_weights.yaml"
    if not weights_path.exists():
        return [], []
    data = yaml.safe_load(weights_path.read_text())
    return data.get("updates", []), data.get("warnings", [])


def apply_batch_weights(batch_id: str, updates: list[dict]):
    """Apply weight updates to source YAML files for a batch."""
    defn = BATCH_DEFS[batch_id]
    source_paths = [Path(f) for f in defn["files"]]

    weight_map = {}
    for u in updates:
        weight_map[(u["from"], u["to"])] = u["new_weight"]

    total = 0
    for path in source_paths:
        count = apply_weights_to_file(path, weight_map)
        total += count
        if count > 0:
            print(f"  Updated {count} edges in {path}")

    return total


def run_batch(client, batch_id: str):
    """Run a single batch: get edges, call Gemini, validate, save."""
    edges, source_paths = get_batch_edges(batch_id)
    if not edges:
        print(f"  No causal edges for batch {batch_id}")
        return

    print(f"\n  Batch {batch_id}: {len(edges)} causal edges from {[str(p) for p in source_paths]}")

    edges_yaml = format_edges_for_prompt(edges)
    prompt = build_prompt(edges_yaml)
    answer, thinking = call_gemini(client, prompt, batch_id)

    if not answer:
        print(f"  No response for {batch_id}")
        return

    # Save raw response
    save_raw_response(batch_id, answer, thinking)

    # Parse and validate
    rerated = parse_yaml_response(answer)
    print(f"  Parsed {len(rerated)} edges from response")

    updates, warnings = match_and_validate(edges, rerated)

    # Print warnings
    for w in warnings:
        print(f"  WARNING: {w['from']}→{w['to']}: {w['reason']}")

    # Save weights
    save_weights(batch_id, updates, warnings)

    # Apply to source files
    total = apply_batch_weights(batch_id, updates)
    print(f"  Applied {total} weight updates for batch {batch_id}")


def list_batches():
    """Print batch IDs and edge counts."""
    print(f"{'Batch':<15} {'Edges':>6}  Source Files")
    print("-" * 60)
    for batch_id in ALL_BATCH_IDS:
        edges, paths = get_batch_edges(batch_id)
        files_str = ", ".join(str(p) for p in paths)
        print(f"{batch_id:<15} {len(edges):>6}  {files_str}")
    print(f"\n{len(ALL_BATCH_IDS)} batches total")


def apply_saved():
    """Apply previously saved weights from eval_results without calling Gemini."""
    for batch_id in ALL_BATCH_IDS:
        updates, warnings = load_saved_weights(batch_id)
        if not updates:
            print(f"  {batch_id}: no saved weights found, skipping")
            continue

        print(f"\n  {batch_id}: applying {len(updates)} saved weights ({len(warnings)} warnings)")
        for w in warnings:
            print(f"    WARNING: {w['from']}→{w['to']}: {w.get('reason', '')}")

        total = apply_batch_weights(batch_id, updates)
        print(f"  Applied {total} weight updates for batch {batch_id}")


def main():
    parser = argparse.ArgumentParser(description="Re-rate causal edge weights via Gemini 3.1 Pro")
    parser.add_argument("batches", nargs="*", help="Batch IDs or 'all'")
    parser.add_argument("--list", action="store_true", help="List batch IDs and edge counts")
    parser.add_argument("--apply", action="store_true", help="Apply saved weights (skip Gemini)")
    args = parser.parse_args()

    if args.list:
        list_batches()
        return

    if args.apply:
        apply_saved()
        return

    if not args.batches:
        parser.print_help()
        return

    targets = ALL_BATCH_IDS if "all" in args.batches else args.batches

    # Validate batch IDs
    for bid in targets:
        if bid not in BATCH_DEFS:
            print(f"Unknown batch: {bid}. Valid: {', '.join(ALL_BATCH_IDS)}")
            sys.exit(1)

    client = get_gemini_client()

    for i, batch_id in enumerate(targets):
        run_batch(client, batch_id)
        # Pause between batches to avoid rate limits
        if i < len(targets) - 1:
            print("\n  Waiting 5s before next batch...")
            time.sleep(5)

    print(f"\nDone. Processed {len(targets)} batches.")


if __name__ == "__main__":
    main()
