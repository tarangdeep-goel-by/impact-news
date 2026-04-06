"""Feedback-driven diagnostic question engine.

Selects diagnostic, depth, and deepening questions based on:
- Which article was delivered and its matched nodes
- Whether the user said relevant or irrelevant
- What the user's profile is missing (depth gaps)
- Rate limiting (max questions per day)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticOption:
    label: str
    action: str = ""           # "follow_up" or "flag_location" or ""
    follow_up_id: str = ""     # ID of depth question to ask next
    depth_update: dict = field(default_factory=dict)   # key-value to store in depth_answers
    adjustments: dict[str, float] = field(default_factory=dict)  # node: delta


@dataclass
class DiagnosticQuestion:
    id: str
    trigger: dict              # {feedback, matched_nodes_any, profile_missing}
    text: str
    options: list[DiagnosticOption]


@dataclass
class DepthOption:
    label: str
    value: str
    depth_update: dict = field(default_factory=dict)
    adjustments: dict[str, float] = field(default_factory=dict)


@dataclass
class DepthQuestion:
    id: str
    text: str
    type: str = "single_choice"  # single_choice or multi_choice
    options: list[DepthOption] = field(default_factory=list)


@dataclass
class DeepeningQuestion:
    id: str
    trigger: dict
    text: str
    options: list[DiagnosticOption]  # Same structure as diagnostic options


class DiagnosticsEngine:
    """Loads and selects diagnostic/depth/deepening questions."""

    def __init__(self, yaml_path: str = "profiling/questions/diagnostics.yaml"):
        path = Path(yaml_path)
        with open(path) as f:
            data = yaml.safe_load(f)

        self.diagnostics = self._parse_diagnostics(data.get("diagnostic_questions", []))
        self.depth_questions = self._parse_depth(data.get("depth_questions", []))
        self.deepening = self._parse_deepening(data.get("deepening_questions", []))

        self._depth_by_id = {q.id: q for q in self.depth_questions}

    def select_diagnostic(
        self,
        matched_nodes: list[str],
        depth_answers: dict,
    ) -> DiagnosticQuestion | None:
        """Select the best diagnostic question for a negative feedback event.

        Args:
            matched_nodes: node IDs that matched the article to this user
            depth_answers: user's current depth_answers dict (to check profile_missing)

        Returns:
            Best matching DiagnosticQuestion, or None if no match.
        """
        for diag in self.diagnostics:
            trigger = diag.trigger

            # Check matched_nodes overlap
            required_nodes = set(trigger.get("matched_nodes_any", []))
            if required_nodes and not required_nodes.intersection(matched_nodes):
                continue

            # Check profile_missing
            missing_key = trigger.get("profile_missing", "")
            if missing_key and missing_key in depth_answers:
                continue  # Already answered this depth dimension

            return diag

        return None

    def select_deepening(
        self,
        matched_nodes: list[str],
        depth_answers: dict,
        feedback_count: int,
    ) -> DeepeningQuestion | None:
        """Select a deepening question for a positive feedback event.

        Rate-limited by min_feedback_count in trigger.
        """
        for deep in self.deepening:
            trigger = deep.trigger

            # Check matched_nodes overlap
            required_nodes = set(trigger.get("matched_nodes_any", []))
            if required_nodes and not required_nodes.intersection(matched_nodes):
                continue

            # Check profile_missing
            missing_key = trigger.get("profile_missing", "")
            if missing_key and missing_key in depth_answers:
                continue

            # Check minimum feedback count
            min_count = trigger.get("min_feedback_count", 0)
            if feedback_count < min_count:
                continue

            return deep

        return None

    def get_depth_question(self, question_id: str) -> DepthQuestion | None:
        """Look up a depth follow-up question by ID."""
        return self._depth_by_id.get(question_id)

    # --- Parsing ---

    def _parse_diagnostics(self, raw: list[dict]) -> list[DiagnosticQuestion]:
        result = []
        for item in raw:
            options = [
                DiagnosticOption(
                    label=o["label"],
                    action=o.get("action", ""),
                    follow_up_id=o.get("follow_up_id", ""),
                    depth_update=o.get("depth_update", {}),
                    adjustments=o.get("adjustments", {}),
                )
                for o in item.get("options", [])
            ]
            result.append(DiagnosticQuestion(
                id=item["id"],
                trigger=item.get("trigger", {}),
                text=item["text"],
                options=options,
            ))
        return result

    def _parse_depth(self, raw: list[dict]) -> list[DepthQuestion]:
        result = []
        for item in raw:
            options = [
                DepthOption(
                    label=o["label"],
                    value=o.get("value", ""),
                    depth_update=o.get("depth_update", {}),
                    adjustments=o.get("adjustments", {}),
                )
                for o in item.get("options", [])
            ]
            result.append(DepthQuestion(
                id=item["id"],
                text=item["text"],
                type=item.get("type", "single_choice"),
                options=options,
            ))
        return result

    def _parse_deepening(self, raw: list[dict]) -> list[DeepeningQuestion]:
        result = []
        for item in raw:
            options = [
                DiagnosticOption(
                    label=o["label"],
                    action=o.get("action", ""),
                    follow_up_id=o.get("follow_up_id", ""),
                    depth_update=o.get("depth_update", {}),
                    adjustments=o.get("adjustments", {}),
                )
                for o in item.get("options", [])
            ]
            result.append(DeepeningQuestion(
                id=item["id"],
                trigger=item.get("trigger", {}),
                text=item["text"],
                options=options,
            ))
        return result
