"""Post-LLM confidence filter for surfacing impacts to users.

Sits between the LLM analyzer output and user delivery. Classifies each
MicroImpact into confidence tiers based on probability, magnitude, and order.

Usage:
    from engine.confidence_filter import filter_impacts, ConfidenceTier

    result = analyzer.analyze_new_v3(...)
    filtered = filter_impacts(result["micro_impacts"])

    # Only show high-confidence impacts to users
    for imp in filtered:
        if imp["confidence_tier"] == "high":
            deliver_to_user(imp)
"""

from __future__ import annotations

from typing import Literal

from engine.base import MicroImpact

ConfidenceTier = Literal["high", "medium", "low"]

# Thresholds derived from eval: hits avg prob=0.81, FPs avg prob=0.63
# At prob >= 0.7: precision jumps from 44% to 64% while keeping 82% recall
DEFAULT_THRESHOLDS = {
    "high": {"min_probability": 0.7, "min_score": 0.4},
    "medium": {"min_probability": 0.5, "min_score": 0.2},
    # Everything else is "low"
}


def compute_score(impact: MicroImpact) -> float:
    """Composite confidence score: probability * magnitude."""
    return impact.get("probability", 0) * impact.get("magnitude", 0)


def classify_confidence(
    impact: MicroImpact,
    thresholds: dict | None = None,
) -> ConfidenceTier:
    """Classify a single impact into a confidence tier."""
    t = thresholds or DEFAULT_THRESHOLDS
    prob = impact.get("probability", 0)
    score = compute_score(impact)

    if prob >= t["high"]["min_probability"] and score >= t["high"]["min_score"]:
        return "high"
    if prob >= t["medium"]["min_probability"] and score >= t["medium"]["min_score"]:
        return "medium"
    return "low"


def filter_impacts(
    impacts: list[MicroImpact],
    min_tier: ConfidenceTier = "medium",
    thresholds: dict | None = None,
) -> list[dict]:
    """Filter and annotate impacts with confidence tiers.

    Args:
        impacts: Raw MicroImpact list from LLM analyzer.
        min_tier: Minimum tier to include. "high" = strict, "medium" = balanced, "low" = all.
        thresholds: Custom threshold overrides.

    Returns:
        Filtered list of impacts with added "confidence_tier" and "score" fields.
    """
    tier_order = {"high": 0, "medium": 1, "low": 2}
    min_rank = tier_order[min_tier]

    result = []
    for imp in impacts:
        tier = classify_confidence(imp, thresholds)
        if tier_order[tier] <= min_rank:
            annotated = dict(imp)
            annotated["confidence_tier"] = tier
            annotated["score"] = compute_score(imp)
            result.append(annotated)

    return result


def filter_stats(impacts: list[MicroImpact], thresholds: dict | None = None) -> dict:
    """Return counts by confidence tier (for logging/debugging)."""
    tiers = {"high": 0, "medium": 0, "low": 0}
    for imp in impacts:
        tier = classify_confidence(imp, thresholds)
        tiers[tier] += 1
    return tiers
