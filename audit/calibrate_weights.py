"""Apply structural heuristic weight defaults to causal edges in source YAML files.

For each causal edge (not CONTAINS/IS_A):
1. Look up type default weight
2. Multiply by cross-L1 category multiplier
3. Multiply by level multiplier
4. Clamp to [0.20, 0.95], round to 2 decimal places
5. Write back to source YAML files in-place
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from pathlib import Path

import yaml

from graph.merge import TaxonomyMerger
from graph.markov_engine import CAUSAL_TYPES

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAXONOMY_DIR = Path("taxonomy")
SOURCE_FILES = (
    [f"I{i}.yaml" for i in range(1, 12)]
    + [f"T{i}.yaml" for i in range(1, 6)]
    + ["bridge_edges.yaml", "lateral_edges.yaml"]
)

TYPE_DEFAULTS = {
    "PRODUCES": 0.90,
    "SUPPLIES": 0.78,
    "FUNDS": 0.82,
    "DISRUPTS": 0.62,
    "DEPENDS_ON": 0.88,
    "REGULATES": 0.60,
    "AFFECTS": 0.45,
    "COMPETES_WITH": 0.50,
    "EMPLOYS": 0.70,
    "MANAGES": 0.65,
}

# ---------------------------------------------------------------------------
# Multiplier helpers
# ---------------------------------------------------------------------------


def _parse_world(category: str) -> str | None:
    """Return 'T' or 'I' from a category like 'T1', 'I11', etc."""
    if not category:
        return None
    c = category.upper()
    if c.startswith("T"):
        return "T"
    if c.startswith("I"):
        return "I"
    return None


def cross_l1_multiplier(src_cat: str, tgt_cat: str) -> float:
    """Multiplier based on source/target categories."""
    if not src_cat or not tgt_cat:
        return 1.0
    if src_cat == tgt_cat:
        return 1.0
    src_world = _parse_world(src_cat)
    tgt_world = _parse_world(tgt_cat)
    if src_world and tgt_world and src_world != tgt_world:
        return 0.85  # cross-world (T↔I)
    return 0.9  # different category, same world


def level_multiplier(src_level: int | None, tgt_level: int | None) -> float:
    """Multiplier based on source/target node levels."""
    if src_level is None or tgt_level is None:
        return 1.0
    pair = (src_level, tgt_level)
    if pair == (4, 4):
        return 1.0
    if pair == (3, 3):
        return 0.95
    if pair in ((2, 3), (3, 4)):
        return 0.90
    if pair in ((2, 2), (2, 4)):
        return 0.85
    # Any other combination — use a sensible default
    return 0.90


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def build_node_info(G) -> dict[str, dict]:
    """Build lookup: node_id → {category, level}."""
    info = {}
    for nid, attrs in G.nodes(data=True):
        info[nid] = {
            "category": attrs.get("category", ""),
            "level": attrs.get("level"),
        }
    return info


def compute_weight(edge_type: str, src_cat: str, tgt_cat: str,
                   src_level: int | None, tgt_level: int | None) -> float:
    """Compute calibrated weight for a single causal edge."""
    base = TYPE_DEFAULTS.get(edge_type, 0.50)
    w = base * cross_l1_multiplier(src_cat, tgt_cat) * level_multiplier(src_level, tgt_level)
    w = round(max(0.20, min(0.95, w)), 2)
    return w


def calibrate_file(path: Path, node_info: dict[str, dict], dry_run: bool = False) -> tuple[int, list[dict]]:
    """Calibrate weights in a single YAML file.

    Returns (edges_updated, list of {from, to, type, old_weight, new_weight}).
    """
    data = yaml.safe_load(path.read_text())
    if data is None:
        return 0, []

    edges = data.get("edges") or []
    updated = 0
    changes = []

    for edge in edges:
        etype = edge.get("type", "")
        if etype not in CAUSAL_TYPES:
            continue

        src = edge.get("from", "")
        tgt = edge.get("to", "")
        src_info = node_info.get(src, {})
        tgt_info = node_info.get(tgt, {})

        old_weight = edge.get("weight", 1.0)
        new_weight = compute_weight(
            etype,
            src_info.get("category", ""),
            tgt_info.get("category", ""),
            src_info.get("level"),
            tgt_info.get("level"),
        )

        changes.append({
            "from": src,
            "to": tgt,
            "type": etype,
            "old_weight": old_weight,
            "new_weight": new_weight,
        })

        if not dry_run:
            edge["weight"] = new_weight
            updated += 1

    if not dry_run and updated > 0:
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True))

    return updated if not dry_run else len(changes), changes


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def bucket_label(w: float) -> str:
    lo = int(w * 10) / 10
    return f"{lo:.1f}-{lo + 0.1:.1f}"


def print_distribution(label: str, weights: list[float]) -> None:
    """Print histogram by 0.1 buckets."""
    buckets: dict[str, int] = defaultdict(int)
    for w in weights:
        buckets[bucket_label(w)] += 1
    print(f"\n  {label} weight distribution ({len(weights)} edges):")
    for b in sorted(buckets.keys()):
        count = buckets[b]
        bar = "#" * count
        print(f"    {b}: {count:4d}  {bar}")


def print_type_averages(label: str, changes: list[dict], key: str) -> None:
    """Print average weight per edge type."""
    by_type: dict[str, list[float]] = defaultdict(list)
    for c in changes:
        by_type[c["type"]].append(c[key])
    print(f"\n  {label} average weight by type:")
    for t in sorted(by_type.keys()):
        vals = by_type[t]
        avg = sum(vals) / len(vals)
        print(f"    {t:16s}: {avg:.3f}  (n={len(vals)})")


def print_report(all_changes: list[dict]) -> None:
    """Print before/after comparison."""
    old_weights = [c["old_weight"] for c in all_changes]
    new_weights = [c["new_weight"] for c in all_changes]

    print_distribution("BEFORE", old_weights)
    print_distribution("AFTER", new_weights)
    print_type_averages("BEFORE", all_changes, "old_weight")
    print_type_averages("AFTER", all_changes, "new_weight")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply structural heuristic weight defaults to causal edges"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show distribution stats only, don't modify files")
    parser.add_argument("--report", action="store_true",
                        help="Show before/after comparison")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Load merged graph for node info lookup only
    merger = TaxonomyMerger()
    G = merger.merge(apply_patches=False)
    node_info = build_node_info(G)
    log.info("Loaded %d nodes from merged graph for lookup", len(node_info))

    all_changes: list[dict] = []
    total_updated = 0

    for fname in SOURCE_FILES:
        path = TAXONOMY_DIR / fname
        if not path.exists():
            log.warning("File not found, skipping: %s", path)
            continue

        count, changes = calibrate_file(path, node_info, dry_run=args.dry_run)
        all_changes.extend(changes)
        total_updated += count

        if count > 0:
            mode = "would update" if args.dry_run else "updated"
            print(f"  {fname}: {mode} {count} edges")

    print(f"\nTotal: {total_updated} causal edges {'analyzed' if args.dry_run else 'updated'}")

    if args.dry_run or args.report:
        print_report(all_changes)


if __name__ == "__main__":
    main()
