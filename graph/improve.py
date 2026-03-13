"""Scorecard improvement pipeline — deterministic fixes + Gemini-verified content.

CLI usage:
    python3 -m graph.improve normalize-categories [--dry-run | --apply]
    python3 -m graph.improve normalize-edge-types [--dry-run | --apply]
    python3 -m graph.improve deduplicate [--dry-run | --apply]
    python3 -m graph.improve add-inference-nodes [--dry-run | --apply]
    python3 -m graph.improve generate-descriptions [--dry-run | --apply]
    python3 -m graph.improve generate-causal-edges [--dry-run | --apply]
    python3 -m graph.improve all-deterministic --apply   # 1A + 1B + 1C
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from graph.quality import CANONICAL_CATEGORIES, CANONICAL_EDGE_TYPES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_DIR = PROJECT_ROOT / "taxonomy"

FLAT_FILES = [
    "employment_domain_graph.yaml",
    "financial_system_domain_graph.yaml",
    "food_energy_graph.yaml",
    "local_governance_graph.yaml",
]
TREE_FILE = "universal_life_dependency_graph.yaml"
PATCH_FILE = "edge_patches.yaml"
GENERATED_PATCH_FILE = "edge_patches_generated.yaml"

ALL_SOURCE_FILES = FLAT_FILES + [TREE_FILE]

MODEL_NAME = "gemini-3.1-pro-preview"
BATCH_SIZE_NODES = 30
BATCH_SIZE_DESCRIPTIONS = 20
BATCH_SIZE_CAUSAL = 15
RATE_LIMIT_SLEEP = 2.0

# ---------------------------------------------------------------------------
# 1A. Category normalization mapping
# ---------------------------------------------------------------------------

CATEGORY_MAP: dict[str, str] = {
    "employment": "employment_and_income",
    "food": "food_and_agriculture",
    "food_and_nutrition": "food_and_agriculture",
    "food_policy": "food_and_agriculture",
    "agriculture_and_farming": "food_and_agriculture",
    "energy_and_fuel": "energy",
    "energy_policy": "energy",
    "housing_and_shelter": "housing",
    "property_land": "housing",
    "healthcare": "health_and_healthcare",
    "transport_and_mobility": "transport",
    "education_and_learning": "education",
    "financial_system": "financial",
    "local_governance": "governance_and_regulation",
    "municipal_governance": "governance_and_regulation",
    "state_policy": "governance_and_regulation",
    "law_order": "governance_and_regulation",
    "environment": "environment_and_climate",
    "climate": "environment_and_climate",
    "technology_and_innovation": "technology_and_telecom",
    "technology": "technology_and_telecom",
    "communication_and_information": "technology_and_telecom",
    "water_systems": "infrastructure",
    "water_infrastructure": "infrastructure",
    "utilities": "infrastructure",
    "industrial_metals_and_materials": "consumer_goods",
    "clothing_and_personal_care": "consumer_goods",
    "recreation_and_culture": "demographics_and_social",
    "safety_and_security": "demographics_and_social",
    "geopolitics": "global_economy",
    "global_macro_and_geopolitics": "global_economy",
    "macro": "global_economy",
    "cross_domain": "global_economy",
    "user": "demographics_and_social",
}

# ---------------------------------------------------------------------------
# 1B. Edge type normalization mapping
# ---------------------------------------------------------------------------

EDGE_TYPE_MAP: dict[str, str] = {
    "LOCATED_IN": "CONTAINS",
    "CONSUMES": "DEPENDS_ON",
    "BENCHMARKED_TO": "DEPENDS_ON",
    "CONNECTS": "AFFECTS",
}

# ---------------------------------------------------------------------------
# 1C. Primary file ownership for deduplication
# ---------------------------------------------------------------------------

CATEGORY_PRIMARY_FILE: dict[str, str] = {
    "food_and_agriculture": "food_energy_graph.yaml",
    "energy": "food_energy_graph.yaml",
    "employment_and_income": "employment_domain_graph.yaml",
    "financial": "financial_system_domain_graph.yaml",
    "governance_and_regulation": "local_governance_graph.yaml",
    "infrastructure": "local_governance_graph.yaml",
    "transport": "local_governance_graph.yaml",
    "housing": "local_governance_graph.yaml",
    "health_and_healthcare": "universal_life_dependency_graph.yaml",
    "education": "universal_life_dependency_graph.yaml",
    "consumer_goods": "universal_life_dependency_graph.yaml",
    "technology_and_telecom": "universal_life_dependency_graph.yaml",
    "environment_and_climate": "local_governance_graph.yaml",
    "demographics_and_social": "universal_life_dependency_graph.yaml",
    "global_economy": "financial_system_domain_graph.yaml",
}

# ---------------------------------------------------------------------------
# YAML I/O helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text())
    return data if data else {}


def _save_yaml(path: Path, data: dict, header: str = "") -> None:
    body = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    path.write_text(header + body)


def _load_output() -> dict:
    path = TAXONOMY_DIR / GENERATED_PATCH_FILE
    if path.exists():
        data = yaml.safe_load(path.read_text())
        if data:
            return data
    return {"edges": [], "description_fills": [], "new_nodes": []}


def _save_output(data: dict) -> None:
    header = (
        "# Auto-generated by graph/improve.py\n"
        "# Review before merging into production graph\n\n"
    )
    _save_yaml(TAXONOMY_DIR / GENERATED_PATCH_FILE, data, header)


# ---------------------------------------------------------------------------
# Gemini client (reuses patterns from llm_weights.py)
# ---------------------------------------------------------------------------


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from config import settings
            api_key = settings.gemini_api_key
        except Exception:
            pass
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY or GOOGLE_API_KEY.", file=sys.stderr)
        sys.exit(1)

    from google import genai
    return genai.Client(api_key=api_key)


def _call_gemini(client, prompt: str, max_retries: int = 5) -> str:
    from google import genai
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=genai.types.GenerateContentConfig(temperature=0.2),
            )
            return response.text
        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "overloaded" in err_str.lower():
                wait = (attempt + 1) * 5  # 5, 10, 15, 20, 25s
                print(f"  Gemini 503 — retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"Gemini unavailable after {max_retries} retries")


def _parse_json_response(text: str) -> Any:
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    for pattern in [r"\[[\s\S]*\]", r"\{[\s\S]*\}"]:
        match = re.search(pattern, cleaned)
        if match:
            candidate = re.sub(r",\s*([}\]])", r"\1", match.group(0))
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    print(f"WARNING: Could not parse JSON:\n{text[:500]}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Tree walker helpers
# ---------------------------------------------------------------------------

_TREE_SKIP_KEYS = {"id", "level", "type", "description", "aliases", "leaf", "universality", "meta"}


def _walk_tree_categories(node: dict, mapping: dict[str, str], stats: dict) -> None:
    """Recursively update category fields in a tree-structured YAML dict."""
    if not isinstance(node, dict):
        return
    cat = node.get("category")
    if cat and cat in mapping:
        stats["changed"] += 1
        node["category"] = mapping[cat]

    for key, val in node.items():
        if key in _TREE_SKIP_KEYS:
            continue
        if key == "children":
            if isinstance(val, dict):
                for _ck, cv in val.items():
                    if isinstance(cv, dict):
                        _walk_tree_categories(cv, mapping, stats)
        elif isinstance(val, dict):
            _walk_tree_categories(val, mapping, stats)


def _walk_tree_ids(node: dict, out: set[str]) -> None:
    """Recursively extract all 'id' fields from tree."""
    if not isinstance(node, dict):
        return
    if "id" in node:
        out.add(node["id"])
    for key, val in node.items():
        if key in _TREE_SKIP_KEYS:
            continue
        if key == "children":
            if isinstance(val, dict):
                for _ck, cv in val.items():
                    if isinstance(cv, dict):
                        _walk_tree_ids(cv, out)
        elif isinstance(val, dict):
            _walk_tree_ids(val, out)


def _walk_tree_remove_ids(node: dict, ids_to_remove: set[str]) -> int:
    """Remove nodes with given IDs from tree. Returns count removed."""
    if not isinstance(node, dict):
        return 0
    removed = 0
    keys_to_delete = []
    for key, val in node.items():
        if key in _TREE_SKIP_KEYS:
            continue
        if key == "children" and isinstance(val, dict):
            child_keys_to_delete = []
            for ck, cv in val.items():
                if isinstance(cv, dict) and cv.get("id") in ids_to_remove:
                    child_keys_to_delete.append(ck)
                    removed += 1
                elif isinstance(cv, dict):
                    removed += _walk_tree_remove_ids(cv, ids_to_remove)
            for ck in child_keys_to_delete:
                del val[ck]
        elif isinstance(val, dict) and val.get("id") in ids_to_remove:
            keys_to_delete.append(key)
            removed += 1
        elif isinstance(val, dict):
            removed += _walk_tree_remove_ids(val, ids_to_remove)
    for k in keys_to_delete:
        del node[k]
    return removed


# ---------------------------------------------------------------------------
# Mode 1A: normalize-categories
# ---------------------------------------------------------------------------


def run_normalize_categories(dry_run: bool = False, apply: bool = False) -> None:
    print("=== Normalize Categories ===")
    total_changed = 0

    for fname in FLAT_FILES:
        path = TAXONOMY_DIR / fname
        data = _load_yaml(path)
        changed = 0
        for node in data.get("nodes", []) or []:
            cat = node.get("category", "")
            if cat in CATEGORY_MAP:
                if dry_run:
                    print(f"  {fname}: {node['id']}: {cat} -> {CATEGORY_MAP[cat]}")
                node["category"] = CATEGORY_MAP[cat]
                changed += 1
        if changed:
            print(f"  {fname}: {changed} categories to remap")
            total_changed += changed
            if apply:
                _save_yaml(path, data)

    # Tree file — categories are set by L1 key names in merge.py, but nodes
    # may store explicit category fields (rare in this tree, but handle it)
    tree_path = TAXONOMY_DIR / TREE_FILE
    tree_data = _load_yaml(tree_path)
    stats = {"changed": 0}
    _walk_tree_categories(tree_data, CATEGORY_MAP, stats)
    if stats["changed"]:
        print(f"  {TREE_FILE}: {stats['changed']} categories to remap")
        total_changed += stats["changed"]
        if apply:
            _save_yaml(tree_path, tree_data)

    # Patch file
    patch_path = TAXONOMY_DIR / PATCH_FILE
    patch_data = _load_yaml(patch_path)
    changed = 0
    for node in patch_data.get("new_nodes", []) or []:
        cat = node.get("category", "")
        if cat in CATEGORY_MAP:
            node["category"] = CATEGORY_MAP[cat]
            changed += 1
    if changed:
        print(f"  {PATCH_FILE}: {changed} categories to remap")
        total_changed += changed
        if apply:
            _save_yaml(patch_path, patch_data)

    print(f"Total: {total_changed} category remaps")
    if apply:
        print("Applied.")
    elif not dry_run:
        print("Use --apply to write changes.")


# ---------------------------------------------------------------------------
# Mode 1B: normalize-edge-types
# ---------------------------------------------------------------------------


def run_normalize_edge_types(dry_run: bool = False, apply: bool = False) -> None:
    print("=== Normalize Edge Types ===")
    total_changed = 0

    for fname in FLAT_FILES + [PATCH_FILE]:
        path = TAXONOMY_DIR / fname
        data = _load_yaml(path)
        changed = 0
        for edge in data.get("edges", []) or []:
            etype = edge.get("type", "")
            if etype in EDGE_TYPE_MAP:
                if dry_run:
                    print(f"  {fname}: {edge['from']}->{edge['to']}: {etype} -> {EDGE_TYPE_MAP[etype]}")
                edge["type"] = EDGE_TYPE_MAP[etype]
                changed += 1
        if changed:
            print(f"  {fname}: {changed} edge types to remap")
            total_changed += changed
            if apply:
                _save_yaml(path, data)

    # Generated patch file
    gen_path = TAXONOMY_DIR / GENERATED_PATCH_FILE
    if gen_path.exists():
        gen_data = _load_yaml(gen_path)
        changed = 0
        for edge in gen_data.get("edges", []) or []:
            etype = edge.get("type", "")
            if etype in EDGE_TYPE_MAP:
                edge["type"] = EDGE_TYPE_MAP[etype]
                changed += 1
        if changed:
            print(f"  {GENERATED_PATCH_FILE}: {changed} edge types to remap")
            total_changed += changed
            if apply:
                _save_output(gen_data)

    print(f"Total: {total_changed} edge type remaps")
    if apply:
        print("Applied.")
    elif not dry_run:
        print("Use --apply to write changes.")


# ---------------------------------------------------------------------------
# Mode 1C: deduplicate
# ---------------------------------------------------------------------------


def run_deduplicate(dry_run: bool = False, apply: bool = False) -> None:
    print("=== Cross-File Deduplication ===")

    # Build node -> [files] map
    node_files: dict[str, list[str]] = defaultdict(list)

    for fname in FLAT_FILES:
        path = TAXONOMY_DIR / fname
        data = _load_yaml(path)
        for node in data.get("nodes", []) or []:
            node_files[node["id"]].append(fname)

    # Tree file IDs
    tree_path = TAXONOMY_DIR / TREE_FILE
    tree_data = _load_yaml(tree_path)
    tree_ids: set[str] = set()
    _walk_tree_ids(tree_data, tree_ids)
    for nid in tree_ids:
        node_files[nid].append(TREE_FILE)

    # Find overlaps
    overlaps = {nid: files for nid, files in node_files.items() if len(files) > 1}
    if not overlaps:
        print("No overlapping nodes found.")
        return

    print(f"Found {len(overlaps)} overlapping nodes")

    # Determine primary file for each node and remove from secondaries
    removals: dict[str, list[str]] = defaultdict(list)  # file -> [node_ids to remove]

    for nid, files in overlaps.items():
        # Get the node's category (need to look it up)
        cat = _lookup_node_category(nid, files)
        primary = CATEGORY_PRIMARY_FILE.get(cat, files[0])
        if primary not in files:
            primary = files[0]
        for f in files:
            if f != primary:
                removals[f].append(nid)

    for fname, ids in removals.items():
        print(f"  {fname}: remove {len(ids)} duplicate nodes")
        if dry_run:
            for nid in ids[:5]:
                print(f"    - {nid}")
            if len(ids) > 5:
                print(f"    ... and {len(ids) - 5} more")

    if apply:
        for fname, ids in removals.items():
            ids_set = set(ids)
            if fname == TREE_FILE:
                removed = _walk_tree_remove_ids(tree_data, ids_set)
                _save_yaml(tree_path, tree_data)
                print(f"  Removed {removed} from {TREE_FILE}")
            else:
                path = TAXONOMY_DIR / fname
                data = _load_yaml(path)
                before = len(data.get("nodes", []))
                data["nodes"] = [n for n in data.get("nodes", []) if n["id"] not in ids_set]
                after = len(data["nodes"])
                _save_yaml(path, data)
                print(f"  Removed {before - after} from {fname}")
        print("Applied.")
    elif not dry_run:
        print("Use --apply to write changes.")


def _lookup_node_category(nid: str, files: list[str]) -> str:
    """Look up a node's category from its source files."""
    for fname in files:
        path = TAXONOMY_DIR / fname
        data = _load_yaml(path)
        if fname == TREE_FILE:
            # For tree files, we need the L1 key which becomes the category in merge
            # Just return a reasonable default
            continue
        for node in data.get("nodes", []) or []:
            if node["id"] == nid:
                cat = node.get("category", "")
                # Apply category mapping if non-canonical
                return CATEGORY_MAP.get(cat, cat)
    return ""


