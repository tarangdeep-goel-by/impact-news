"""Inference engine: maps questionnaire answers to graph nodes."""

from __future__ import annotations

from graph.graph import ImpactGraph
from models import UserEdge, UserGraph

# ---------------------------------------------------------------------------
# City → graph-node mappings (20 Indian cities)
# ---------------------------------------------------------------------------

CITY_GRAPH_MAP = {
    "bangalore": {
        "direct": ["bangalore", "karnataka"],
        "municipal": ["bbmp"],
        "electricity": ["bescom"],
        "water": ["bwssb", "cauvery_water"],
        "transport": ["bmrcl", "bmtc"],
        "climate": ["tropical_climate", "monsoon"],
        "economy": ["it_services_sector"],
    },
    "mumbai": {
        "direct": ["mumbai", "maharashtra"],
        "municipal": ["mcgm"],
        "electricity": ["msedcl"],
        "water": ["mumbai_water"],
        "transport": ["mumbai_metro", "mumbai_local_trains"],
        "climate": ["tropical_climate", "monsoon", "coastal_flooding"],
        "economy": ["financial_services"],
    },
    "delhi": {
        "direct": ["delhi", "ncr"],
        "municipal": ["mcd"],
        "electricity": ["bses", "tata_power_delhi"],
        "water": ["delhi_jal_board"],
        "transport": ["delhi_metro", "dtc"],
        "climate": ["extreme_heat", "winter_fog", "air_pollution"],
        "economy": ["government_employment", "retail_sector"],
    },
    "hyderabad": {
        "direct": ["hyderabad", "telangana"],
        "municipal": ["ghmc"],
        "electricity": ["tsspdcl"],
        "water": ["hmwssb"],
        "transport": ["hyderabad_metro", "tsrtc"],
        "climate": ["tropical_climate", "monsoon"],
        "economy": ["it_services_sector", "pharma_sector"],
    },
    "chennai": {
        "direct": ["chennai", "tamil_nadu"],
        "municipal": ["gcc"],
        "electricity": ["tangedco"],
        "water": ["chennai_metro_water"],
        "transport": ["chennai_metro", "mtc"],
        "climate": ["tropical_climate", "monsoon", "coastal_flooding", "cyclone_risk"],
        "economy": ["manufacturing_sector", "it_services_sector"],
    },
    "pune": {
        "direct": ["pune", "maharashtra"],
        "municipal": ["pmc"],
        "electricity": ["msedcl"],
        "water": ["pune_water"],
        "transport": ["pune_metro", "pmpml"],
        "climate": ["tropical_climate", "monsoon"],
        "economy": ["it_services_sector", "manufacturing_sector"],
    },
    "kolkata": {
        "direct": ["kolkata", "west_bengal"],
        "municipal": ["kmc"],
        "electricity": ["cesc"],
        "water": ["kolkata_water"],
        "transport": ["kolkata_metro", "kolkata_tram"],
        "climate": ["tropical_climate", "monsoon", "cyclone_risk"],
        "economy": ["financial_services", "retail_sector"],
    },
    "ahmedabad": {
        "direct": ["ahmedabad", "gujarat"],
        "municipal": ["amc"],
        "electricity": ["torrent_power"],
        "water": ["ahmedabad_water"],
        "transport": ["ahmedabad_metro", "amts"],
        "climate": ["extreme_heat", "monsoon"],
        "economy": ["manufacturing_sector", "retail_sector"],
    },
    "jaipur": {
        "direct": ["jaipur", "rajasthan"],
        "municipal": ["jmc"],
        "electricity": ["jvvnl"],
        "water": ["jaipur_water"],
        "transport": ["jaipur_metro", "jctsl"],
        "climate": ["extreme_heat", "arid_climate"],
        "economy": ["hospitality_tourism_sector", "retail_sector"],
    },
    "lucknow": {
        "direct": ["lucknow", "uttar_pradesh"],
        "municipal": ["lmc"],
        "electricity": ["lesa"],
        "water": ["lucknow_water"],
        "transport": ["lucknow_metro", "upsrtc"],
        "climate": ["extreme_heat", "monsoon", "winter_fog"],
        "economy": ["government_employment"],
    },
    "chandigarh": {
        "direct": ["chandigarh", "punjab", "haryana"],
        "municipal": ["chandigarh_mc"],
        "electricity": ["chandigarh_electricity"],
        "water": ["chandigarh_water"],
        "transport": ["chandigarh_ctu"],
        "climate": ["extreme_heat", "winter_fog"],
        "economy": ["government_employment"],
    },
    "kochi": {
        "direct": ["kochi", "kerala"],
        "municipal": ["kochi_corporation"],
        "electricity": ["kseb"],
        "water": ["kochi_water"],
        "transport": ["kochi_metro", "ksrtc_kerala"],
        "climate": ["tropical_climate", "monsoon", "coastal_flooding"],
        "economy": ["hospitality_tourism_sector", "it_services_sector"],
    },
    "indore": {
        "direct": ["indore", "madhya_pradesh"],
        "municipal": ["imc"],
        "electricity": ["mpmkvvcl"],
        "water": ["indore_water"],
        "transport": ["indore_transport"],
        "climate": ["extreme_heat", "monsoon"],
        "economy": ["manufacturing_sector", "retail_sector"],
    },
    "bhopal": {
        "direct": ["bhopal", "madhya_pradesh"],
        "municipal": ["bhopal_mc"],
        "electricity": ["mpmkvvcl"],
        "water": ["bhopal_water"],
        "transport": ["bhopal_transport"],
        "climate": ["extreme_heat", "monsoon"],
        "economy": ["government_employment"],
    },
    "patna": {
        "direct": ["patna", "bihar"],
        "municipal": ["patna_mc"],
        "electricity": ["sbpdcl"],
        "water": ["patna_water"],
        "transport": ["patna_transport"],
        "climate": ["extreme_heat", "monsoon", "flood_risk"],
        "economy": ["agriculture_sector", "government_employment"],
    },
    "guwahati": {
        "direct": ["guwahati", "assam"],
        "municipal": ["gmda"],
        "electricity": ["apdcl"],
        "water": ["guwahati_water"],
        "transport": ["guwahati_transport"],
        "climate": ["tropical_climate", "monsoon", "flood_risk"],
        "economy": ["agriculture_sector"],
    },
    "thiruvananthapuram": {
        "direct": ["thiruvananthapuram", "kerala"],
        "municipal": ["tvm_corporation"],
        "electricity": ["kseb"],
        "water": ["tvm_water"],
        "transport": ["ksrtc_kerala"],
        "climate": ["tropical_climate", "monsoon", "coastal_flooding"],
        "economy": ["government_employment", "it_services_sector"],
    },
    "coimbatore": {
        "direct": ["coimbatore", "tamil_nadu"],
        "municipal": ["coimbatore_corporation"],
        "electricity": ["tangedco"],
        "water": ["coimbatore_water"],
        "transport": ["coimbatore_transport"],
        "climate": ["tropical_climate", "monsoon"],
        "economy": ["manufacturing_sector"],
    },
    "visakhapatnam": {
        "direct": ["visakhapatnam", "andhra_pradesh"],
        "municipal": ["gvmc"],
        "electricity": ["apspdcl"],
        "water": ["vizag_water"],
        "transport": ["vizag_transport"],
        "climate": ["tropical_climate", "monsoon", "cyclone_risk", "coastal_flooding"],
        "economy": ["manufacturing_sector"],
    },
    "nagpur": {
        "direct": ["nagpur", "maharashtra"],
        "municipal": ["nmc"],
        "electricity": ["msedcl"],
        "water": ["nagpur_water"],
        "transport": ["nagpur_metro", "nagpur_transport"],
        "climate": ["extreme_heat", "monsoon"],
        "economy": ["manufacturing_sector", "retail_sector"],
    },
}

