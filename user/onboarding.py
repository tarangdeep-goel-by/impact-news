"""Questionnaire definition and logic for user onboarding."""

from dataclasses import dataclass


@dataclass
class Question:
    key: str  # answer dict key
    text: str  # question text shown to user
    options: list[str]  # button labels
    multi_select: bool  # True for multi-select questions
    callback_prefix: str  # prefix for callback data


# ---------------------------------------------------------------------------
# Tier 1 — Core profiling (everyone answers these)
# ---------------------------------------------------------------------------

QUESTIONS = [
    Question(
        key="city",
        text="Where do you live?",
        options=[
            "Mumbai", "Delhi NCR", "Bangalore", "Hyderabad", "Chennai",
            "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow", "Other",
        ],
        multi_select=False,
        callback_prefix="city",
    ),
    Question(
        key="employment",
        text="What best describes your work situation?",
        options=[
            "Salaried (private)", "Salaried (govt/PSU)", "Self-employed/Business",
            "Freelance/Gig", "Student", "Retired", "Homemaker",
        ],
        multi_select=False,
        callback_prefix="employ",
    ),
    Question(
        key="industry",
        text="What industry/sector do you work in?",
        options=[
            "IT/Software", "Banking/Finance", "Healthcare", "Manufacturing",
            "Education", "Government/PSU", "Retail", "Startups", "Agriculture",
            "Consulting", "Media/Entertainment", "Real Estate", "Pharma",
            "Telecom", "Other",
        ],
        multi_select=False,
        callback_prefix="industry",
    ),
    Question(
        key="housing",
        text="What's your living situation?",
        options=["Own (with loan/EMI)", "Own (no loan)", "Rent", "Living with family"],
        multi_select=False,
        callback_prefix="housing",
    ),
    Question(
        key="transport",
        text="How do you get around? (tap all, then Done)",
        options=[
            "Own car", "Bike/scooter", "Metro/train", "Bus",
            "Auto/cab", "Cycle/walk", "WFH mostly",
        ],
        multi_select=True,
        callback_prefix="transport",
    ),
    Question(
        key="loans",
        text="Any active loans or EMIs? (tap all, then Done)",
        options=[
            "Home loan", "Car loan", "Education loan", "Personal loan",
            "Credit card debt", "Business loan", "No loans",
        ],
        multi_select=True,
        callback_prefix="loans",
    ),
    Question(
        key="dependents",
        text="Who depends on your income? (tap all, then Done)",
        options=[
            "Spouse/partner", "Children (school-age)", "Children (college)",
            "Elderly parents", "None",
        ],
        multi_select=True,
        callback_prefix="depend",
    ),
    Question(
        key="investments",
        text="Where do you invest? (tap all, then Done)",
        options=[
            "Stocks", "Mutual Funds", "Fixed Deposits", "Gold",
            "PPF/NPS", "Crypto", "Real Estate", "Don't invest",
        ],
        multi_select=True,
        callback_prefix="invest",
    ),
    Question(
        key="top_expenses",
        text="What are your biggest monthly expenses after housing? (pick your top 3, then Done)",
        options=[
            "Groceries & cooking", "Fuel & transport", "Children's education",
            "Healthcare/insurance", "Utilities (electricity/water/gas)",
            "Eating out/delivery", "Subscriptions & tech", "Domestic help",
            "Parents' care", "Savings/investments", "Entertainment/travel",
        ],
        multi_select=True,
        callback_prefix="expenses",
    ),
    Question(
        key="income_range",
        text="What's your approximate monthly household income?",
        options=[
            "Under ₹25K", "₹25K–50K", "₹50K–1L", "₹1L–2.5L",
            "₹2.5L–5L", "Above ₹5L", "Prefer not to say",
        ],
        multi_select=False,
        callback_prefix="income",
    ),
]

# ---------------------------------------------------------------------------
# Tier 2 — Sector deep-dives (shown based on Tier 1 answers)
# ---------------------------------------------------------------------------

