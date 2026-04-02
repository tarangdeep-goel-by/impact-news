"""Impact engine protocol — common interface for graph and LLM engines."""

from __future__ import annotations

from typing import Protocol, TypedDict


class ImpactResult(TypedDict):
    """Single impact assessment for one node."""
    node: str           # I-tree node ID (e.g., "retail_petrol", "home_loan_emi")
    probability: float  # 0-1, likelihood this node is affected
    magnitude: float    # 0-1, how severely affected
    polarity: int       # +1 (increases) or -1 (decreases)
    delay: str          # IMMEDIATE / SHORT_TERM / MEDIUM_TERM / LONG_TERM
    mechanism: str      # 1-line causal chain explanation
    path: list[str]     # [trigger_node, ..., impact_node]


class ImpactEngine(Protocol):
    """Protocol for impact scoring engines."""

    def evaluate_article(self, title: str, summary: str) -> list[ImpactResult]:
        """Score an article's impacts on I-tree leaf nodes.

        Args:
            title: Article headline
            summary: Article body/summary text

        Returns:
            List of ImpactResult dicts, sorted by probability * magnitude descending.
        """
        ...