# ---------------------------------------------------------------------------
# Mode 2A: add-inference-nodes (Gemini-verified)
# ---------------------------------------------------------------------------


def run_add_inference_nodes(dry_run: bool = False, apply: bool = False) -> None:
    print("=== Add Missing Inference Nodes ===")

    from graph.merge import TaxonomyMerger
    from graph.quality import QualityAnalyzer

    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()
    validation = QualityAnalyzer._validate_inference_refs(G)

    missing = validation.missing_nodes
    if not missing:
        print("No missing inference nodes.")
        return

    print(f"Missing inference nodes: {len(missing)}")

    # Check which are already in generated patches
    output_data = _load_output()
    existing_ids = {n["id"] for n in output_data.get("new_nodes", [])}
    remaining = [nid for nid in missing if nid not in existing_ids]

    if not remaining:
        print(f"All {len(missing)} already in generated patches.")
        return

    print(f"Already generated: {len(missing) - len(remaining)}")
    print(f"Remaining: {len(remaining)}")

    if dry_run:
        batches = [remaining[i:i + BATCH_SIZE_NODES] for i in range(0, len(remaining), BATCH_SIZE_NODES)]
        for i, batch in enumerate(batches, 1):
            print(f"\n--- Batch {i}/{len(batches)} ({len(batch)} nodes) ---")
            print(f"  {', '.join(batch[:10])}")
        return

    canonical_cats = sorted(CANONICAL_CATEGORIES)
    canonical_types = sorted(CANONICAL_EDGE_TYPES - {"CONTAINS", "IS_A"})
    client = _get_client()

    batches = [remaining[i:i + BATCH_SIZE_NODES] for i in range(0, len(remaining), BATCH_SIZE_NODES)]
    for i, batch in enumerate(batches, 1):
        print(f"Batch {i}/{len(batches)}: generating {len(batch)} node definitions...")

        prompt = f"""You are an expert on Indian governance, infrastructure, and economy.

For each node_id below, generate:
1. aliases: 3+ human-readable names (including abbreviations Indians commonly use)
2. category: STRICTLY one of {json.dumps(canonical_cats)}
3. edges: 1-2 causal edges connecting this node to the broader Indian economy graph.
   Edge types must be one of: {json.dumps(canonical_types)}

Node IDs to define:
{json.dumps(batch)}

Output ONLY a JSON array:
[{{"id": "...", "aliases": ["..."], "category": "...", "edges": [{{"from": "...", "to": "...", "type": "...", "description": "...", "weight": 0.7, "polarity": 1, "delay": "SHORT_TERM"}}]}}]

Return valid JSON only. No markdown, no explanation."""

        try:
            response = _call_gemini(client, prompt)
            parsed = _parse_json_response(response)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            time.sleep(RATE_LIMIT_SLEEP)
            continue

        if not parsed or not isinstance(parsed, list):
            print(f"  WARNING: Could not parse batch {i}")
            time.sleep(RATE_LIMIT_SLEEP)
            continue

        for item in parsed:
            if not isinstance(item, dict):
                continue
            nid = item.get("id", "")
            aliases = item.get("aliases", [])
            cat = item.get("category", "")
            edges = item.get("edges", [])

            # Validate category
            if cat not in CANONICAL_CATEGORIES:
                cat = CATEGORY_MAP.get(cat, "demographics_and_social")

            if nid and nid not in existing_ids:
                output_data.setdefault("new_nodes", []).append({
                    "id": nid,
                    "aliases": aliases,
                    "category": cat,
                })
                existing_ids.add(nid)

            # Add edges
            for edge in edges:
                if isinstance(edge, dict) and edge.get("from") and edge.get("to"):
                    etype = edge.get("type", "AFFECTS")
                    if etype not in CANONICAL_EDGE_TYPES:
                        etype = EDGE_TYPE_MAP.get(etype, "AFFECTS")
                    output_data.setdefault("edges", []).append({
                        "from": edge["from"],
                        "to": edge["to"],
                        "type": etype,
                        "description": edge.get("description", ""),
                        "weight": edge.get("weight", 0.7),
                        "polarity": edge.get("polarity", 1),
                        "delay": edge.get("delay", "SHORT_TERM"),
                    })

        _save_output(output_data)
        print(f"  Saved. Total new_nodes: {len(output_data.get('new_nodes', []))}")
        time.sleep(RATE_LIMIT_SLEEP)

    print(f"\nDone. {len(output_data.get('new_nodes', []))} total new nodes in {GENERATED_PATCH_FILE}")


