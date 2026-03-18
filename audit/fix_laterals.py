"""Fix lateral edges based on Gemini review feedback.

For each L1 with issues, sends the current edges + review feedback
back to Gemini and asks for corrected output.

Usage:
    python -m audit.fix_laterals I4 I2 I3 I6 I9    # fix specific L1s
    python -m audit.fix_laterals all                 # fix all flagged
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import yaml

OUTPUT_DIR = Path("taxonomy/eval_results")
LATERAL_DIR = Path("taxonomy/laterals")

# Review feedback per L1 from Gemini reviewer
REVIEW_FEEDBACK = {
    "I2": """INVALID:
- residential_power_supply → residential_water_supply (DEPENDS_ON, p=1): Direction/Type mismatch. Water depends on power, not the other way. Either reverse to residential_water_supply → residential_power_supply (DEPENDS_ON) or change to residential_power_supply → residential_water_supply (SUPPLIES).

QUESTIONABLE (fix these):
- piped_natural_gas → lpg_cylinder (AFFECTS, p=-1): Upgrade to DISRUPTS. PNG networks structurally cannibalize LPG usage.

MISSING (add these):
- residential_power_supply → electricity_tariff: Shortages drive reliance on expensive diesel backups.""",

    "I3": """QUESTIONABLE (upgrade ALL of these from AFFECTS to SUPPLIES — fuel is a physical input):
- retail_diesel → highway_bus_travel: change to SUPPLIES
- cng_fuel → auto_rickshaw_fare: change to SUPPLIES
- cng_fuel → cab_aggregator_fare: change to SUPPLIES
- retail_petrol → bike_taxi_fare: change to SUPPLIES
- ev_charging_tariff → e_rickshaw_fare: change to SUPPLIES
- road_potholes → vehicle_servicing_cost: change to PRODUCES (potholes generate damage)
- traffic_congestion → ride_hailing_services: change to PRODUCES (congestion produces surge pricing)

MISSING (add):
- traffic_congestion → auto_rickshaw_fare / cab_aggregator_fare (PRODUCES): increased ride time produces higher fares.""",

    "I4": """CRITICAL: 8 out of 13 edges targeted L2 category nodes, violating Rule 20 (NEVER TARGET L2).

INVALID — REMOVE ALL OF THESE:
- mgnrega_wages → agriculture_and_allied (L2 target)
- urban_unemployment_rate → delivery_and_logistics (L2 target)
- startup_ecosystem → delivery_and_logistics (L2 target)
- msme_manufacturing → manufacturing_and_core (L2 target)
- mgnrega_wages → construction_and_manual (L2 target)
- minimum_wage → msme_manufacturing (L2 target)
- startup_layoffs → freelance_and_services (L2 target)
- maternity_leave_benefits → manufacturing_and_core (L2 target)

REGENERATE the entire I4 batch from scratch. Target ONLY L3 and L4 nodes.
L3 examples: farm_labor_wages, gig_worker_payouts, factory_floor_jobs, it_sector_salary, domestic_help_wages
L4 examples: specific job types or wage entities

MISSING: minimum_wage → domestic_help_wages (PRODUCES)""",

    "I6": """INVALID (wrong polarity per Rule 1):
- diabetes → cardiovascular_health (AFFECTS, p=1): WRONG. If diabetes increases, cardiovascular health DECREASES. Fix to p=-1.
- cardiovascular_health → chronic_disease_medication (AFFECTS, p=1): WRONG. If cardiovascular health increases (improves), medication need DECREASES. Fix to p=-1.

QUESTIONABLE (upgrade edge types per Rule 12b):
- vector_borne_diseases → blood_tests: change AFFECTS to PRODUCES
- respiratory_infections → doctor_consultation: change AFFECTS to PRODUCES
- doctor_consultation → prescription_drugs: change AFFECTS to PRODUCES
- oncology → inpatient_care: change AFFECTS to PRODUCES
- pediatric_vaccines → respiratory_infections (AFFECTS, p=-1): change to DISRUPTS

MISSING:
- diagnostic_services → surgical_procedures (PRODUCES)""",

    "I7": """QUESTIONABLE (upgrade edge types per Rule 12b):
