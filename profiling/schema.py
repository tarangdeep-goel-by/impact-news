"""Load and validate question YAML files for user profiling segments."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Option:
    """A single answer option with its node activations."""

    label: str
    value: str
    activations: dict[str, float]


@dataclass
class Question:
    """A profiling question with type, UX hint, and options."""

    id: str
    text: str
    type: str  # single_choice | multi_choice | autocomplete_text
    telegram_ux: str
    max_selections: int = 1
    options: list[Option] = field(default_factory=list)


@dataclass
class Segment:
    """A profiling segment (0-2) with questions and optional trigger condition."""

    segment: int
    name: str
    questions: list[Question]
    trigger: dict | None = None  # condition + message for segments 1, 2


def load_segments(base_dir: str = "profiling/questions") -> list[Segment]:
    """Read all segment YAML files, return sorted by segment number."""
    base = Path(base_dir)
    segments: list[Segment] = []

    for path in sorted(base.glob("segment_*.yaml")):
        with open(path) as f:
            data = yaml.safe_load(f)

        questions: list[Question] = []
        for q in data.get("questions", []):
            options = [
                Option(
                    label=opt["label"],
                    value=opt["value"],
                    activations=opt.get("activations", {}),
                )
                for opt in q.get("options", [])
            ]
            questions.append(
                Question(
                    id=q["id"],
                    text=q["text"],
                    type=q["type"],
                    telegram_ux=q["telegram_ux"],
                    max_selections=q.get("max_selections", 1),
                    options=options,
                )
            )

        segments.append(
            Segment(
                segment=data["segment"],
                name=data["name"],
                questions=questions,
                trigger=data.get("trigger"),
            )
        )

    segments.sort(key=lambda s: s.segment)
    return segments