# ---------------------------------------------------------------------------
# Mode 3A: generate-descriptions
# ---------------------------------------------------------------------------

TEMPLATE_DESCRIPTIONS: dict[str, str] = {
    "CONTAINS": "{from_id} contains {to_id} as a subcategory",
    "IS_A": "{to_id} is a type of {from_id}",
}


def run_generate_descriptions(dry_run: bool = False, apply: bool = False) -> None:
    print("=== Generate Edge Descriptions ===")

    from graph.merge import TaxonomyMerger
    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()

    # Find edges without descriptions
    edges_missing: list[dict] = []
    template_fills: list[dict] = []

    for src, dst, attrs in G.edges(data=True):
        desc = attrs.get("description", "")
        if desc:
            continue
        etype = attrs.get("type", "")
        if etype in TEMPLATE_DESCRIPTIONS:
            template_fills.append({
                "from": src,
                "to": dst,
                "description": TEMPLATE_DESCRIPTIONS[etype].format(from_id=src, to_id=dst),
            })
        else:
            edges_missing.append({
                "from": src,
                "to": dst,
                "type": etype,
            })

    print(f"Template-fillable (IS_A/CONTAINS): {len(template_fills)}")
    print(f"Causal edges needing Gemini: {len(edges_missing)}")

    output_data = _load_output()

    # Check already filled
    filled_keys = {(f["from"], f["to"]) for f in output_data.get("description_fills", [])}
    template_new = [f for f in template_fills if (f["from"], f["to"]) not in filled_keys]
    causal_remaining = [e for e in edges_missing if (e["from"], e["to"]) not in filled_keys]

    print(f"Template fills remaining: {len(template_new)}")
    print(f"Causal remaining: {len(causal_remaining)}")

    # Apply template fills immediately
    for fill in template_new:
        output_data.setdefault("description_fills", []).append(fill)
        filled_keys.add((fill["from"], fill["to"]))

    if template_new:
        _save_output(output_data)
        print(f"Wrote {len(template_new)} template descriptions")

    if not causal_remaining:
        print("No causal edges need Gemini generation.")
        return

    if dry_run:
        batches = [causal_remaining[i:i + BATCH_SIZE_DESCRIPTIONS]
                    for i in range(0, len(causal_remaining), BATCH_SIZE_DESCRIPTIONS)]
        for i, batch in enumerate(batches, 1):
            print(f"--- Batch {i}/{len(batches)} ({len(batch)} edges) ---")
        return

    # Build node lookup for context
    node_lookup = {}
    for nid, attrs in G.nodes(data=True):
        node_lookup[nid] = {
            "aliases": attrs.get("aliases", []),
            "category": attrs.get("category", ""),
        }

    client = _get_client()
    batches = [causal_remaining[i:i + BATCH_SIZE_DESCRIPTIONS]
                for i in range(0, len(causal_remaining), BATCH_SIZE_DESCRIPTIONS)]

    for i, batch in enumerate(batches, 1):
        print(f"Batch {i}/{len(batches)}: {len(batch)} edges...")

        edges_json = []
        for edge in batch:
            src_info = node_lookup.get(edge["from"], {})
            dst_info = node_lookup.get(edge["to"], {})
            edges_json.append({
                "from": edge["from"],
                "from_aliases": src_info.get("aliases", [])[:3],
                "to": edge["to"],
                "to_aliases": dst_info.get("aliases", [])[:3],
                "type": edge["type"],
            })

        prompt = f"""You are an expert on Indian governance, infrastructure, and economy.

For each edge, write a concise 1-2 sentence description of the causal relationship. Be specific to India.

Return ONLY JSON array: [{{"from": "...", "to": "...", "description": "..."}}]

Edges:
{json.dumps(edges_json, indent=2)}

Return valid JSON only."""

        try:
            response = _call_gemini(client, prompt)
            parsed = _parse_json_response(response)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            time.sleep(RATE_LIMIT_SLEEP)
            continue

        if not parsed or not isinstance(parsed, list):
            print(f"  WARNING: parse failed for batch {i}")
            time.sleep(RATE_LIMIT_SLEEP)
            continue

        added = 0
        for item in parsed:
            if not isinstance(item, dict):
                continue
            src = item.get("from", "")
            dst = item.get("to", "")
            desc = item.get("description", "")
            if src and dst and desc and (src, dst) not in filled_keys:
                output_data.setdefault("description_fills", []).append({
                    "from": src, "to": dst, "description": desc,
                })
                filled_keys.add((src, dst))
                added += 1

        _save_output(output_data)
        print(f"  +{added} descriptions")
        time.sleep(RATE_LIMIT_SLEEP)

    total = len(output_data.get("description_fills", []))
    print(f"\nDone. {total} total description fills in {GENERATED_PATCH_FILE}")