# ---------------------------------------------------------------------------
# Tier 1: Question → graph-node maps
# Each entry: (node_id, relation, importance)
# ---------------------------------------------------------------------------

EMPLOYMENT_TYPE_MAP: dict[str, list[tuple[str, str, float]]] = {
    "salaried_private": [("income_tax", "pays", 0.7), ("epf", "contributes_to", 0.6)],
    "salaried_govt": [("government_employment", "works_in", 0.9), ("pay_commission", "affected_by", 0.8), ("nps", "contributes_to", 0.6), ("pension_policy", "eligible_for", 0.7)],
    "self_employed": [("business_income", "earns", 0.9), ("gst", "pays", 0.8), ("business_loan", "may_need", 0.6), ("business_loan", "part_of", 0.7)],
    "freelance": [("gig_workers", "works_in", 0.9), ("platform_economy", "depends_on", 0.7), ("income_volatility", "exposed_to", 0.8)],
    "student": [("education_sector", "part_of", 0.8), ("education_loan", "may_need", 0.6), ("job_market_india", "entering", 0.7)],
    "retired": [("pension_policy", "receives", 0.9), ("fd_rates", "invests_in", 0.6)],
    "homemaker": [("consumer", "is", 0.8), ("food_inflation_india", "affected_by", 0.7)],
}

