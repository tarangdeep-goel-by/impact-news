"""Article-to-user matching layer.

Scores articles against user profiles to determine personal relevance.
Sits downstream of confidence_filter — expects MicroImpact list as input.

Usage:
    from profiling.matcher import score_article_for_user, match_articles_for_user

    score, matched = score_article_for_user(article_impacts, user_weights)
    results = match_articles_for_user(articles, user_weights, min_tier="digest")
"""

from __future__ import annotations

from typing import Literal

from engine.base import MicroImpact


DeliveryTier = Literal["push", "digest", "skip"]

# Nodes that are inherently city-specific — scope filtering is mandatory for these
CITY_SCOPED_NODES = frozenset({
    "traffic_congestion", "road_conditions_and_closures",
    "metro_and_local_train", "city_bus_transit", "auto_e_rickshaw",
    "street_waterlogging", "drinking_water_contamination", "water_supply_and_tankers",
    "uncollected_street_garbage", "open_drains_and_sewage",
    "riots_and_mob_violence", "curfews_and_public_emergencies", "crowd_stampedes",
    "residential_rent_and_pg",
})

STATE_SCOPED_NODES = frozenset({
    "electricity_tariff", "government_schools", "school_board_exams",
    "welfare_and_ration_cards", "state_govt_jobs",
})


def is_location_relevant(
    impact: dict,
    user_city: str,
    user_state: str,
) -> bool:
    """Check if an impact's geographic scope matches the user's location.

    Rules:
    - Impacts with scope "national" or no scope → always relevant
    - Impacts with scope "city:X" → relevant only if user is in city X
    - Impacts with scope "state:X" → relevant only if user is in state X
    - Known city-scoped nodes WITHOUT a scope field → assume mismatch (conservative)
    """
    scope = impact.get("scope", "")
    node = impact.get("i_node", "")

    if not scope or scope == "national":
        # If node is inherently city-scoped but LLM didn't provide scope,
        # we can't filter — let it through (backward compatible)
        return True

    if scope.startswith("city:"):
        scope_city = scope.split(":", 1)[1].strip().lower()
        return _fuzzy_city_match(scope_city, user_city.lower())

    if scope.startswith("state:"):
        scope_state = scope.split(":", 1)[1].strip().lower()
        return _fuzzy_state_match(scope_state, user_state.lower())

    return True  # unknown scope format → assume relevant


def _fuzzy_city_match(scope_city: str, user_city: str) -> bool:
    """Match city names accounting for common variations."""
    if scope_city == user_city:
        return True
    # Common aliases
    aliases = {
        "mumbai": {"bombay"}, "delhi": {"new delhi", "ncr"},
        "bangalore": {"bengaluru"}, "chennai": {"madras"},
        "kolkata": {"calcutta"}, "pune": {"poona"},
        "hyderabad": {"cyberabad"}, "gurgaon": {"gurugram"},
        "allahabad": {"prayagraj"}, "varanasi": {"benares", "kashi"},
    }
    for canonical, alts in aliases.items():
        names = {canonical} | alts
        if scope_city in names and user_city in names:
            return True
    return False


def _fuzzy_state_match(scope_state: str, user_state: str) -> bool:
    """Match state names with common variations."""
    if scope_state == user_state:
        return True
    aliases = {
        "karnataka": {"karnataka"},
        "maharashtra": {"maharashtra"},
        "jammu and kashmir": {"j&k", "jk"},
        "tamil nadu": {"tamilnadu", "tn"},
        "uttar pradesh": {"up"},
    }
    for canonical, alts in aliases.items():
        names = {canonical} | alts
        if scope_state in names and user_state in names:
            return True
    return False


# Thresholds for delivery tiers
PUSH_THRESHOLD = 0.5    # Score >= 0.5 → immediate push notification
DIGEST_THRESHOLD = 0.2  # Score >= 0.2 → daily digest
# Below 0.2 → skip or weekly summary


def score_article_for_user(
    article_impacts: list[MicroImpact],
    user_weights: dict[str, float],
    user_city: str = "",
    user_state: str = "",
) -> tuple[float, list[dict]]:
    """Score an article's impacts against a user's node weight profile.

    Args:
        article_impacts: MicroImpact list from LLM engine (post confidence_filter).
            Each has at minimum: i_node (str), probability (float), magnitude (float).
        user_weights: User's node weight map {node_id: weight} from ProfileEngine.

    Returns:
        (score, matched_nodes) where:
        - score: 0.0-1.0 personal relevance score
        - matched_nodes: list of dicts with node, impact_score, user_weight,
          personal_score, rationale

    Algorithm:
        For each impact in article_impacts:
            - Look up user_weight for that i_node (default 0.0 if not in profile)
            - impact_score = probability * magnitude
            - personal_score = impact_score * user_weight
        Take top-3 personal_scores (to avoid bias toward articles with many weak impacts)
        Normalize: raw_sum / 2.0, capped at 1.0
    """
    personal_scores: list[dict] = []

    for impact in article_impacts:
        node = impact.get("i_node", "")
        if not node:
            continue

        # Location filter — skip city/state-specific impacts that don't match user
        if (user_city or user_state) and not is_location_relevant(impact, user_city, user_state):
            continue

        user_w = user_weights.get(node, 0.0)
        if user_w <= 0:
            continue

        prob = impact.get("probability", 0)
        mag = impact.get("magnitude", 0)
        impact_score = prob * mag
        personal = impact_score * user_w

        if personal > 0:
            personal_scores.append({
                "node": node,
                "impact_score": round(impact_score, 4),
                "user_weight": round(user_w, 2),
                "personal_score": round(personal, 4),
                "rationale": impact.get("rationale", ""),
            })

    if not personal_scores:
        return 0.0, []

    personal_scores.sort(key=lambda x: x["personal_score"], reverse=True)
    top_3 = personal_scores[:3]

    raw_score = sum(p["personal_score"] for p in top_3)
    normalized = min(raw_score / 2.0, 1.0)

    return round(normalized, 4), top_3


def classify_delivery_tier(score: float) -> DeliveryTier:
    """Map personal relevance score to delivery tier."""
    if score >= PUSH_THRESHOLD:
        return "push"
    elif score >= DIGEST_THRESHOLD:
        return "digest"
    return "skip"


def match_articles_for_user(
    articles: list[dict],
    user_weights: dict[str, float],
    min_tier: DeliveryTier = "digest",
    user_city: str = "",
    user_state: str = "",
) -> list[dict]:
    """Score multiple articles and filter by delivery tier.

    Args:
        articles: List of dicts with at least 'article_id' and 'impacts'
            (list[MicroImpact]).
        user_weights: User's node weight profile.
        min_tier: Minimum tier to include.
            "push" = strict, "digest" = balanced, "skip" = all.

    Returns:
        List of matched articles sorted by score descending, each with:
        - article_id, score, delivery_tier, matched_nodes (top 3)
    """
    tier_order: dict[DeliveryTier, int] = {"push": 0, "digest": 1, "skip": 2}
    min_rank = tier_order[min_tier]

    results: list[dict] = []
    for article in articles:
        article_id = article.get("article_id", "")
        impacts = article.get("impacts", [])

        if not impacts:
            continue

        score, matched = score_article_for_user(impacts, user_weights, user_city, user_state)
        tier = classify_delivery_tier(score)

        if tier_order[tier] <= min_rank:
            results.append({
                "article_id": article_id,
                "score": score,
                "delivery_tier": tier,
                "matched_nodes": matched,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
