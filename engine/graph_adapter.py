"""Graph engine adapter — wraps CausalMarkovEngine to ImpactEngine protocol."""

from __future__ import annotations

import logging

from engine.base import ImpactResult
from graph.embeddings import NodeMatcher
from graph.graph import ImpactGraph
from graph.markov_engine import CausalMarkovEngine
from graph.merge import TaxonomyMerger
from graph.migrate_weights import apply_defaults
from pipeline.gemini import GeminiClient, parse_json_response
from config import settings

logger = logging.getLogger(__name__)

# Single-article tag extraction prompt (matcher.py batches; we need single-shot)
TAG_EXTRACTION_PROMPT = """You are a news impact analyst for the Indian economy.
Given a news article, extract what real-world things it AFFECTS (not just mentions).

Return tags as lowercase_underscored identifiers (e.g. "crude_oil", "home_loan_emi").
Think about second and third order effects.

Output ONLY a JSON array of strings: ["tag1", "tag2", ...]

Article:
Title: {title}
Summary: {summary}"""


class GraphImpactEngine:
    """Wraps existing graph pipeline to satisfy ImpactEngine protocol."""

    def __init__(self) -> None:
        # Merge taxonomy YAML sources into a fresh DiGraph
        merger = TaxonomyMerger()
        G = merger.merge()
        apply_defaults(G)

        # CausalMarkovEngine operates on the raw nx.DiGraph
        self.engine = CausalMarkovEngine(
            G,
            i_world_boost=settings.i_world_boost,
            category_penalty=settings.category_penalty,
            leaf_boost_l4=settings.leaf_boost_l4,
            leaf_boost_l3=settings.leaf_boost_l3,
        )

        # NodeMatcher expects an ImpactGraph wrapper — inject merged DiGraph
        ig = ImpactGraph()
        ig.g = G
        self.matcher = NodeMatcher(graph=ig)
        self.matcher.build_index()

        self.gemini = GeminiClient()
        self.graph = G

    def evaluate_article(self, title: str, summary: str) -> list[ImpactResult]:
        """Extract tags from article, match to graph nodes, run CSP engine."""
        # Step 1: Extract tags via Gemini
        prompt = TAG_EXTRACTION_PROMPT.format(title=title, summary=summary)
        try:
            raw = self.gemini.call(prompt)
            tags = parse_json_response(raw)
            if not isinstance(tags, list):
                tags = []
        except Exception as e:
            logger.error("Tag extraction failed: %s", e)
            tags = []

        if not tags:
            return []

        # Step 2: Match tags to graph nodes via FAISS embeddings
        matched_nodes: set[str] = set()
        for tag in tags:
            matches = self.matcher.match(
                str(tag), threshold=settings.match_threshold, top_k=3,
            )
            for nm in matches:
                matched_nodes.add(nm.node_id)

        if not matched_nodes:
            return []

        # Step 3: Run CSP engine per matched trigger node, keep best per target
        best: dict[str, tuple[float, dict]] = {}  # node -> (cis, raw_result)
        for trigger in matched_nodes:
            if trigger not in self.graph:
                continue
            results = self.engine.evaluate_impact(trigger)
            for r in results:
                node = r["node"]
                cis = r.get("cis", r["probability"] * r["magnitude"])
                if node not in best or cis > best[node][0]:
                    best[node] = (cis, r)

        # Step 4: Convert to ImpactResult protocol
        impact_results: list[ImpactResult] = []
        for _cis, r in best.values():
            path = r.get("path", [])
            impact_results.append(ImpactResult(
                node=r["node"],
                probability=r["probability"],
                magnitude=r["magnitude"],
                polarity=r["polarity"],
                delay=r["delay"],
                mechanism=" -> ".join(path),
                path=path,
            ))

        # Sort by probability * magnitude descending (protocol contract)
        impact_results.sort(
            key=lambda x: x["probability"] * x["magnitude"], reverse=True,
        )
        return impact_results