INDUSTRY_MAP: dict[str, list[tuple[str, str, float]]] = {
    "IT": [("it_services_sector", "works_in", 1.0), ("skill_obsolescence", "exposed_to", 0.7), ("us_economy", "depends_on", 0.6), ("ai_job_displacement", "exposed_to", 0.7)],
    "Banking": [("banking", "works_in", 1.0), ("banking_regulation", "regulated_by", 0.8), ("repo_rate", "affected_by", 0.9), ("fintech", "competes_with", 0.5)],
    "Healthcare": [("health_and_healthcare", "works_in", 1.0), ("pharma_sector", "depends_on", 0.7), ("health_insurance", "provides", 0.6)],
    "Manufacturing": [("manufacturing_sector", "works_in", 1.0), ("state_economic_policy", "regulated_by", 0.7), ("logistics_sector", "depends_on", 0.6)],
    "Education": [("education_sector", "works_in", 1.0), ("education_policy", "regulated_by", 0.8), ("edtech_sector", "competes_with", 0.5)],
    "Government": [("government_employment", "works_in", 1.0), ("pay_commission", "affected_by", 0.9), ("union_budget", "affected_by", 0.8)],
    "Retail": [("retail_sector", "works_in", 1.0), ("consumer", "depends_on", 0.7), ("ecommerce_sector", "competes_with", 0.6)],
    "Startups": [("startup_policy", "works_in", 1.0), ("vc_funding_india", "funded_by", 0.8), ("angel_tax", "affected_by", 0.7), ("ai_job_displacement", "exposed_to", 0.6)],
    "Agriculture": [("agriculture_sector", "works_in", 1.0), ("monsoon", "depends_on", 0.9), ("crop_insurance", "uses", 0.7), ("price_controls", "affected_by", 0.8)],
    "Consulting": [("consulting_sector", "works_in", 1.0), ("us_economy", "depends_on", 0.5)],
    "Media": [("media_entertainment", "works_in", 1.0)],
    "Real_Estate": [("real_estate_sector", "works_in", 1.0), ("property_price", "affected_by", 0.9), ("rera", "regulated_by", 0.7)],
    "Pharma": [("pharma_sector", "works_in", 1.0), ("drug_pricing", "affected_by", 0.8), ("health_and_healthcare", "serves", 0.6)],
    "Telecom": [("telecom_sector", "works_in", 1.0), ("spectrum_policy", "affected_by", 0.7), ("broadband_internet", "provides", 0.6)],
    "Other": [],
}

