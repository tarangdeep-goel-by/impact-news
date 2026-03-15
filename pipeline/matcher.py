"""Article tag extraction, graph matching, and impact scoring pipeline."""

from __future__ import annotations

import json
import logging

from config import settings
from graph.embeddings import NodeMatcher
from graph.graph import ImpactGraph
from graph.markov_engine import CausalMarkovEngine
from graph.traverse import analyze_impact
from models import Article, ArticleImpact, TagExtractionResult, UserGraph
from pipeline.database import Database
from pipeline.gemini import GeminiClient, parse_json_response

logger = logging.getLogger(__name__)

TAG_EXTRACTION_PROMPT = """You are a news impact analyst for the Indian economy.
Given news articles, extract what real-world things each article AFFECTS (not just mentions).

For each article, return:
- tags: Direct impacts (commodities, policies, sectors, companies, infrastructure)
- indirect_effects: Secondary/tertiary effects that may follow
- domains: Which broad domains (energy, food, financial, employment, governance, tech, health, transport)

Be exhaustive. Think about second and third order effects.
Use lowercase, underscored identifiers (e.g. "crude_oil_prices", "home_loan_emi", "it_sector_jobs").

Output ONLY a JSON array: [{{"id": "...", "tags": [...], "indirect_effects": [...], "domains": [...]}}]

Articles:
{articles_json}"""

EXPLANATION_PROMPT = """You are explaining why a news article matters to a specific person in India.

Article: {title}
Summary: {summary}

This article affects these areas connected to the user's life:
{impact_chain}

Write 2-3 concise sentences explaining WHY this matters to them personally.
Focus on the causal chain — how the news event propagates to affect their daily life.
Be specific, not generic. No hedging language."""


