"""ProfileEngine — builds user node-weight profiles from questionnaire answers."""

from __future__ import annotations

from difflib import get_close_matches

from profiling.schema import Question, load_segments
from profiling.universals import (
    CITY_TIER_ACTIVATIONS,
    SEASONAL_ACTIVATIONS,
    UNIVERSAL_FLOOR,
    UNIVERSAL_NODES,
    load_city_lookup,
)


class ProfileEngine:
    """Computes user node-weight profiles from questionnaire answers."""

    def __init__(self, base_dir: str = "profiling") -> None:
        self.segments = load_segments(f"{base_dir}/questions")
        self.city_lookup = load_city_lookup(f"{base_dir}/cities.yaml")
        self._questions_by_id: dict[str, Question] = {
            q.id: q for seg in self.segments for q in seg.questions
        }

    def resolve_city(self, city_input: str) -> tuple[str, str, dict]:
        """Fuzzy match city input to city_lookup. Return (tier, state, seasonal_flags).

        Falls back to _default_rural if no match.
        """
        key = city_input.strip().lower()

        # Exact match
        if key in self.city_lookup:
            info = self.city_lookup[key]
            return info["tier"], info.get("state", ""), info.get("seasonal", {})

        # Fuzzy match against all keys
        candidates = list(self.city_lookup.keys())
        matches = get_close_matches(key, candidates, n=1, cutoff=0.6)
        if matches:
            info = self.city_lookup[matches[0]]
            return info["tier"], info.get("state", ""), info.get("seasonal", {})

        # Default fallback
        fallback = self.city_lookup.get("_default_rural", {})
        return fallback.get("tier", "rural"), fallback.get("state", ""), fallback.get("seasonal", {})

    def process_answer(
        self, question_id: str, answer_value: str | list[str]
    ) -> dict[str, float]:
        """Given a question ID and answer value(s), return activation dict.

        For multi_choice, merge activations from all selected options (MAX wins).
        """
        question = self._questions_by_id.get(question_id)
        if not question:
            return {}

        # Normalize to list
        values = answer_value if isinstance(answer_value, list) else [answer_value]

        # Build option lookup
        option_map = {opt.value: opt for opt in question.options}

        merged: dict[str, float] = {}
        for val in values:
            opt = option_map.get(val)
            if not opt:
                continue
            for node_id, weight in opt.activations.items():
                merged[node_id] = max(merged.get(node_id, 0.0), weight)

        return merged

    def compute_profile(
        self, raw_answers: dict[str, str | list[str]]
    ) -> dict[str, float]:
        """Compute full node weight map from all answers + universals + city-tier.

        Steps:
        1. Start with UNIVERSAL_NODES
        2. If s0_city answered, add city-tier + seasonal activations
        3. For each answered question, merge activations (MAX wins per node)
        4. Apply universal floor (universals can't go below 0.5)
        5. Return {node_id: weight} dict
        """
        weights: dict[str, float] = dict(UNIVERSAL_NODES)

        # City-tier and seasonal activations
        city_tier_nodes: dict[str, float] = {}
        if "s0_city" in raw_answers:
            tier, state, seasonal = self.resolve_city(str(raw_answers["s0_city"]))
            city_tier_nodes = dict(CITY_TIER_ACTIVATIONS.get(tier, {}))

            # Add seasonal activations for flags that are True
            for flag, flag_active in seasonal.items():
                if flag_active and flag in SEASONAL_ACTIVATIONS:
                    for node_id, w in SEASONAL_ACTIVATIONS[flag].items():
                        city_tier_nodes[node_id] = max(
                            city_tier_nodes.get(node_id, 0.0), w
                        )

        # Merge city-tier defaults into weights (MAX wins)
        for node_id, w in city_tier_nodes.items():
            weights[node_id] = max(weights.get(node_id, 0.0), w)

        # Process each answered question
        explicit_zeros: set[str] = set()
        for qid, answer in raw_answers.items():
            if qid == "s0_city":
                continue  # already handled via city-tier
            activations = self.process_answer(qid, answer)
            for node_id, w in activations.items():
                if w == 0.0:
                    explicit_zeros.add(node_id)
                else:
                    weights[node_id] = max(weights.get(node_id, 0.0), w)

        # Explicit 0.0 from answers suppresses city-tier defaults but NOT universals
        for node_id in explicit_zeros:
            if node_id not in UNIVERSAL_NODES and node_id not in weights:
                # Only suppress if no positive source set it
                pass
            elif node_id not in UNIVERSAL_NODES:
                # Check if a positive answer also set this node
                if weights.get(node_id, 0.0) == city_tier_nodes.get(node_id, 0.0):
                    # Only city-tier contributed — suppress it
                    if node_id in weights and node_id in city_tier_nodes:
                        del weights[node_id]

        # Apply universal floor
        for node_id in UNIVERSAL_NODES:
            if node_id in weights:
                weights[node_id] = max(weights[node_id], UNIVERSAL_FLOOR)

        return weights

    def get_next_question(
        self, answered_ids: set[str], current_segment: int
    ) -> Question | None:
        """Return next unanswered question in current segment, or None if complete."""
        for seg in self.segments:
            if seg.segment != current_segment:
                continue
            for q in seg.questions:
                if q.id not in answered_ids:
                    return q
        return None

    def get_segment_questions(self, segment: int) -> list[Question]:
        """Return all questions for a given segment."""
        for seg in self.segments:
            if seg.segment == segment:
                return seg.questions
        return []

    def apply_feedback_adjustments(
        self,
        current_weights: dict[str, float],
        adjustments: dict[str, float],
    ) -> dict[str, float]:
        """Apply relative weight adjustments from feedback.

        Args:
            current_weights: Current node weight profile.
            adjustments: {node_id: delta} — positive boosts, negative suppresses.

        Returns:
            Updated weights dict (mutated in place).
        """
        for node, delta in adjustments.items():
            current = current_weights.get(node, 0.5 if delta > 0 else 0.0)
            new = max(0.0, min(1.0, current + delta))

            # Universal floor still applies
            if node in UNIVERSAL_NODES:
                new = max(new, UNIVERSAL_FLOOR)

            if new > 0:
                current_weights[node] = round(new, 2)
            elif node in current_weights and node not in UNIVERSAL_NODES:
                del current_weights[node]

        return current_weights

    def recompute_profile(
        self,
        raw_answers: dict[str, str | list[str]],
        depth_answers: dict | None = None,
        adjustments_log: list[dict[str, float]] | None = None,
    ) -> dict[str, float]:
        """Full layered profile recomputation.

        Layers applied in order:
        1. Base profile from intake answers (compute_profile)
        2. Depth answer adjustments (from diagnostic follow-ups)
        3. Cumulative feedback adjustments
        4. Universal floor
        """
        # Layer 1: base profile
        weights = self.compute_profile(raw_answers)

        # Layer 2: depth adjustments (if any)
        # Depth answers don't have direct node adjustments stored —
        # they're applied at feedback time and accumulated in adjustments_log

        # Layer 3: accumulated adjustments
        if adjustments_log:
            for adj in adjustments_log:
                self.apply_feedback_adjustments(weights, adj)

        return weights