HOUSING_MAP: dict[str, list[tuple[str, str, float]]] = {
    "own_loan": [("home_loan", "has", 1.0), ("repo_rate", "sensitive_to", 0.9), ("property_tax", "pays", 0.7), ("real_estate_sector", "owns", 0.6)],
    "own_clear": [("property_tax", "pays", 0.7), ("real_estate_sector", "owns", 0.6)],
    "rent": [("rental_market", "uses", 0.8), ("rental_housing", "affected_by", 0.7)],
    "family": [],
}

TRANSPORT_MAP: dict[str, list[tuple[str, str, float]]] = {
    "car": [("petrol", "affected_by", 0.9), ("diesel", "affected_by", 0.8), ("road_infrastructure", "uses", 0.6)],
    "bike": [("petrol", "affected_by", 0.7)],
    "metro": [("metro_fare", "pays", 0.7)],
    "bus": [("bus_fare", "pays", 0.6)],
    "auto_cab": [("ride_hailing", "uses", 0.7), ("petrol", "affected_by", 0.5)],
    "cycle": [("road_infrastructure", "uses", 0.3)],
    "wfh": [("electricity", "consumes", 0.7), ("broadband_internet", "depends_on", 0.8)],
}

LOANS_MAP: dict[str, list[tuple[str, str, float]]] = {
    "home": [("home_loan", "has", 1.0), ("repo_rate", "sensitive_to", 0.95), ("rbi_mpc", "watches", 0.9)],
    "car": [("auto_loan", "has", 0.8)],
    "education": [("education_loan", "has", 0.8), ("education_loan_subsidy", "eligible_for", 0.6)],
    "personal": [("personal_loan", "has", 0.8)],
    "credit_card": [("credit_cards", "has", 0.7)],
    "business": [("business_loan", "has", 0.9), ("business_loan", "part_of", 0.6)],
    "none": [],
}

INVESTMENTS_MAP: dict[str, list[tuple[str, str, float]]] = {
    "stocks": [("equity_markets", "invests_in", 0.9), ("nifty_50", "tracks", 0.7), ("sebi", "regulated_by", 0.6), ("capital_gains_tax", "pays", 0.7)],
    "mf": [("mutual_funds", "invests_in", 0.8), ("sebi", "regulated_by", 0.6)],
    "fd": [("fd_rates", "invests_in", 0.8), ("repo_rate", "affected_by", 0.7)],
    "gold": [("gold", "tracks", 0.8), ("gold_import_duty", "affected_by", 0.6)],
    "ppf_nps": [("ppf", "invests_in", 0.7), ("nps", "invests_in", 0.7)],
    "crypto": [("crypto_currencies", "invests_in", 0.7), ("crypto_regulation_india", "regulated_by", 0.8)],
    "real_estate": [("real_estate_sector", "invests_in", 0.8), ("property_price", "tracks", 0.7)],
    "none": [],
}

DEPENDENTS_MAP: dict[str, list[tuple[str, str, float]]] = {
    "spouse": [],
    "school_children": [("school_fees", "pays", 0.9), ("education_policy", "affected_by", 0.8)],
    "college_children": [("college_university_fees", "pays", 0.9), ("education_loan", "may_need", 0.7)],
    "parents": [("elderly_care", "needs", 0.8), ("health_insurance", "needs", 0.7)],
    "none": [],
}