def extract_tags(
    articles: list[Article], gemini: GeminiClient
) -> dict[str, TagExtractionResult]:
    """Batch tag extraction. 10 articles per Gemini call."""
    results: dict[str, TagExtractionResult] = {}
    batch_size = 10

    for i in range(0, len(articles), batch_size):
        batch = articles[i : i + batch_size]
        articles_json = json.dumps(
            [{"id": a.id, "title": a.title, "summary": a.summary} for a in batch],
            ensure_ascii=False,
        )
        prompt = TAG_EXTRACTION_PROMPT.format(articles_json=articles_json)

        try:
            raw = gemini.call(prompt)
            parsed = parse_json_response(raw)
        except Exception:
            logger.exception("Tag extraction failed for batch %d", i // batch_size)
            # Return empty results for this batch
            for a in batch:
                results[a.id] = TagExtractionResult(article_id=a.id)
            continue

        if not isinstance(parsed, list):
            parsed = [parsed]

        extraction_map = {}
        for item in parsed:
            if isinstance(item, dict) and "id" in item:
                extraction_map[item["id"]] = item

        for a in batch:
            item = extraction_map.get(a.id, {})
            results[a.id] = TagExtractionResult(
                article_id=a.id,
                tags=item.get("tags", []),
                indirect_effects=item.get("indirect_effects", []),
                domains=item.get("domains", []),
            )

    return results


def match_tags_to_graph(
    tags: TagExtractionResult,
    node_matcher: NodeMatcher,
    user_graph: UserGraph,
    graph: ImpactGraph,
    engine: CausalMarkovEngine | None = None,
) -> list[dict]:
    """Match extracted tags to graph nodes and score against user profile.

    For each tag:
    1. FAISS match → top graph nodes
    2. Filter to nodes in user's reachable_nodes
    3. analyze_impact() → check if propagated nodes hit user's direct edges
    4. Combined score = tag_match × graph_score × user_importance
    """
    user_direct_nodes = {e.node_id: e.importance for e in user_graph.edges}
    matches = []

    all_tags = [(tag, False) for tag in tags.tags] + [
        (tag, True) for tag in tags.indirect_effects
    ]

    for tag_text, is_indirect in all_tags:
        node_matches = node_matcher.match(tag_text, top_k=3, threshold=settings.match_threshold)

        for nm in node_matches:
            # Check if this node is in user's reachable zone
            if nm.node_id not in user_graph.reachable_nodes:
                continue

            tag_match_score = nm.score

            # Run impact propagation from this node
            if engine:
                impacts = engine.evaluate_impact(nm.node_id, prob_threshold=0.0001)
            else:
                impacts = analyze_impact(graph.g, nm.node_id, threshold=0.05, max_depth=4)

            # Find best hit among user's direct edges
            best_graph_score = 0.0
            best_user_node = None
            best_path = []
            best_polarity = 0
            best_delay = "SHORT_TERM"

            for impact in impacts:
                if impact["node"] in user_direct_nodes:
                    score_key = "probability" if engine else "score"
                    if impact[score_key] > best_graph_score:
                        best_graph_score = impact[score_key]
                        best_user_node = impact["node"]
                        best_path = impact["path"]
                        best_polarity = impact["polarity"]
                        best_delay = impact["delay"]

            # If no propagated node hits user's direct edges,
            # check if the matched node itself is a direct edge
            if best_user_node is None and nm.node_id in user_direct_nodes:
                best_graph_score = 1.0
                best_user_node = nm.node_id
                best_path = [nm.node_id]
                best_polarity = 0
                best_delay = "IMMEDIATE"

            if best_user_node is None:
                continue

            user_importance = user_direct_nodes.get(best_user_node, 1.0)
            combined = tag_match_score * best_graph_score * user_importance

            if is_indirect:
                combined *= settings.indirect_weight

            matches.append({
                "node_id": nm.node_id,
                "tag": tag_text,
                "alias_matched": nm.alias_matched,
                "match_score": round(tag_match_score, 3),
                "graph_score": round(best_graph_score, 3),
                "user_importance": round(user_importance, 3),
                "combined": round(combined, 3),
                "user_node": best_user_node,
                "path": best_path,
                "polarity": best_polarity,
                "delay": best_delay,
                "is_indirect": is_indirect,
            })

    # Deduplicate by node_id, keeping highest combined score
    seen: dict[str, dict] = {}
    for m in matches:
        key = m["node_id"]
        if key not in seen or m["combined"] > seen[key]["combined"]:
            seen[key] = m

    return sorted(seen.values(), key=lambda x: x["combined"], reverse=True)


def _severity(score: float) -> str:
    """Map score to severity tier."""
    if score >= settings.score_high_threshold:
        return "high"
    if score >= settings.score_medium_threshold:
        return "medium"
    return "low"


def generate_explanation(
    article: Article,
    top_matches: list[dict],
    gemini: GeminiClient,
) -> str:
    """Generate 2-3 sentence explanation for why this article matters to user."""
    if not top_matches:
        return ""

    chains = []
    for m in top_matches[:3]:
        path_str = " → ".join(m["path"])
        pol = {1: "↑", -1: "↓", 0: "~"}.get(m["polarity"], "~")
        chains.append(f"- {m['tag']} → {path_str} (impact: {m['combined']:.2f}, {pol}, {m['delay']})")

    impact_chain = "\n".join(chains)
    prompt = EXPLANATION_PROMPT.format(
        title=article.title,
        summary=article.summary or "(no summary)",
        impact_chain=impact_chain,
    )

    try:
        return gemini.call(prompt).strip()
    except Exception:
        logger.exception("Explanation generation failed for %s", article.id)
        return f"This article may affect: {', '.join(m['user_node'] for m in top_matches[:3])}"


def process_articles(
    db: Database,
    node_matcher: NodeMatcher,
    graph: ImpactGraph,
    user_graph: UserGraph,
    gemini: GeminiClient,
    engine: CausalMarkovEngine | None = None,
) -> list[ArticleImpact]:
    """Full pipeline: extract tags → match → score → explain → persist."""
    articles = db.get_unprocessed_articles()
    if not articles:
        logger.info("No unprocessed articles")
        return []

    logger.info("Processing %d articles", len(articles))

    # 1. Batch tag extraction
    tag_results = extract_tags(articles, gemini)

    # 2. Match + score each article
    impacts: list[ArticleImpact] = []

    for article in articles:
        tags = tag_results.get(article.id)
        if not tags or (not tags.tags and not tags.indirect_effects):
            # No tags extracted — mark processed, skip
            db.mark_processed(article.id, {"tags": [], "indirect_effects": [], "domains": []})
            continue

        matched = match_tags_to_graph(tags, node_matcher, user_graph, graph, engine=engine)
        top_score = matched[0]["combined"] if matched else 0.0
        severity = _severity(top_score)

        # 3. Generate explanation for HIGH/MEDIUM
        explanation = ""
        if severity in ("high", "medium") and matched:
            explanation = generate_explanation(article, matched, gemini)

        impact = ArticleImpact(
            article_id=article.id,
            matched_nodes=matched,
            top_score=top_score,
            severity=severity,
            explanation=explanation,
        )
        impacts.append(impact)

        # 4. Persist
        db.mark_processed(
            article.id,
            {"tags": tags.tags, "indirect_effects": tags.indirect_effects, "domains": tags.domains},
        )

        if matched:
            db.insert_match(
                article_id=article.id,
                user_id=user_graph.user_id,
                matched_nodes=matched,
                score=top_score,
                explanation=explanation,
                severity=severity,
            )

        logger.info(
            "Article %s: score=%.3f severity=%s matches=%d",
            article.id[:12], top_score, severity, len(matched),
        )

    high = sum(1 for i in impacts if i.severity == "high")
    medium = sum(1 for i in impacts if i.severity == "medium")
    logger.info("Pipeline done: %d articles → %d HIGH, %d MEDIUM", len(impacts), high, medium)

    return impacts


if __name__ == "__main__":
    # Quick test mode
    import sys
    sys.path.insert(0, ".")

    from config import settings as _s
    from graph.graph import ImpactGraph
    from graph.embeddings import NodeMatcher
    from pipeline.database import Database

    print("Loading graph...")
    g = ImpactGraph(_s.graph_path)
    g.load()
    print(f"Graph: {g.stats()['node_count']} nodes")

    print("Loading embeddings...")
    m = NodeMatcher(g)
    from pathlib import Path
    if Path(_s.embeddings_path, "embeddings.faiss").exists():
        m.load(_s.embeddings_path)
    else:
        m.build_index()
        m.save(_s.embeddings_path)

    print("Loading DB...")
    db = Database(_s.db_path)
    db.init_schema()

    articles = db.get_unprocessed_articles()
    if not articles:
        print("No unprocessed articles. Run 'python main.py collect' first.")
        sys.exit(0)

    # Test tag extraction on first 5
    test_articles = articles[:5]
    print(f"\nTesting with {len(test_articles)} articles:")
    for a in test_articles:
        print(f"  - {a.title[:80]}")

    client = GeminiClient()
    tags = extract_tags(test_articles, client)

    for a in test_articles:
        t = tags.get(a.id)
        print(f"\n--- {a.title[:60]} ---")
        print(f"  Tags: {t.tags if t else 'NONE'}")
        print(f"  Indirect: {t.indirect_effects if t else 'NONE'}")
        print(f"  Domains: {t.domains if t else 'NONE'}")

        if t and t.tags:
            # Test matching (without user graph)
            for tag in t.tags[:3]:
                matches = m.match(tag, top_k=3)
                nodes = ", ".join(f"{nm.node_id}({nm.score:.2f})" for nm in matches)
                print(f"  Match '{tag}': {nodes}")

    db.close()
    print("\nDone.")