# ---------------------------------------------------------------------------
# Mode 3B: generate-causal-edges
# ---------------------------------------------------------------------------


def run_generate_causal_edges(dry_run: bool = False, apply: bool = False) -> None:
    print("=== Generate Causal Edges for Dead-Ends ===")

    from graph.merge import TaxonomyMerger
    from graph.traverse import CAUSAL_TYPES, TAXONOMY_TYPES

    merger = TaxonomyMerger(root=PROJECT_ROOT)
    G = merger.merge()

    # Find dead-end nodes (only taxonomy edges)
    dead_ends: list[str] = []
    for node in G.nodes():
        has_causal = False
        for succ in G.successors(node):
            if G.edges[node, succ].get("type") not in TAXONOMY_TYPES:
                has_causal = True
                break
        if not has_causal:
            for pred in G.predecessors(node):
                if G.edges[pred, node].get("type") not in TAXONOMY_TYPES:
                    has_causal = True
                    break
        if not has_causal:
            dead_ends.append(node)

    print(f"Dead-end nodes: {len(dead_ends)}")

    output_data = _load_output()

    # Filter already addressed
    existing_edge_nodes = set()
    for edge in output_data.get("edges", []):
        existing_edge_nodes.add(edge["from"])
        existing_edge_nodes.add(edge["to"])

    remaining = [n for n in dead_ends if n not in existing_edge_nodes]
    print(f"Already addressed: {len(dead_ends) - len(remaining)}")
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        return

    if dry_run:
        batches = [remaining[i:i + BATCH_SIZE_CAUSAL]
                    for i in range(0, len(remaining), BATCH_SIZE_CAUSAL)]
        for i, batch in enumerate(batches, 1):
            print(f"--- Batch {i}/{len(batches)} ({len(batch)} nodes): {', '.join(batch[:5])}...")
        return

    canonical_types = sorted(CAUSAL_TYPES)
    client = _get_client()
    batches = [remaining[i:i + BATCH_SIZE_CAUSAL]
                for i in range(0, len(remaining), BATCH_SIZE_CAUSAL)]

    for i, batch in enumerate(batches, 1):
        print(f"Batch {i}/{len(batches)}: {len(batch)} dead-end nodes...")

        # Build context: nearby well-connected nodes
        context = []
        for nid in batch:
            node_attrs = G.nodes.get(nid, {})
            cat = node_attrs.get("category", "")
            nearby = []
            for other_nid, other_attrs in G.nodes(data=True):
                if other_nid == nid:
                    continue
                if other_attrs.get("category") == cat and G.degree(other_nid) > 2:
                    nearby.append({"id": other_nid, "aliases": other_attrs.get("aliases", [])[:2]})
                    if len(nearby) >= 5:
                        break
            context.append({
                "node_id": nid,
                "aliases": node_attrs.get("aliases", [])[:3],
                "category": cat,
                "nearby_nodes": nearby,
            })

        prompt = f"""You are an expert on Indian governance, infrastructure, and economy.

For each dead-end node below, suggest 1-2 causal edges connecting it to the broader graph.
Use types: {json.dumps(canonical_types)}
Each edge: from, to, type, description, weight (0.2/0.4/0.7/0.9), polarity (-1/0/1), delay (IMMEDIATE/SHORT_TERM/MEDIUM_TERM/LONG_TERM).

Nodes:
{json.dumps(context, indent=2)}

Return ONLY JSON array of edge objects. No markdown."""

        try:
            response = _call_gemini(client, prompt)
            parsed = _parse_json_response(response)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            time.sleep(RATE_LIMIT_SLEEP)
            continue

        if not parsed or not isinstance(parsed, list):
            print(f"  WARNING: parse failed for batch {i}")
            time.sleep(RATE_LIMIT_SLEEP)
            continue

        added = 0
        for item in parsed:
            if not isinstance(item, dict):
                continue
            src = item.get("from", "")
            dst = item.get("to", "")
            etype = item.get("type", "AFFECTS")
            desc = item.get("description", "")
            if not src or not dst or not desc:
                continue
            if etype not in CANONICAL_EDGE_TYPES:
                etype = EDGE_TYPE_MAP.get(etype, "AFFECTS")
            output_data.setdefault("edges", []).append({
                "from": src,
                "to": dst,
                "type": etype,
                "description": desc,
                "weight": item.get("weight", 0.4),
                "polarity": item.get("polarity", 0),
                "delay": item.get("delay", "SHORT_TERM"),
            })
            added += 1

        _save_output(output_data)
        print(f"  +{added} edges")
        time.sleep(RATE_LIMIT_SLEEP)

    total = len(output_data.get("edges", []))
    print(f"\nDone. {total} total generated edges in {GENERATED_PATCH_FILE}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Improve graph quality scorecard dimensions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "mode",
        choices=[
            "normalize-categories",
            "normalize-edge-types",
            "deduplicate",
            "add-inference-nodes",
            "generate-descriptions",
            "generate-causal-edges",
            "all-deterministic",
        ],
        help="Improvement mode to run",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--apply", action="store_true", help="Apply changes to source files")
    args = parser.parse_args()

    if args.dry_run and args.apply:
        print("ERROR: Cannot use both --dry-run and --apply", file=sys.stderr)
        sys.exit(1)

    MODE_MAP = {
        "normalize-categories": run_normalize_categories,
        "normalize-edge-types": run_normalize_edge_types,
        "deduplicate": run_deduplicate,
        "add-inference-nodes": run_add_inference_nodes,
        "generate-descriptions": run_generate_descriptions,
        "generate-causal-edges": run_generate_causal_edges,
    }

    if args.mode == "all-deterministic":
        for mode_name in ["normalize-categories", "normalize-edge-types", "deduplicate"]:
            print()
            MODE_MAP[mode_name](dry_run=args.dry_run, apply=args.apply)
    else:
        MODE_MAP[args.mode](dry_run=args.dry_run, apply=args.apply)


if __name__ == "__main__":
    main()