TOP_EXPENSES_MAP: dict[str, list[tuple[str, str, float]]] = {
    "groceries": [("food_inflation_india", "affected_by", 0.9), ("vegetable_prices", "affected_by", 0.8), ("pulses", "affected_by", 0.7), ("edible_oil", "consumes", 0.7), ("milk", "affected_by", 0.6), ("chicken", "affected_by", 0.5)],
    "fuel_transport": [("petrol", "affected_by", 0.9), ("diesel", "affected_by", 0.8), ("crude_oil", "depends_on", 0.7), ("road_infrastructure", "uses", 0.5)],
    "children_education": [("school_fees", "pays", 0.9), ("education_policy", "affected_by", 0.8), ("college_university_fees", "pays", 0.7)],
    "healthcare_insurance": [("health_insurance", "pays", 0.8), ("pharma_sector", "depends_on", 0.6)],
    "utilities": [("electricity", "consumes", 0.8), ("electricity", "affected_by", 0.8), ("water_supply", "affected_by", 0.6), ("lpg_cylinder", "affected_by", 0.7), ("piped_gas", "uses", 0.5)],
    "eating_out": [("gst", "pays", 0.5), ("food_inflation_india", "affected_by", 0.6)],
    "subscriptions_tech": [("broadband_internet", "depends_on", 0.7), ("telecom_sector", "uses", 0.6), ("digital_services", "subscribes_to", 0.6)],
    "domestic_help": [("minimum_wage", "affected_by", 0.6), ("informal_sector", "depends_on", 0.5)],
    "parents_care": [("elderly_care", "needs", 0.8)],
    "savings_investments": [("deposit_growth", "affected_by", 0.7), ("repo_rate", "affected_by", 0.6), ("equity_markets", "invests_in", 0.5)],
    "entertainment_travel": [("hospitality_tourism_sector", "uses", 0.6), ("air_travel", "uses", 0.5)],
}

INCOME_MULTIPLIER_MAP: dict[str, float] = {
    "under_25k": 1.3,
    "25k_50k": 1.2,
    "50k_1l": 1.0,
    "1l_2.5l": 1.0,
    "2.5l_5l": 0.9,
    "above_5l": 0.8,
    "prefer_not_say": 1.0,
}

# ---------------------------------------------------------------------------
# Tier 2: Sector-specific deep-dive maps
# ---------------------------------------------------------------------------

TIER2_INVESTMENTS_MAP = {
    "inv_types": {
        "individual_stocks": [("equity_markets", "invests_in", 0.9), ("nifty_50", "tracks", 0.8), ("capital_gains_tax", "pays", 0.7), ("sebi", "regulated_by", 0.6)],
        "equity_mf": [("mutual_funds", "invests_in", 0.8), ("equity_markets", "exposed_to", 0.7), ("sebi", "regulated_by", 0.6)],
        "debt_mf": [("mutual_funds", "invests_in", 0.7), ("repo_rate", "affected_by", 0.7)],
        "index_funds": [("nifty_50", "tracks", 0.8), ("index_fund", "uses", 0.7)],
        "bonds": [("corporate_bonds", "invests_in", 0.8), ("repo_rate", "affected_by", 0.7)],
        "gold_physical_digital": [("gold", "tracks", 0.9), ("gold_import_duty", "affected_by", 0.7)],
        "crypto": [("crypto_currencies", "invests_in", 0.8), ("crypto_regulation_india", "regulated_by", 0.9)],
        "none_of_these": [],
    },
    "inv_alternative": {
        "reits": [("real_estate_sector", "invests_in", 0.7), ("reit", "invests_in", 0.8)],
        "startup_vc_angel": [("vc_funding_india", "invests_in", 0.8), ("angel_tax", "affected_by", 0.7), ("startup_policy", "supports", 0.6)],
        "p2p_lending": [("digital_lending", "uses", 0.7)],
        "commodities": [("global_commodity_cycle", "tracks", 0.8), ("crude_oil", "trades", 0.6)],
        "foreign_stocks": [("us_economy", "exposed_to", 0.7), ("usd_inr", "affected_by", 0.8), ("fii_flows", "affected_by", 0.6)],
        "none": [],
    },
    "inv_global": {
        "yes_significantly": [("us_economy", "exposed_to", 0.9), ("fii_flows", "affected_by", 0.8), ("usd_inr", "affected_by", 0.8), ("fed_policy", "watches", 0.7)],
        "somewhat": [("us_economy", "exposed_to", 0.5), ("fii_flows", "affected_by", 0.5)],
        "not_really": [],
    },
}

