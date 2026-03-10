"""Questionnaire definition and logic for user onboarding."""

from dataclasses import dataclass


@dataclass
class Question:
    key: str  # answer dict key
    text: str  # question text shown to user
    options: list[str]  # button labels
    multi_select: bool  # True for multi-select questions
    callback_prefix: str  # prefix for callback data


QUESTIONS = [
    Question(
        key="city",
        text="Where do you live?",
        options=["Mumbai", "Delhi NCR", "Bangalore", "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow", "Other"],
        multi_select=False,
        callback_prefix="city",
    ),
    Question(
        key="work_sector",
        text="What sector do you work in?",
        options=["IT/Software", "Banking/Finance", "Healthcare", "Manufacturing", "Education", "Government/PSU", "Retail", "Startups", "Gig/Freelance", "Agriculture", "Consulting", "Other"],
        multi_select=False,
        callback_prefix="sector",
    ),
    Question(
        key="housing",
        text="Do you own or rent your home?",
        options=["Own (with loan)", "Own (no loan)", "Rent"],
        multi_select=False,
        callback_prefix="housing",
    ),
    Question(
        key="commute",
        text="How do you get around daily? (tap all that apply, then Done)",
        options=["Own car", "Bike/scooter", "Metro/train", "Bus", "Auto/cab", "Cycle/walk", "WFH mostly"],
        multi_select=True,
        callback_prefix="commute",
    ),
    Question(
        key="loans",
        text="Do you have any active loans? (tap all, then Done)",
        options=["Home loan", "Car loan", "Education loan", "Personal loan", "Credit card debt", "No loans"],
        multi_select=True,
        callback_prefix="loans",
    ),
    Question(
        key="investments",
        text="Do you invest in any of these? (tap all, then Done)",
        options=["Stocks", "Mutual Funds", "Fixed Deposits", "Gold", "PPF/NPS", "Crypto", "Real Estate", "Don't invest"],
        multi_select=True,
        callback_prefix="invest",
    ),
    Question(
        key="diet",
        text="Any dietary preferences?",
        options=["Vegetarian", "Vegan", "Non-vegetarian", "Eggetarian", "No restrictions"],
        multi_select=False,
        callback_prefix="diet",
    ),
    Question(
        key="dependents",
        text="Do you have family dependents? (tap all, then Done)",
        options=["Spouse/partner", "Children (school)", "Children (college)", "Elderly parents", "None"],
        multi_select=True,
        callback_prefix="depend",
    ),
    Question(
        key="health",
        text="Any chronic health conditions in your household? (tap all, then Done)",
        options=["Diabetes", "Heart condition", "Asthma/respiratory", "Thyroid", "Blood pressure", "Mental health", "None", "Prefer not to say"],
        multi_select=True,
        callback_prefix="health",
    ),
]

# Maps button labels to answer values for inference.py
ANSWER_VALUE_MAP = {
    # City
    "Mumbai": "mumbai", "Delhi NCR": "delhi", "Bangalore": "bangalore",
    "Hyderabad": "hyderabad", "Chennai": "chennai", "Pune": "pune",
    "Kolkata": "kolkata", "Ahmedabad": "ahmedabad", "Jaipur": "jaipur",
    "Lucknow": "lucknow",
    # Work sector
    "IT/Software": "IT", "Banking/Finance": "Banking", "Healthcare": "Healthcare",
    "Manufacturing": "Manufacturing", "Education": "Education",
    "Government/PSU": "Government", "Retail": "Retail", "Startups": "Startups",
    "Gig/Freelance": "Gig", "Agriculture": "Agriculture", "Consulting": "Consulting",
    # Housing
    "Own (with loan)": "own_loan", "Own (no loan)": "own_clear", "Rent": "rent",
    # Commute
    "Own car": "car", "Bike/scooter": "bike", "Metro/train": "metro",
    "Bus": "bus", "Auto/cab": "auto_cab", "Cycle/walk": "cycle", "WFH mostly": "wfh",
    # Loans
    "Home loan": "home", "Car loan": "car", "Education loan": "education",
    "Personal loan": "personal", "Credit card debt": "credit_card", "No loans": "none",
    # Investments
    "Stocks": "stocks", "Mutual Funds": "mf", "Fixed Deposits": "fd",
    "Gold": "gold", "PPF/NPS": "ppf_nps", "Crypto": "crypto",
    "Real Estate": "real_estate", "Don't invest": "none",
    # Diet
    "Vegetarian": "veg", "Vegan": "vegan", "Non-vegetarian": "non_veg",
    "Eggetarian": "eggetarian", "No restrictions": "no_restriction",
    # Dependents
    "Spouse/partner": "spouse", "Children (school)": "school_children",
    "Children (college)": "college_children", "Elderly parents": "parents", "None": "none",
    # Health
    "Diabetes": "diabetes", "Heart condition": "heart", "Asthma/respiratory": "asthma",
    "Thyroid": "thyroid", "Blood pressure": "bp", "Mental health": "mental_health",
    "Prefer not to say": "none",
}

# Options that should clear other selections when picked in multi-select
EXCLUSIVE_OPTIONS = {"No loans", "Don't invest", "None", "Prefer not to say"}


def normalize_answer(label: str) -> str:
    """Convert button label to inference value."""
    return ANSWER_VALUE_MAP.get(label, label.lower().replace(" ", "_"))
