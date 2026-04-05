"""Tier 1 article classifier — relevance check + macro shifts + event matching."""

from __future__ import annotations

import logging
import time as _time

from engine.base import ClassificationResult, ClassificationResultV2, ClassificationResultV3
from engine.prompts.classify import build_classify_prompt
from pipeline.gemini import GeminiClient, parse_json_response

logger = logging.getLogger(__name__)


class ArticleClassifier:
    """Tier 1: classify article relevance, identify T-node triggers, and match events.

    Uses flash-lite model with T-world taxonomy context for precise trigger identification.
    """

    def __init__(self, gemini: GeminiClient, event_store, taxonomy) -> None:
        self.gemini = gemini
        self.event_store = event_store
        self._t_trees = taxonomy.format_t_trees()

    def classify(self, title: str, summary: str) -> ClassificationResultV2 | None:
        """Classify an article's relevance, identify triggers, and match to existing event.

        Returns ClassificationResultV2 or None after all retries exhausted.
        """
        active_events = self.event_store.get_event_summary_list()
        prompt = build_classify_prompt(self._t_trees, active_events, title, summary)

        parsed = self._call_and_parse(prompt)
        if parsed is None:
            return None

        relevant = bool(parsed.get("relevant", False))

        if not relevant:
            return ClassificationResultV2(
                relevant=False,
                triggers=[],
                exclude_l1s=[],
                event_match=None,
                event_name=None,
                reason=parsed.get("reason", "not relevant"),
            )

        # Parse triggers
        triggers = parsed.get("triggers", [])
        if not isinstance(triggers, list):
            triggers = []

        # Parse exclude_l1s
        exclude_l1s = parsed.get("exclude_l1s", [])
        if not isinstance(exclude_l1s, list):
            exclude_l1s = []

        # Parse event match (same as before)
        event_match = parsed.get("event_match")
        if isinstance(event_match, dict):
            confidence = float(event_match.get("confidence", 0))
            if confidence < 0.7:
                event_match = None

        return ClassificationResultV2(
            relevant=True,
            triggers=triggers,
            exclude_l1s=exclude_l1s,
            event_match=event_match,
            event_name=parsed.get("event_name"),
            reason=None,
        )

    def classify_v3(self, title: str, summary: str) -> ClassificationResultV3 | None:
        """Classify with MacroShift model (V3)."""
        # Use V3 event list with macro_shifts (trajectory) if available
        if hasattr(self.event_store, 'get_event_summary_list_v3'):
            active_events = self.event_store.get_event_summary_list_v3()
        else:
            active_events = self.event_store.get_event_summary_list()
        prompt = build_classify_prompt(self._t_trees, active_events, title, summary)

        parsed = self._call_and_parse(prompt)
        if parsed is None:
            return None

        relevant = bool(parsed.get("relevant", False))

        if not relevant:
            return ClassificationResultV3(
                relevant=False,
                macro_shifts=[],
                exclude_l1s=[],
                event_match=None,
                event_name=None,
                reason=parsed.get("reason", "not relevant"),
            )

        # Parse macro_shifts
        macro_shifts = parsed.get("macro_shifts", [])
        if not isinstance(macro_shifts, list):
            macro_shifts = []

        # Validate trajectory values
        valid_trajectories = {"escalating", "deescalating", "status_quo", "disruption"}
        for shift in macro_shifts:
            if shift.get("trajectory") not in valid_trajectories:
                shift["trajectory"] = "escalating"  # safe default

        # Parse exclude_l1s
        exclude_l1s = parsed.get("exclude_l1s", [])
        if not isinstance(exclude_l1s, list):
            exclude_l1s = []

        # Parse event match
        event_match = parsed.get("event_match")
        if isinstance(event_match, dict):
            confidence = float(event_match.get("confidence", 0))
            if confidence < 0.7:
                event_match = None

        return ClassificationResultV3(
            relevant=True,
            macro_shifts=macro_shifts,
            exclude_l1s=exclude_l1s,
            event_match=event_match,
            event_name=parsed.get("event_name"),
            reason=None,
        )

    def _call_and_parse(self, prompt: str) -> dict | None:
        """Call Gemini flash-lite with retry + backoff. Returns parsed dict or None."""
        max_attempts = 4
        for attempt in range(max_attempts):
            try:
                raw = self.gemini.call(prompt)
            except Exception as exc:
                logger.error("Tier 1 API call failed (attempt %d)", attempt + 1, exc_info=True)
                err_str = str(exc)
                if ("429" in err_str or "503" in err_str) and attempt < max_attempts - 1:
                    wait = 2 ** attempt * 5
                    logger.info("Tier 1 rate limited, waiting %ds", wait)
                    _time.sleep(wait)
                    continue
                if attempt < max_attempts - 1:
                    continue
                return None

            try:
                parsed = parse_json_response(raw)
            except (ValueError, Exception):
                logger.warning("Tier 1 JSON parse failed (attempt %d): %.200s", attempt + 1, raw, exc_info=True)
                if attempt < max_attempts - 1:
                    continue
                return None

            if not isinstance(parsed, dict):
                logger.warning("Tier 1 expected dict, got %s", type(parsed))
                if attempt < max_attempts - 1:
                    continue
                return None

            return parsed

        return None