TIER2_HEALTH_MAP = {
    "health_insurance": {
        "employer_provided": [("health_insurance", "has", 0.8), ("superannuation", "receives", 0.6)],
        "private_self_bought": [("health_insurance", "has", 0.9)],
        "government": [("health_scheme_state", "eligible_for", 0.8), ("public_healthcare", "uses", 0.7)],
        "none": [("uninsured", "is", 0.9)],
    },
    "health_conditions": {
        "diabetes": [("diabetes_medication", "needs", 0.9), ("sugar", "monitors", 0.5)],
        "heart": [("cardiac_care", "needs", 0.9)],
        "asthma": [("air_quality", "sensitive_to", 0.9), ("respiratory_drugs", "needs", 0.8)],
        "thyroid": [("thyroid_medication", "needs", 0.8)],
        "bp": [("bp_medication", "needs", 0.8)],
        "mental_health": [("mental_health_services", "needs", 0.8)],
        "none": [],
        "prefer_not_say": [],
    },
    "health_env": {
        "air_pollution": [("air_quality", "sensitive_to", 0.9), ("respiratory_drugs", "may_need", 0.5)],
        "water_quality": [("water_quality", "concerned_about", 0.8), ("water_purification", "needs", 0.6)],
        "noise_pollution": [("noise_pollution", "affected_by", 0.6)],
        "none": [],
    },
}

TIER2_EDUCATION_MAP = {
    "edu_pursuing": {
        "school_k12": [("school_fees", "pays", 0.9), ("education_policy", "affected_by", 0.8)],
        "college_university": [("college_university_fees", "pays", 0.9), ("education_loan", "may_need", 0.7), ("college_regulation", "regulated_by", 0.5)],
        "professional_courses": [("professional_courses", "pursuing", 0.8)],
        "competitive_exams": [("coaching_industry", "preparing_for", 0.8), ("coaching_industry", "uses", 0.7)],
        "online_upskilling": [("edtech_sector", "uses", 0.7), ("ai_job_displacement", "adapting_to", 0.6)],
        "none": [],
    },
    "edu_career": {
        "job_market": [("job_market_india", "concerned_about", 0.8), ("ai_job_displacement", "worried_about", 0.7)],
        "ai_impact": [("ai_job_displacement", "exposed_to", 0.9), ("skill_obsolescence", "worried_about", 0.8)],
        "upskilling": [("edtech_sector", "uses", 0.6), ("skill_development", "pursuing", 0.7)],
        "govt_exam": [("coaching_industry", "preparing_for", 0.8), ("government_employment", "aspires_to", 0.7)],
        "career_switch": [("job_market_india", "navigating", 0.7), ("skill_development", "pursuing", 0.6)],
        "none": [],
    },
}

TIER2_CIVIC_MAP = {
    "civic_concerns": {
        "roads_traffic": [("road_infrastructure", "concerned_about", 0.8)],
        "waste_management": [("solid_waste_management", "concerned_about", 0.7), ("municipal_services", "uses", 0.6)],
        "water_supply": [("water_supply", "concerned_about", 0.8), ("water_supply", "pays", 0.6)],
        "air_quality": [("air_quality", "concerned_about", 0.9), ("spcb", "wants", 0.7)],
        "public_safety": [("law_and_order", "concerned_about", 0.7)],
        "urban_flooding": [("urban_flooding", "exposed_to", 0.8), ("monsoon", "affected_by", 0.7)],
        "power_cuts": [("electricity", "depends_on", 0.8), ("electricity", "pays", 0.7)],
        "none": [],
    },
    "civic_govt": {
        "frequently": [("government_services", "uses", 0.8), ("bureaucracy", "interacts_with", 0.7)],
        "occasionally": [("government_services", "uses", 0.5)],
        "rarely": [("government_services", "uses", 0.3)],
        "never": [],
    },
    "civic_dev": {
        "metro_highway": [("road_infrastructure", "affected_by", 0.7), ("land_acquisition", "affected_by", 0.6)],
        "smart_city": [("smart_city", "affected_by", 0.7), ("municipal_services", "improved_by", 0.6)],
        "industrial_corridors": [("state_economic_policy", "affected_by", 0.7), ("land_acquisition", "affected_by", 0.6)],
        "housing_schemes": [("affordable_housing", "eligible_for", 0.7), ("real_estate_sector", "affected_by", 0.6)],
        "none": [],
    },
}

