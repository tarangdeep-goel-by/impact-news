"""Inference engine: maps questionnaire answers to graph nodes."""

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
        "economy": ["it_services_sector", "pharma"],
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
        "economy": ["tourism_sector", "retail_sector"],
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
        "economy": ["tourism_sector", "it_services_sector"],
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
# Question → graph-node maps
# Each entry: (node_id, relation, importance)
# ---------------------------------------------------------------------------

WORK_SECTOR_MAP: dict[str, list[tuple[str, str, float]]] = {
    "IT": [("it_services_sector", "works_in", 1.0), ("automation_risk", "exposed_to", 0.7), ("us_economy", "depends_on", 0.6)],
    "Banking": [("banking_sector", "works_in", 1.0), ("rbi_regulation", "regulated_by", 0.8), ("repo_rate", "affected_by", 0.9)],
    "Healthcare": [("healthcare_sector", "works_in", 1.0), ("pharma", "depends_on", 0.7)],
    "Manufacturing": [("manufacturing_sector", "works_in", 1.0), ("industrial_policy", "regulated_by", 0.7)],
    "Education": [("education_sector", "works_in", 1.0), ("education_policy", "regulated_by", 0.8)],
    "Government": [("government_employment", "works_in", 1.0), ("pay_commission", "affected_by", 0.9)],
    "Retail": [("retail_sector", "works_in", 1.0), ("consumer", "depends_on", 0.7)],
    "Startups": [("startup_ecosystem", "works_in", 1.0), ("venture_capital", "funded_by", 0.8), ("angel_tax", "affected_by", 0.7)],
    "Gig": [("gig_economy", "works_in", 1.0), ("platform_economy", "depends_on", 0.8)],
    "Agriculture": [("agriculture_sector", "works_in", 1.0), ("monsoon", "depends_on", 0.9), ("crop_insurance", "uses", 0.7)],
    "Consulting": [("consulting_sector", "works_in", 1.0)],
    "Other": [],
}

HOUSING_MAP: dict[str, list[tuple[str, str, float]]] = {
    "own_loan": [("home_loan", "has", 1.0), ("repo_rate", "sensitive_to", 0.9), ("property_tax", "pays", 0.7), ("real_estate", "owns", 0.6)],
    "own_clear": [("property_tax", "pays", 0.7), ("real_estate", "owns", 0.6)],
    "rent": [("rental_market", "uses", 0.8), ("rent_inflation", "affected_by", 0.7)],
}

COMMUTE_MAP: dict[str, list[tuple[str, str, float]]] = {
    "car": [("petrol_price", "affected_by", 0.9), ("diesel_price", "affected_by", 0.8), ("road_infrastructure", "uses", 0.6), ("auto_insurance", "pays", 0.5)],
    "bike": [("petrol_price", "affected_by", 0.7)],
    "metro": [("metro_fare", "pays", 0.7), ("urban_transport", "uses", 0.6)],
    "bus": [("bus_fare", "pays", 0.6), ("urban_transport", "uses", 0.5)],
    "auto_cab": [("ride_hailing", "uses", 0.7), ("petrol_price", "affected_by", 0.5)],
    "cycle": [("road_infrastructure", "uses", 0.3)],
    "wfh": [("electricity", "consumes", 0.7), ("broadband", "depends_on", 0.8)],
}

LOANS_MAP: dict[str, list[tuple[str, str, float]]] = {
    "home": [("home_loan", "has", 1.0), ("repo_rate", "sensitive_to", 0.95), ("rbi_mpc", "watches", 0.9)],
    "car": [("auto_loan", "has", 0.8)],
    "education": [("education_loan", "has", 0.8), ("education_loan_subsidy", "eligible_for", 0.6)],
    "personal": [("personal_loan", "has", 0.8), ("unsecured_lending", "exposed_to", 0.7)],
    "credit_card": [("credit_card_debt", "has", 0.7)],
    "none": [],
}