TIER2_SECTORS: dict[str, dict] = {
    "investments": {
        "name": "Advanced Investments",
        "questions": [
            Question(
                key="inv_types",
                text="What types of investments do you hold? (tap all, then Done)",
                options=[
                    "Individual stocks", "Equity MF", "Debt MF",
                    "Index funds/ETFs", "Bonds/debentures",
                    "Gold (physical/digital)", "Crypto", "None of these",
                ],
                multi_select=True,
                callback_prefix="inv_type",
            ),
            Question(
                key="inv_alternative",
                text="Any alternative investments? (tap all, then Done)",
                options=[
                    "REITs", "Startup/VC/Angel", "P2P lending",
                    "Commodities", "Foreign stocks", "None",
                ],
                multi_select=True,
                callback_prefix="inv_alt",
            ),
            Question(
                key="inv_global",
                text="Do global markets affect your investments?",
                options=["Yes significantly", "Somewhat", "Not really"],
                multi_select=False,
                callback_prefix="inv_global",
            ),
        ],
    },
    "health": {
        "name": "Health & Wellness",
        "questions": [
            Question(
                key="health_insurance",
                text="What health insurance do you have?",
                options=[
                    "Employer-provided", "Private (self-bought)",
                    "Government (Ayushman/CGHS)", "None",
                ],
                multi_select=False,
                callback_prefix="h_ins",
            ),
            Question(
                key="health_conditions",
                text="Any chronic conditions in your household? (tap all, then Done)",
                options=[
                    "Diabetes", "Heart condition", "Asthma/respiratory",
                    "Thyroid", "Blood pressure", "Mental health",
                    "None", "Prefer not to say",
                ],
                multi_select=True,
                callback_prefix="h_cond",
            ),
            Question(
                key="health_env",
                text="Any environmental health concerns? (tap all, then Done)",
                options=["Air pollution", "Water quality", "Noise pollution", "None"],
                multi_select=True,
                callback_prefix="h_env",
            ),
        ],
    },
    "education": {
        "name": "Education & Career",
        "questions": [
            Question(
                key="edu_pursuing",
                text="Anyone in your household pursuing education? (tap all, then Done)",
                options=[
                    "School (K-12)", "College/University",
                    "Professional courses (CA/law/MBA)",
                    "Competitive exams (UPSC/JEE/NEET)",
                    "Online courses/upskilling", "None",
                ],
                multi_select=True,
                callback_prefix="edu_type",
            ),
            Question(
                key="edu_career",
                text="Career concerns? (tap all, then Done)",
                options=[
                    "Job market competition", "AI impact on my field",
                    "Upskilling needs", "Govt exam preparation",
                    "Career switch", "None",
                ],
                multi_select=True,
                callback_prefix="edu_career",
            ),
        ],
    },
    "civic": {
        "name": "Local Civic Life",
        "questions": [
            Question(
                key="civic_concerns",
                text="Local civic concerns? (tap all, then Done)",
                options=[
                    "Roads & traffic", "Waste management", "Water supply",
                    "Air quality", "Public safety", "Urban flooding",
                    "Power cuts", "None",
                ],
                multi_select=True,
                callback_prefix="civic",
            ),
            Question(
                key="civic_govt",
                text="How often do you interact with govt services?",
                options=["Frequently", "Occasionally", "Rarely", "Never"],
                multi_select=False,
                callback_prefix="civic_govt",
            ),
            Question(
                key="civic_dev",
                text="Any development projects affecting you? (tap all, then Done)",
                options=[
                    "Metro/highway construction", "Smart city projects",
                    "Industrial corridors", "Housing schemes", "None",
                ],
                multi_select=True,
                callback_prefix="civic_dev",
            ),
        ],
    },
    "consumer": {
        "name": "Consumer & Lifestyle",
        "questions": [
            Question(
                key="consumer_purchases",
                text="Big purchase categories for you? (tap all, then Done)",
                options=[
                    "Electronics/gadgets", "Clothing/fashion",
                    "Home appliances", "Automobile", "None",
                ],
                multi_select=True,
                callback_prefix="con_buy",
            ),
            Question(
                key="consumer_leisure",
                text="Leisure activities? (tap all, then Done)",
                options=[
                    "Travel/holidays", "Dining out", "OTT/streaming",
                    "Fitness/sports", "Gaming", "None",
                ],
                multi_select=True,
                callback_prefix="con_leisure",
            ),
            Question(
                key="consumer_pets",
                text="Do you have pets?",
                options=["Dog", "Cat", "Other pet", "No pets"],
                multi_select=False,
                callback_prefix="con_pet",
            ),
        ],
    },
}

# ---------------------------------------------------------------------------
# Answer normalisation
# ---------------------------------------------------------------------------