TIER2_CONSUMER_MAP = {
    "consumer_purchases": {
        "electronics": [("electronics", "buys", 0.7), ("customs_duty", "affected_by", 0.6), ("gst", "pays", 0.5)],
        "clothing": [("clothing", "buys_from", 0.6), ("retail_sector", "uses", 0.5)],
        "home_appliances": [("electronics", "buys", 0.6), ("consumer", "is", 0.5)],
        "automobile": [("auto_manufacturing", "buys_from", 0.8), ("auto_loan", "may_need", 0.6), ("petrol", "affected_by", 0.7)],
        "none": [],
    },
    "consumer_leisure": {
        "travel": [("hospitality_tourism_sector", "uses", 0.8), ("air_travel", "uses", 0.7), ("hotel_accommodation", "uses", 0.6)],
        "dining_out": [("gst", "pays", 0.5)],
        "ott_streaming": [("digital_services", "subscribes_to", 0.6)],
        "fitness": [("gym_fitness", "uses", 0.5)],
        "gaming": [("gaming_sector", "uses", 0.5), ("digital_services", "subscribes_to", 0.4)],
        "none": [],
    },
    "consumer_pets": {
        "dog": [("pet_industry", "uses", 0.6), ("veterinary_care", "uses", 0.5)],
        "cat": [("pet_industry", "uses", 0.6), ("veterinary_care", "uses", 0.5)],
        "other_pet": [("pet_industry", "uses", 0.5)],
        "no_pets": [],
    },
}