INVESTMENTS_MAP: dict[str, list[tuple[str, str, float]]] = {
    "stocks": [("equity_markets", "invests_in", 0.9), ("nifty_50", "tracks", 0.7), ("sebi_regulation", "regulated_by", 0.6), ("capital_gains_tax", "pays", 0.7)],
    "mf": [("mutual_funds", "invests_in", 0.8), ("sebi_regulation", "regulated_by", 0.6)],
    "fd": [("fixed_deposits", "invests_in", 0.8), ("repo_rate", "affected_by", 0.7)],
    "gold": [("gold_prices", "tracks", 0.8), ("gold_import_duty", "affected_by", 0.6)],
    "ppf_nps": [("ppf", "invests_in", 0.7), ("nps", "invests_in", 0.7)],
    "crypto": [("cryptocurrency", "invests_in", 0.7), ("crypto_regulation", "regulated_by", 0.8)],
    "real_estate": [("real_estate", "invests_in", 0.8), ("property_prices", "tracks", 0.7)],
    "none": [],
}

DIET_MAP: dict[str, list[tuple[str, str, float]]] = {
    "veg": [("vegetable_prices", "affected_by", 0.9), ("dal_prices", "affected_by", 0.8), ("cooking_oil", "consumes", 0.7), ("dairy_prices", "affected_by", 0.7)],
    "vegan": [("vegetable_prices", "affected_by", 0.9), ("dal_prices", "affected_by", 0.8), ("cooking_oil", "consumes", 0.7)],
    "non_veg": [("vegetable_prices", "affected_by", 0.7), ("poultry_prices", "affected_by", 0.8), ("fish_prices", "affected_by", 0.7), ("cooking_oil", "consumes", 0.7), ("dairy_prices", "affected_by", 0.6)],
    "eggetarian": [("vegetable_prices", "affected_by", 0.8), ("egg_prices", "affected_by", 0.8), ("dairy_prices", "affected_by", 0.7), ("cooking_oil", "consumes", 0.7)],
    "no_restriction": [("food_inflation_india", "affected_by", 0.7)],
}

DEPENDENTS_MAP: dict[str, list[tuple[str, str, float]]] = {
    "spouse": [("household_income", "contributes_to", 0.5)],
    "school_children": [("school_fees", "pays", 0.9), ("education_policy", "affected_by", 0.8)],
    "college_children": [("higher_education_costs", "pays", 0.9), ("education_loan", "may_need", 0.7)],
    "parents": [("elderly_care", "needs", 0.8), ("healthcare_costs", "pays", 0.8), ("health_insurance", "needs", 0.7)],
    "none": [],
}

HEALTH_MAP: dict[str, list[tuple[str, str, float]]] = {
    "diabetes": [("insulin", "needs", 0.9), ("healthcare_costs", "pays", 0.8), ("sugar_prices", "monitors", 0.5)],
    "heart": [("cardiac_care", "needs", 0.9), ("healthcare_costs", "pays", 0.8)],
    "asthma": [("air_quality", "sensitive_to", 0.9), ("respiratory_medication", "needs", 0.8)],
    "thyroid": [("thyroid_medication", "needs", 0.8)],
    "bp": [("bp_medication", "needs", 0.8), ("healthcare_costs", "pays", 0.6)],
    "mental_health": [("mental_healthcare", "needs", 0.8)],
    "none": [],
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
# Main entry point
# ---------------------------------------------------------------------------


def connect_user_to_graph(
    answers: dict,
    graph: ImpactGraph,
    user_id: str = "default",
) -> UserGraph:
    """Maps questionnaire answers to graph nodes with importance weights."""
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

    # Q2: Work sector (single-select)
    _process_single_select(edges, answers, "work_sector", WORK_SECTOR_MAP, graph)

    # Q3: Housing (single-select)
    _process_single_select(edges, answers, "housing", HOUSING_MAP, graph)

    # Q4: Commute (multi-select)
    _process_multi_select(edges, answers, "commute", COMMUTE_MAP, graph)

    # Q5: Loans (multi-select)
    _process_multi_select(edges, answers, "loans", LOANS_MAP, graph)

    # Q6: Investments (multi-select)
    _process_multi_select(edges, answers, "investments", INVESTMENTS_MAP, graph)

    # Q7: Diet (single-select)
    _process_single_select(edges, answers, "diet", DIET_MAP, graph)

    # Q8: Dependents (multi-select)
    _process_multi_select(edges, answers, "dependents", DEPENDENTS_MAP, graph)

    # Q9: Health (multi-select)
    _process_multi_select(edges, answers, "health", HEALTH_MAP, graph)

    # Compute reachability (backward BFS, 3 hops)
    direct_nodes = [e.node_id for e in edges]
    reachable = graph.backward_bfs(direct_nodes, max_hops=3)

    return UserGraph(user_id=user_id, edges=edges, reachable_nodes=reachable)