- test_prep_edtech → offline_coaching_centers (AFFECTS, p=-1): change to DISRUPTS
- k12_edtech → private_tutors (AFFECTS, p=-1): change to DISRUPTS
- educational_scholarships → undergraduate_programs (AFFECTS, p=1): change to FUNDS
- private_schools → school_fees: change to PRODUCES
- test_prep_industry → coaching_fees: change to PRODUCES

MISSING:
- coaching_fees → educational_loans (PRODUCES)""",

    "I9": """INVALID:
- street_garbage → open_drains (DISRUPTS, p=1): Polarity/Type conflict. If it disrupts drains, it reduces functionality, so p should be -1. Fix polarity to -1.

QUESTIONABLE (upgrade edge types):
- neighborhood_greenery → outdoor_heat (AFFECTS, p=-1): change to DISRUPTS
- neighborhood_greenery → particulate_matter_levels (AFFECTS, p=-1): change to DISRUPTS
- neighborhood_greenery → noise_pollution (AFFECTS, p=-1): change to DISRUPTS
- particulate_matter_levels → ambient_aqi (AFFECTS): change to PRODUCES

MISSING:
- winter_smog → ambient_aqi (PRODUCES)""",

    "I10": """QUESTIONABLE (upgrade edge types):
- mobile_network_quality → upi_transaction_success (AFFECTS): change to DEPENDS_ON (description says "essential for")
- mobile_network_quality → aadhaar_authentication (AFFECTS): change to DEPENDS_ON (description says "rely heavily on")
- personal_data_privacy → telemarketing_and_spam (AFFECTS, p=-1): change to DISRUPTS

MISSING:
- smartphone_device → upi_ecosystem (DEPENDS_ON)""",

    "I11": """QUESTIONABLE (upgrade edge types):
- digital_entertainment → cinema_and_theatre (AFFECTS, p=-1): change to DISRUPTS
- rwa_regulation → community_gathering (AFFECTS, p=-1): change to DISRUPTS
- rwa_regulation → festivals_and_celebrations (AFFECTS, p=-1): change to DISRUPTS
- festivals_and_celebrations → religious_pilgrimage (AFFECTS): change to PRODUCES
- festivals_and_celebrations → live_events (AFFECTS): change to PRODUCES

MISSING:
- tour_package → tourism_services (SUPPLIES/PRODUCES)""",

    "I1": """QUESTIONABLE (upgrade edge types):
- retail_onion → street_food (AFFECTS): change to SUPPLIES (physical input)
- retail_tomato → street_food (AFFECTS): change to SUPPLIES (physical input)

MISSING:
- wheat_flour → street_food (SUPPLIES): Maida/Atta base for samosas, kachoris, bhatures.""",
}


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


def extract_tree(G, l1_id: str) -> str:
    """Extract tree structure as text."""
    nodes_by_id = {}
    for n, d in sorted(G.nodes(data=True)):
        if d.get("category") != l1_id:
            continue
        nodes_by_id[n] = d

    lines = []
    def render(node_id, indent=0):
        d = nodes_by_id.get(node_id, {})
        prefix = "  " * indent
        cat = " [CATEGORY/L2]" if d.get("is_category") and d.get("level") == 2 else (" [CATEGORY]" if d.get("is_category") else "")
        aliases = d.get("aliases", [])[:2]
        alias_str = f" ({', '.join(aliases)})" if aliases else ""
        lines.append(f"{prefix}L{d.get('level','?')}: {node_id}{alias_str}{cat}")
        for succ in sorted(G.successors(node_id)):
            if G[node_id][succ].get("type") == "CONTAINS" and succ in nodes_by_id:
                render(succ, indent + 1)

    root = next((n for n, d in nodes_by_id.items() if d.get("level") == 1), None)
    if root:
        render(root)
    return "\n".join(lines)


def call_gemini(client, prompt: str, l1_id: str) -> tuple[str, str]:
    from google.genai import types
    chat = client.chats.create(
        model="gemini-3.1-pro-preview",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="high", include_thoughts=True),
            temperature=0.3,
        ),
    )

    print(f"\n{'='*60}")
    print(f"Fixing laterals for {l1_id} ({len(prompt)} chars)...")
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
        return "", ""

    answer, thinking = "", ""
    for part in response.candidates[0].content.parts:
        if part.thought:
            thinking += part.text + "\n"
        else:
            answer += part.text + "\n"

    usage = response.usage_metadata
    print(f"  Thinking: {usage.thoughts_token_count} tokens, Output: {usage.candidates_token_count} tokens")
    return answer.strip(), thinking.strip()


def parse_yaml_response(response: str) -> list[dict]:
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        edges = yaml.safe_load(text)
        return edges if isinstance(edges, list) else []
    except yaml.YAMLError as e:
        print(f"  YAML parse error: {e}")
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("l1s", nargs="+", help="L1 IDs or 'all'")
    args = parser.parse_args()

    from graph.merge import TaxonomyMerger
    from graph.migrate_weights import apply_defaults
    merger = TaxonomyMerger()
    G = merger.merge(apply_patches=False)
    apply_defaults(G)

    flagged = list(REVIEW_FEEDBACK.keys())
    targets = flagged if "all" in args.l1s else [l for l in args.l1s if l in flagged]

    if not targets:
        print(f"No feedback for: {args.l1s}. Flagged: {flagged}")
        return

    client = get_gemini_client()

    for l1_id in targets:
        feedback = REVIEW_FEEDBACK[l1_id]
        tree_text = extract_tree(G, l1_id)

        # Load current edges
        yaml_path = LATERAL_DIR / f"{l1_id.lower()}_laterals.yaml"
        current_edges = yaml.safe_load(yaml_path.read_text()) if yaml_path.exists() else []
        current_yaml = yaml.dump(current_edges, default_flow_style=False, sort_keys=False)

        is_regenerate = l1_id == "I4"

        if is_regenerate:
            prompt = f"""You are generating intra-L1 lateral edges for {l1_id} from scratch.