TIER2_MAPS: dict[str, dict] = {
    "investments": TIER2_INVESTMENTS_MAP,
    "health": TIER2_HEALTH_MAP,
    "education": TIER2_EDUCATION_MAP,
    "civic": TIER2_CIVIC_MAP,
    "consumer": TIER2_CONSUMER_MAP,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INFRA_CATEGORIES = {"municipal", "electricity", "water", "transport"}


def _add_edges_from_tuples(
    edges: list[UserEdge],
    tuples: list[tuple[str, str, float]],
    graph: ImpactGraph,
) -> None:
    """Append UserEdge for each tuple whose node exists in the graph."""
    for node_id, relation, importance in tuples:
        if graph.get_node(node_id):
            edges.append(UserEdge(node_id=node_id, relation=relation, importance=importance))


def _process_multi_select(
    edges: list[UserEdge],
    answers: dict,
    key: str,
    mapping: dict[str, list[tuple[str, str, float]]],
    graph: ImpactGraph,
) -> None:
    """Process a multi-select answer (list of strings)."""
    values = answers.get(key, [])
    if not isinstance(values, list):
        values = [values]
    for val in values:
        tuples = mapping.get(val, [])
        _add_edges_from_tuples(edges, tuples, graph)


def _process_single_select(
    edges: list[UserEdge],
    answers: dict,
    key: str,
    mapping: dict[str, list[tuple[str, str, float]]],
    graph: ImpactGraph,
) -> None:
    """Process a single-select answer (string)."""
    val = answers.get(key)
    if val is None:
        return
    tuples = mapping.get(val, [])
    _add_edges_from_tuples(edges, tuples, graph)


# ---------------------------------------------------------------------------
# Main entry point — Tier 1
# ---------------------------------------------------------------------------


def connect_user_to_graph(
    answers: dict,
    graph: ImpactGraph,
    user_id: str = "default",
) -> UserGraph:
    """Maps Tier 1 questionnaire answers to graph nodes."""
    edges: list[UserEdge] = []

    # Q1: City
    city = answers.get("city", "").lower()
    if city in CITY_GRAPH_MAP:
        city_data = CITY_GRAPH_MAP[city]
        for category, nodes in city_data.items():
            if category == "direct":
                importance = 1.0
            elif category in _INFRA_CATEGORIES:
                importance = 0.8
            else:
                importance = 0.6
            for node_id in nodes:
                if graph.get_node(node_id):
                    edges.append(UserEdge(node_id=node_id, relation=f"lives_in_{category}", importance=importance))

    # Q2: Employment type (single-select)
    _process_single_select(edges, answers, "employment", EMPLOYMENT_TYPE_MAP, graph)

    # Q3: Industry (single-select)
    _process_single_select(edges, answers, "industry", INDUSTRY_MAP, graph)

    # Q4: Housing (single-select)
    _process_single_select(edges, answers, "housing", HOUSING_MAP, graph)

    # Q5: Transport (multi-select)
    _process_multi_select(edges, answers, "transport", TRANSPORT_MAP, graph)

    # Q6: Loans (multi-select)
    _process_multi_select(edges, answers, "loans", LOANS_MAP, graph)

    # Q7: Dependents (multi-select)
    _process_multi_select(edges, answers, "dependents", DEPENDENTS_MAP, graph)

    # Q8: Investments (multi-select)
    _process_multi_select(edges, answers, "investments", INVESTMENTS_MAP, graph)

    # Q9: Top expenses (multi-select)
    _process_multi_select(edges, answers, "top_expenses", TOP_EXPENSES_MAP, graph)

    # Q10: Income range → importance multiplier (not a node map)
    income = answers.get("income_range", "")
    income_multiplier = INCOME_MULTIPLIER_MAP.get(income, 1.0)

    # Apply income-based importance scaling
    # Lower income = higher sensitivity to price changes
    for edge in edges:
        edge.importance = round(min(edge.importance * income_multiplier, 1.0), 2)

    # Compute reachability
    direct_nodes = [e.node_id for e in edges]
    reachable = graph.backward_bfs(direct_nodes, max_hops=3)

    return UserGraph(
        user_id=user_id,
        edges=edges,
        reachable_nodes=reachable,
        completed_tiers=["tier1"],
        income_multiplier=income_multiplier,
    )


# ---------------------------------------------------------------------------
# Tier 2 enrichment
# ---------------------------------------------------------------------------


def enrich_user_graph(
    existing: UserGraph,
    sector: str,
    answers: dict,
    graph: ImpactGraph,
) -> UserGraph:
    """Add Tier 2 edges to existing user graph."""
    sector_maps = TIER2_MAPS.get(sector)
    if not sector_maps:
        return existing

    new_edges: list[UserEdge] = []

    for question_key, option_map in sector_maps.items():
        val = answers.get(question_key)
        if val is None:
            continue
        if isinstance(val, list):
            for v in val:
                tuples = option_map.get(v, [])
                _add_edges_from_tuples(new_edges, tuples, graph)
        else:
            tuples = option_map.get(val, [])
            _add_edges_from_tuples(new_edges, tuples, graph)

    # Apply income multiplier from existing profile
    for edge in new_edges:
        edge.importance = round(min(edge.importance * existing.income_multiplier, 1.0), 2)

    # Merge: add new edges, deduplicate by node_id
    existing_node_ids = {e.node_id for e in existing.edges}
    for edge in new_edges:
        if edge.node_id not in existing_node_ids:
            existing.edges.append(edge)
            existing_node_ids.add(edge.node_id)

    # Update completed tiers
    if sector not in existing.completed_tiers:
        existing.completed_tiers.append(sector)

    # Recompute reachability with expanded edges
    direct_nodes = [e.node_id for e in existing.edges]
    existing.reachable_nodes = graph.backward_bfs(direct_nodes, max_hops=3)

    return existing
