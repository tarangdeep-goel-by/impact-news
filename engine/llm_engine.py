"""LLM impact engine — uses Gemini with full taxonomy context to score articles."""

from __future__ import annotations

import logging

from engine.base import ImpactResult
from engine.prompt import build_impact_prompt
from engine.taxonomy_context import TaxonomyContext
from pipeline.gemini import GeminiClient, parse_json_response

logger = logging.getLogger(__name__)

VALID_DELAYS = {"IMMEDIATE", "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"}


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a float to [lo, hi]."""
    return max(lo, min(hi, value))


class LLMImpactEngine:
    """Score article impacts by sending full taxonomy context to Gemini.

    Satisfies the ImpactEngine protocol defined in engine.base.
    """

    def __init__(
        self,
        taxonomy: TaxonomyContext,
        gemini: GeminiClient | None = None,
    ) -> None:
        self.taxonomy = taxonomy
        self.gemini = gemini or GeminiClient()
        self._t_trees = taxonomy.format_t_trees()
        self._i_trees = taxonomy.format_i_trees()
        self._valid_i_nodes = taxonomy.get_all_i_node_ids()
        self._valid_t_nodes = taxonomy.get_all_t_node_ids()

    def evaluate_article(self, title: str, summary: str) -> list[ImpactResult]:
        """Call Gemini with full taxonomy context, parse and validate results.

        Args:
            title: Article headline
            summary: Article body/summary text

        Returns:
            List of ImpactResult dicts, sorted by probability * magnitude descending.
            Returns empty list on unrecoverable errors.
        """
        prompt = build_impact_prompt(self._t_trees, self._i_trees, title, summary)

        # Call Gemini — retry once on parse failure
        parsed = self._call_and_parse(prompt)
        if parsed is None:
            return []

        triggers = parsed.get("triggers", [])
        impacts = parsed.get("impacts", [])

        if not isinstance(triggers, list):
            triggers = []
        if not isinstance(impacts, list):
            logger.warning("Gemini returned non-list impacts: %s", type(impacts))
            return []

        # Validate triggers
        valid_triggers = [t for t in triggers if t in self._valid_t_nodes]
        if triggers and not valid_triggers:
            logger.warning(
                "All Gemini triggers unknown: %s", triggers,
            )

        # Convert to ImpactResult
        results: list[ImpactResult] = []
        for imp in impacts:
            if not isinstance(imp, dict):
                continue

            node = imp.get("node", "")
            if node not in self._valid_i_nodes:
                logger.warning("Gemini returned unknown I-node: %s — skipping", node)
                continue

            probability = _clamp(float(imp.get("probability", 0)))
            magnitude = _clamp(float(imp.get("magnitude", 0)))

            polarity = int(imp.get("polarity", 1))
            if polarity not in (1, -1):
                polarity = 1

            delay = str(imp.get("delay", "SHORT_TERM"))
            if delay not in VALID_DELAYS:
                logger.warning("Invalid delay '%s' for node %s — defaulting to SHORT_TERM", delay, node)
                delay = "SHORT_TERM"

            path = valid_triggers + [node] if valid_triggers else [node]

            results.append(ImpactResult(
                node=node,
                probability=probability,
                magnitude=magnitude,
                polarity=polarity,
                delay=delay,
                mechanism=str(imp.get("mechanism", "")),
                path=path,
            ))

        # Sort by probability * magnitude descending
        results.sort(key=lambda x: x["probability"] * x["magnitude"], reverse=True)
        return results

    def _call_and_parse(self, prompt: str) -> dict | None:
        """Call Gemini and parse JSON response, retrying once on parse failure."""
        for attempt in range(2):
            try:
                raw = self.gemini.call(prompt)
            except Exception:
                logger.error("Gemini API call failed (attempt %d)", attempt + 1, exc_info=True)
                if attempt == 0:
                    continue
                return None

            try:
                parsed = parse_json_response(raw)
            except (ValueError, Exception):
                logger.warning(
                    "JSON parse failed (attempt %d): %.200s", attempt + 1, raw, exc_info=True,
                )
                if attempt == 0:
                    continue
                return None

            if not isinstance(parsed, dict):
                logger.warning("Expected dict from Gemini, got %s", type(parsed))
                if attempt == 0:
                    continue
                return None

            return parsed

        return None