## Tree
```
{tree_text}
```

## CRITICAL RULES
- **NEVER target L2 nodes** (marked [CATEGORY/L2] or [CATEGORY] at level 2). These are organizational folders.
- **Target L3 or L4 ONLY.** L3 by default. L4 when only one child under an L3 is affected.
- Edge type priority: PRODUCES > SUPPLIES > FUNDS > DISRUPTS > DEPENDS_ON > AFFECTS (fallback)
- Weight = causal pass-through strength (0.3-1.0)
- Polarity: +1 (same direction) or -1 (opposite)
- Description must explain the causal MECHANISM

## Previous attempt feedback (this batch scored 2/10)
{feedback}

## Output
Return ONLY a YAML array of edges. No commentary. Target L3/L4 nodes only."""
        else:
            prompt = f"""You are fixing lateral edges for {l1_id} based on review feedback.

## Tree
```
{tree_text}
```

## Current edges
```yaml
{current_yaml}
```

## Review feedback (apply ALL fixes)
{feedback}

## Rules
- Edge type priority: PRODUCES > SUPPLIES > FUNDS > DISRUPTS > DEPENDS_ON > AFFECTS (fallback)
- Never target L2 nodes
- Polarity: +1 = same direction covariation, -1 = opposite
- Weight = causal pass-through strength

## Output
Return the COMPLETE corrected set of edges (including unchanged ones + fixes + additions). YAML array only, no commentary."""

        answer, thinking = call_gemini(client, prompt, l1_id)
        if not answer:
            print(f"  No response for {l1_id}")
            continue

        edges = parse_yaml_response(answer)
        print(f"  Parsed {len(edges)} edges")

        # Basic validation
        l2_nodes = {n for n, d in G.nodes(data=True) if d.get("category") == l1_id and d.get("level") == 2}
        valid = []
        for e in edges:
            dst = e.get("to", "")
            if dst in l2_nodes:
                print(f"  STILL INVALID: {e['from']}→{dst} targets L2")
            else:
                valid.append(e)

        # Save
        backup_path = LATERAL_DIR / f"{l1_id.lower()}_laterals.v1.yaml"
        if yaml_path.exists() and not backup_path.exists():
            backup_path.write_text(yaml_path.read_text())
            print(f"  Backed up original to {backup_path}")

        yaml_path.write_text(yaml.dump(valid, default_flow_style=False, sort_keys=False, allow_unicode=True))
        print(f"  Saved: {yaml_path} ({len(valid)} edges, was {len(current_edges)})")

        # Save raw
        raw_path = OUTPUT_DIR / f"laterals_{l1_id.lower()}_fix.md"
        raw_content = f"# {l1_id} Lateral Fix\n\nThinking:\n{thinking}\n\nResponse:\n```yaml\n{answer}\n```\n"
        raw_path.write_text(raw_content)

        time.sleep(2)


if __name__ == "__main__":
    main()
