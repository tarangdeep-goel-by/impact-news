"""Tier 2 impact analyzer — deep analysis with full taxonomy context."""

from __future__ import annotations

import logging

from config import settings
from engine.base import AnalysisResult, AnalysisResultV2, ImpactResult, TriggerInstance, ImpactEdgeV2
from engine.prompts.analyze_new import build_analyze_new_prompt
from engine.prompts.analyze_update import build_analyze_update_prompt
from engine.taxonomy_context import TaxonomyContext
from pipeline.gemini import GeminiClient, parse_json_response

logger = logging.getLogger(__name__)

VALID_DELAYS = {"IMMEDIATE", "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"}


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a float to [lo, hi]."""
    return max(lo, min(hi, value))


class ImpactAnalyzer:
    """Tier 2: Deep impact analysis with full taxonomy context.

    Uses gemini-3.1-pro-preview for better reasoning on causal chains.
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

    def analyze_new(self, title: str, summary: str) -> AnalysisResult:
        """Full analysis for a new event (no prior context)."""
        prompt = build_analyze_new_prompt(self._t_trees, self._i_trees, title, summary)
        return self._analyze(prompt)

    def analyze_update(self, title: str, summary: str, event: dict) -> AnalysisResult:
        """Update analysis given existing event context."""
        prompt = build_analyze_update_prompt(
            self._t_trees, self._i_trees, title, summary, event,
        )
        return self._analyze(prompt)

    def _analyze(self, prompt: str) -> AnalysisResult:
        """Shared analysis logic — call Gemini pro, parse, validate."""
        parsed = self._call_and_parse(prompt)
        if parsed is None:
            return AnalysisResult(
                triggers=[], impacts=[], stage="new",
                summary="", is_relevant=False, rejection_reason="api_error",
            )

        # Handle no-impact response
        if parsed.get("no_impact"):
            return AnalysisResult(
                triggers=[], impacts=[], stage="new",
                summary="", is_relevant=False,
                rejection_reason=parsed.get("reason", "no mass citizen impact"),
            )

        triggers = parsed.get("triggers", [])
        impacts_raw = parsed.get("impacts", [])

        if not isinstance(triggers, list):
            triggers = []
        if not isinstance(impacts_raw, list):
            logger.warning("Gemini returned non-list impacts: %s", type(impacts_raw))
            impacts_raw = []

        # Validate triggers
        valid_triggers = [t for t in triggers if t in self._valid_t_nodes]
        if triggers and not valid_triggers:
            logger.warning("All Gemini triggers unknown: %s", triggers)

        # Convert to ImpactResult
        results: list[ImpactResult] = []
        for imp in impacts_raw:
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

        results.sort(key=lambda x: x["probability"] * x["magnitude"], reverse=True)

        stage = parsed.get("stage", "new")
        if stage not in ("new", "escalating", "stable", "resolved"):
            stage = "new"

        summary_text = parsed.get("summary", "")

        return AnalysisResult(
            triggers=valid_triggers,
            impacts=results,
            stage=stage,
            summary=summary_text,
            is_relevant=len(results) > 0,
            rejection_reason=None,
        )

    def _call_and_parse(self, prompt: str) -> dict | None:
        """Call Gemini pro and parse JSON response, with backoff on rate limits."""
        import time as _time

        max_attempts = 4
        for attempt in range(max_attempts):
            try:
                raw = self.gemini.call(prompt, model=settings.gemini_pro_model)
            except Exception as exc:
                logger.error("Gemini API call failed (attempt %d)", attempt + 1, exc_info=True)
                err_str = str(exc)
                if ("429" in err_str or "503" in err_str) and attempt < max_attempts - 1:
                    wait = 2 ** attempt * 5
                    logger.info("Rate limited, waiting %ds before retry", wait)
                    _time.sleep(wait)
                    continue
                if attempt < max_attempts - 1:
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

    # -- V2 methods: Causal Edges architecture --------------------------------

    def analyze_new_v2(
        self,
        title: str,
        summary: str,
        triggers: list[dict],
        i_trees: str,
    ) -> AnalysisResultV2:
        """Tier 2 analysis for new events with pre-identified triggers and filtered taxonomy."""
        prompt = build_analyze_new_prompt(triggers, i_trees, title, summary)
        return self._analyze_v2(prompt, triggers)

    def analyze_update_v2(
        self,
        title: str,
        summary: str,
        triggers: list[dict],
        i_trees: str,
        existing_instances: list[dict],
    ) -> AnalysisResultV2:
        """Tier 2 upsert analysis with existing causal edges."""
        prompt = build_analyze_update_prompt(
            triggers, i_trees, title, summary, existing_instances,
        )
        return self._analyze_v2(prompt, triggers)

    def _analyze_v2(self, prompt: str, triggers: list[dict]) -> AnalysisResultV2:
        """Shared v2 analysis logic — call Gemini pro, parse, validate causal edges."""
        parsed = self._call_and_parse(prompt)
        if parsed is None:
            return AnalysisResultV2(
                trigger_instances=[], stage="new",
                summary="", is_relevant=False, rejection_reason="api_error",
            )

        # Handle no-impact response
        if parsed.get("no_impact"):
            return AnalysisResultV2(
                trigger_instances=[], stage="new",
                summary="", is_relevant=False,
                rejection_reason=parsed.get("reason", "no mass citizen impact"),
            )

        raw_instances = parsed.get("trigger_instances", [])
        if not isinstance(raw_instances, list):
            logger.warning("Gemini returned non-list trigger_instances: %s", type(raw_instances))
            raw_instances = []

        # Validate and build TriggerInstance list
        validated: list[dict] = []
        for ti in raw_instances:
            if not isinstance(ti, dict):
                continue

            t_node = ti.get("t_node", "")
            if t_node and t_node not in self._valid_t_nodes:
                logger.warning("Unknown T-node from Gemini: %s — keeping anyway", t_node)

            # Validate edges
            valid_edges: list[dict] = []
            for edge in ti.get("edges", []):
                if not isinstance(edge, dict):
                    continue

                i_node = edge.get("i_node", "")
                if i_node not in self._valid_i_nodes:
                    logger.warning("Unknown I-node: %s — skipping", i_node)
                    continue

                probability = _clamp(float(edge.get("probability", 0)))
                magnitude = _clamp(float(edge.get("magnitude", 0)))

                polarity = int(edge.get("polarity", 1))
                if polarity not in (1, -1):
                    polarity = 1

                delay_days = int(edge.get("delay_days", 14))
                if delay_days < 1:
                    delay_days = 1
                if delay_days > 365:
                    delay_days = 365

                valid_edge: dict = {
                    "i_node": i_node,
                    "probability": probability,
                    "magnitude": magnitude,
                    "delay_days": delay_days,
                    "polarity": polarity,
                    "mechanism": str(edge.get("mechanism", "")),
                }
                # Preserve ID if present (for upsert)
                if edge.get("id"):
                    valid_edge["id"] = edge["id"]

                valid_edges.append(valid_edge)

            # Sort edges by probability * magnitude descending
            valid_edges.sort(key=lambda e: e["probability"] * e["magnitude"], reverse=True)

            if valid_edges:
                instance: dict = {
                    "t_node": t_node,
                    "context": ti.get("context", ""),
                    "edges": valid_edges,
                }
                # Preserve ID if present (for upsert)
                if ti.get("id"):
                    instance["id"] = ti["id"]
                validated.append(instance)

        stage = parsed.get("stage", "new")
        if stage not in ("new", "escalating", "stable", "resolved"):
            stage = "new"

        return AnalysisResultV2(
            trigger_instances=validated,
            stage=stage,
            summary=parsed.get("summary", ""),
            is_relevant=len(validated) > 0,
            rejection_reason=None,
        )
