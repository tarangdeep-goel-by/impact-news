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


class ClassificationResult(TypedDict):
    """Tier 1 classification output."""
    relevant: bool
    event_match: dict | None   # {"event_id": str, "confidence": float} or None
    category: str | None
    headline_triggers: list[str]
    event_name: str | None     # Only when relevant=True and event_match is None
    reason: str | None         # Only when relevant=False


class AnalysisResult(TypedDict):
    """Tier 2 deep analysis output."""
    triggers: list[str]
    impacts: list[ImpactResult]
    stage: str              # new | escalating | stable | resolved
    summary: str            # Event summary
    is_relevant: bool
    rejection_reason: str | None


# ---------------------------------------------------------------------------
# V2 types — Causal Edges architecture
# ---------------------------------------------------------------------------


class TriggerContext(TypedDict):
    """Tier 1 output: a trigger identified in an article."""
    t_node: str           # T-world node ID
    context: str          # 1-line: WHY this trigger is activated


class ImpactEdgeV2(TypedDict, total=False):
    """A single causal edge from a trigger to an impact."""
    id: str               # UUID — present for existing edges, absent for new
    i_node: str           # I-world node ID
    probability: float    # 0-1
    magnitude: float      # 0-1
    delay_days: int       # Numeric days until citizen feels impact
    polarity: int         # +1 or -1
    mechanism: str        # 1-line causal chain


class TriggerInstance(TypedDict, total=False):
    """A trigger with its impact edges."""
    id: str               # UUID — present for existing instances, absent for new
    t_node: str
    context: str
    edges: list[ImpactEdgeV2]


class ClassificationResultV2(TypedDict):
    """Tier 1 output with T-tree awareness and exclusion spotlight."""
    relevant: bool
    triggers: list[TriggerContext]   # T-nodes with context
    exclude_l1s: list[str]           # I-world L1 codes to EXCLUDE (e.g., ["I7", "I11"])
    event_match: dict | None         # {"event_id": str, "confidence": float} or None
    event_name: str | None           # Only when relevant=True and event_match is None
    reason: str | None               # Only when relevant=False


class AnalysisResultV2(TypedDict):
    """Tier 2 output with causal edges."""
    trigger_instances: list[TriggerInstance]
    stage: str              # new | escalating | stable | resolved
    summary: str            # Event summary
    is_relevant: bool
    rejection_reason: str | None


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
