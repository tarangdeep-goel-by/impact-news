"""Parse Gemini review output and apply FIX/KILL actions to graph YAML files.

Reads review_chunk_XX.md files and applies:
- FIX: Change edge type in source YAML
- KILL: Remove edge from source YAML
- WEIGHT: Apply weight overrides from rerate_chunk_XX_weights.yaml

Usage:
    python3 scripts/apply_review_fixes.py <chunk_numbers...>
    python3 scripts/apply_review_fixes.py 1 2 3        # Apply fixes from chunks 1-3
    python3 scripts/apply_review_fixes.py --dry-run 1   # Show what would change
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REVIEW_DIR = PROJECT_ROOT / "taxonomy" / "eval_results"
TAXONOMY_DIR = PROJECT_ROOT / "taxonomy"

# All YAML files that contain edges
EDGE_FILES = (
    [TAXONOMY_DIR / f"I{i}.yaml" for i in range(1, 12)]
    + [TAXONOMY_DIR / f"T{i}.yaml" for i in range(1, 6)]
    + [TAXONOMY_DIR / "bridge_edges.yaml", TAXONOMY_DIR / "lateral_edges.yaml"]
)


def parse_review(review_path: Path) -> dict:
    """Parse a review markdown file into structured actions."""
    text = review_path.read_text()
    fixes = []
    kills = []
    weight_adjustments = []

    for line in text.split("\n"):
        line = line.strip()
        # Strip leading "- " if present (some chunks use list format)
        if line.startswith("- "):
            line = line[2:]
        # Strip bold markers if present (some chunks use **KEYWORD**, some don't)
        line = line.replace("**FIX**", "FIX").replace("**KILL**", "KILL").replace("**PASS**", "PASS")

        # FIX: from→to — type should be NEW_TYPE (was OLD_TYPE). w=X.XX (current=Y.YY).
        fix_match = re.match(
            r"FIX\s+(\w+)→(\w+)\s+.*type should be (\w+)\s+\(was (\w+)\)\.\s+w=([\d.]+)\s+\(current=([\d.]+)\)",
            line,
        )
        if fix_match:
            new_type = fix_match.group(3)
            old_type = fix_match.group(4)
            if new_type != old_type:  # Skip no-op fixes (e.g., polarity-only notes)
                fixes.append({
                    "from": fix_match.group(1),
                    "to": fix_match.group(2),
                    "new_type": new_type,
                    "old_type": old_type,
                    "new_weight": float(fix_match.group(5)),
                    "old_weight": float(fix_match.group(6)),
                })
            continue

        # KILL: from→to — reason
        kill_match = re.match(r"KILL\s+(\w+)→(\w+)\s+—\s+(.*)", line)
        if kill_match:
            kills.append({
                "from": kill_match.group(1),
                "to": kill_match.group(2),
                "reason": kill_match.group(3),
            })
            continue

        # PASS with weight change: from→to w=X.XX (current=Y.YY) [reason]
        pass_match = re.match(
            r"PASS\s+(\w+)→(\w+)\s+w=([\d.]+)\s+\(current=([\d.]+)\)\s+\[",
            line,
        )
        if pass_match:
            new_w = float(pass_match.group(3))
            old_w = float(pass_match.group(4))
            if abs(new_w - old_w) >= 0.05:
                weight_adjustments.append({
                    "from": pass_match.group(1),
                    "to": pass_match.group(2),
                    "new_weight": new_w,
                    "old_weight": old_w,
                })

    return {"fixes": fixes, "kills": kills, "weights": weight_adjustments}


def find_edge_in_yaml(yaml_path: Path, from_node: str, to_node: str) -> int | None:
    """Find the line number of an edge in a YAML file. Returns line of '- from:' or None."""
    lines = yaml_path.read_text().split("\n")
    for i, line in enumerate(lines):
        if line.strip() == f"- from: {from_node}":
            # Check next line for matching 'to:'
            if i + 1 < len(lines) and lines[i + 1].strip() == f"to: {to_node}":
                return i
    return None


def apply_type_fix(yaml_path: Path, from_node: str, to_node: str, old_type: str, new_type: str) -> bool:
    """Change edge type in a YAML file."""
    text = yaml_path.read_text()
    lines = text.split("\n")
    line_idx = find_edge_in_yaml(yaml_path, from_node, to_node)
    if line_idx is None:
        return False

    # Find the type line within the next ~6 lines
    for i in range(line_idx, min(line_idx + 8, len(lines))):
        if lines[i].strip().startswith("type:"):
            if old_type in lines[i]:
                lines[i] = lines[i].replace(old_type, new_type)
                yaml_path.write_text("\n".join(lines))
                return True
    return False


def apply_weight_change(yaml_path: Path, from_node: str, to_node: str, new_weight: float) -> bool:
    """Change edge weight in a YAML file."""
    text = yaml_path.read_text()
    lines = text.split("\n")
    line_idx = find_edge_in_yaml(yaml_path, from_node, to_node)
    if line_idx is None:
        return False

    for i in range(line_idx, min(line_idx + 8, len(lines))):
        stripped = lines[i].strip()
        if stripped.startswith("w:") or stripped.startswith("weight:"):
            indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
            key = "w" if stripped.startswith("w:") else "weight"
            lines[i] = f"{indent}{key}: {new_weight}"
            yaml_path.write_text("\n".join(lines))
            return True
    return False


def kill_edge(yaml_path: Path, from_node: str, to_node: str) -> bool:
    """Remove an edge block from a YAML file."""
    text = yaml_path.read_text()
    lines = text.split("\n")
    line_idx = find_edge_in_yaml(yaml_path, from_node, to_node)
    if line_idx is None:
        return False

    # Find the extent of this edge block (until next '- from:' or end of edges section)
    end_idx = line_idx + 1
    while end_idx < len(lines):
        stripped = lines[end_idx].strip()
        if stripped.startswith("- from:") or stripped.startswith("- node:") or stripped == "":
            # Check if blank line followed by another edge
            if stripped == "" and end_idx + 1 < len(lines) and not lines[end_idx + 1].strip().startswith("- from:"):
                end_idx += 1
                continue
            break
        end_idx += 1

    del lines[line_idx:end_idx]
    yaml_path.write_text("\n".join(lines))
    return True


def main():
    dry_run = "--dry-run" in sys.argv
    chunk_nums = [int(a) for a in sys.argv[1:] if a != "--dry-run"]

    if not chunk_nums:
        print("Usage: python3 scripts/apply_review_fixes.py [--dry-run] <chunk_numbers...>")
        sys.exit(1)

    total_fixes = 0
    total_kills = 0
    total_weights = 0

    for num in chunk_nums:
        review_path = REVIEW_DIR / f"review_chunk_{num:02d}.md"
        if not review_path.exists():
            print(f"  Skipping chunk {num}: review file not found")
            continue

        actions = parse_review(review_path)
        print(f"\n=== Chunk {num} ===")
        print(f"  FIX: {len(actions['fixes'])}  KILL: {len(actions['kills'])}  WEIGHT: {len(actions['weights'])}")

        # Apply FIX actions
        for fix in actions["fixes"]:
            found = False
            for yaml_path in EDGE_FILES:
                if not yaml_path.exists():
                    continue
                if find_edge_in_yaml(yaml_path, fix["from"], fix["to"]) is not None:
                    if dry_run:
                        print(f"  [DRY] FIX {fix['from']}→{fix['to']}: {fix['old_type']}→{fix['new_type']} in {yaml_path.name}")
                    else:
                        ok = apply_type_fix(yaml_path, fix["from"], fix["to"], fix["old_type"], fix["new_type"])
                        if ok:
                            print(f"  FIX {fix['from']}→{fix['to']}: {fix['old_type']}→{fix['new_type']} in {yaml_path.name}")
                            total_fixes += 1
                        else:
                            print(f"  WARN: Could not fix {fix['from']}→{fix['to']} in {yaml_path.name}")
                    found = True
                    break
            if not found:
                print(f"  MISS: {fix['from']}→{fix['to']} not found in any YAML")

        # Apply KILL actions
        for kill_action in actions["kills"]:
            found = False
            for yaml_path in EDGE_FILES:
                if not yaml_path.exists():
                    continue
                if find_edge_in_yaml(yaml_path, kill_action["from"], kill_action["to"]) is not None:
                    if dry_run:
                        print(f"  [DRY] KILL {kill_action['from']}→{kill_action['to']} in {yaml_path.name}: {kill_action['reason']}")
                    else:
                        ok = kill_edge(yaml_path, kill_action["from"], kill_action["to"])
                        if ok:
                            print(f"  KILL {kill_action['from']}→{kill_action['to']} in {yaml_path.name}")
                            total_kills += 1
                        else:
                            print(f"  WARN: Could not kill {kill_action['from']}→{kill_action['to']} in {yaml_path.name}")
                    found = True
                    break
            if not found:
                print(f"  MISS: {kill_action['from']}→{kill_action['to']} not found in any YAML")

        # Apply weight changes
        for w in actions["weights"]:
            found = False
            for yaml_path in EDGE_FILES:
                if not yaml_path.exists():
                    continue
                if find_edge_in_yaml(yaml_path, w["from"], w["to"]) is not None:
                    if dry_run:
                        print(f"  [DRY] WEIGHT {w['from']}→{w['to']}: {w['old_weight']}→{w['new_weight']} in {yaml_path.name}")
                    else:
                        ok = apply_weight_change(yaml_path, w["from"], w["to"], w["new_weight"])
                        if ok:
                            print(f"  WEIGHT {w['from']}→{w['to']}: {w['old_weight']}→{w['new_weight']} in {yaml_path.name}")
                            total_weights += 1
                        else:
                            print(f"  WARN: Could not update weight {w['from']}→{w['to']} in {yaml_path.name}")
                    found = True
                    break
            if not found:
                print(f"  MISS: {w['from']}→{w['to']} not found in any YAML")

    if not dry_run:
        print(f"\n=== TOTALS ===")
        print(f"  Applied: {total_fixes} type fixes, {total_kills} kills, {total_weights} weight changes")
    else:
        print(f"\n[DRY RUN — no changes made]")


if __name__ == "__main__":
    main()