# Maps button labels to answer values for inference.py
ANSWER_VALUE_MAP = {
    # --- Tier 1 ---
    # City
    "Mumbai": "mumbai", "Delhi NCR": "delhi", "Bangalore": "bangalore",
    "Hyderabad": "hyderabad", "Chennai": "chennai", "Pune": "pune",
    "Kolkata": "kolkata", "Ahmedabad": "ahmedabad", "Jaipur": "jaipur",
    "Lucknow": "lucknow",
    # Employment
    "Salaried (private)": "salaried_private", "Salaried (govt/PSU)": "salaried_govt",
    "Self-employed/Business": "self_employed", "Freelance/Gig": "freelance",
    "Student": "student", "Retired": "retired", "Homemaker": "homemaker",
    # Industry
    "IT/Software": "IT", "Banking/Finance": "Banking", "Healthcare": "Healthcare",
    "Manufacturing": "Manufacturing", "Education": "Education",
    "Government/PSU": "Government", "Retail": "Retail", "Startups": "Startups",
    "Agriculture": "Agriculture", "Consulting": "Consulting",
    "Media/Entertainment": "media_entertainment", "Real Estate": "real_estate",
    "Pharma": "pharma", "Telecom": "telecom",
    # Housing
    "Own (with loan/EMI)": "own_loan", "Own (no loan)": "own_clear",
    "Rent": "rent", "Living with family": "family",
    # Transport
    "Own car": "car", "Bike/scooter": "bike", "Metro/train": "metro",
    "Bus": "bus", "Auto/cab": "auto_cab", "Cycle/walk": "cycle", "WFH mostly": "wfh",
    # Loans
    "Home loan": "home", "Car loan": "car_loan", "Education loan": "education",
    "Personal loan": "personal", "Credit card debt": "credit_card",
    "Business loan": "business", "No loans": "none",
    # Dependents
    "Spouse/partner": "spouse", "Children (school-age)": "school_children",
    "Children (college)": "college_children", "Elderly parents": "parents",
    # Investments
    "Stocks": "stocks", "Mutual Funds": "mf", "Fixed Deposits": "fd",
    "Gold": "gold", "PPF/NPS": "ppf_nps", "Crypto": "crypto",
    "Real Estate": "real_estate", "Don't invest": "none",
    # Top expenses
    "Groceries & cooking": "groceries", "Fuel & transport": "fuel_transport",
    "Children's education": "children_education", "Healthcare/insurance": "healthcare_insurance",
    "Utilities (electricity/water/gas)": "utilities", "Eating out/delivery": "eating_out",
    "Subscriptions & tech": "subscriptions_tech", "Domestic help": "domestic_help",
    "Parents' care": "parents_care", "Savings/investments": "savings_investments",
    "Entertainment/travel": "entertainment_travel",
    # Income range
    "Under ₹25K": "under_25k", "₹25K–50K": "25k_50k", "₹50K–1L": "50k_1l",
    "₹1L–2.5L": "1l_2.5l", "₹2.5L–5L": "2.5l_5l", "Above ₹5L": "above_5l",
    "Prefer not to say": "prefer_not_say",
    # --- Tier 2: Investments ---
    "Individual stocks": "individual_stocks", "Equity MF": "equity_mf",
    "Debt MF": "debt_mf", "Index funds/ETFs": "index_etfs",
    "Bonds/debentures": "bonds", "Gold (physical/digital)": "gold_physical_digital",
    "None of these": "none",
    "REITs": "reits", "Startup/VC/Angel": "startup_vc_angel",
    "P2P lending": "p2p_lending", "Commodities": "commodities",
    "Foreign stocks": "foreign_stocks",
    "Yes significantly": "yes_significantly", "Somewhat": "somewhat",
    "Not really": "not_really",
    # --- Tier 2: Health ---
    "Employer-provided": "employer_provided", "Private (self-bought)": "private_self",
    "Government (Ayushman/CGHS)": "govt_ayushman",
    "Diabetes": "diabetes", "Heart condition": "heart",
    "Asthma/respiratory": "asthma", "Thyroid": "thyroid",
    "Blood pressure": "bp", "Mental health": "mental_health",
    "Air pollution": "air_pollution", "Water quality": "water_quality",
    "Noise pollution": "noise_pollution",
    # --- Tier 2: Education ---
    "School (K-12)": "school_k12", "College/University": "college_university",
    "Professional courses (CA/law/MBA)": "professional_courses",
    "Competitive exams (UPSC/JEE/NEET)": "competitive_exams",
    "Online courses/upskilling": "online_upskilling",
    "Job market competition": "job_market", "AI impact on my field": "ai_impact",
    "Upskilling needs": "upskilling", "Govt exam preparation": "govt_exam",
    "Career switch": "career_switch",
    # --- Tier 2: Civic ---
    "Roads & traffic": "roads_traffic", "Waste management": "waste_management",
    "Water supply": "water_supply", "Air quality": "air_quality",
    "Public safety": "public_safety", "Urban flooding": "urban_flooding",
    "Power cuts": "power_cuts",
    "Frequently": "frequently", "Occasionally": "occasionally",
    "Rarely": "rarely", "Never": "never",
    "Metro/highway construction": "metro_highway", "Smart city projects": "smart_city",
    "Industrial corridors": "industrial_corridors", "Housing schemes": "housing_schemes",
    # --- Tier 2: Consumer ---
    "Electronics/gadgets": "electronics", "Clothing/fashion": "clothing",
    "Home appliances": "home_appliances", "Automobile": "automobile",
    "Travel/holidays": "travel", "Dining out": "dining_out",
    "OTT/streaming": "ott_streaming", "Fitness/sports": "fitness",
    "Gaming": "gaming",
    "Dog": "dog", "Cat": "cat", "Other pet": "other_pet", "No pets": "no_pets",
    # Shared
    "None": "none",
}

# Options that should clear other selections when picked in multi-select
EXCLUSIVE_OPTIONS = {
    "No loans", "Don't invest", "None", "Prefer not to say",
    "None of these", "No pets", "Not really", "Never",
}


def normalize_answer(label: str) -> str:
    """Convert button label to inference value."""
    return ANSWER_VALUE_MAP.get(label, label.lower().replace(" ", "_"))
