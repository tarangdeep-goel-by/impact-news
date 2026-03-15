"""Impact News — Entry point.

Wires together graph loading, embedding index, article ingestion, bot, and pipeline.

CLI:
    python main.py run      — bot + periodic pipeline (collect + process + deliver)
    python main.py bot      — bot only (delivery jobs, no pipeline)
    python main.py collect  — one-shot article collection
    python main.py          — default: init, collect once, test embedding queries
"""

import asyncio
import logging
import sys
from pathlib import Path

from config import settings
from graph.graph import ImpactGraph
from graph.embeddings import NodeMatcher
from pipeline.database import Database
from pipeline.dedup import Deduplicator
from pipeline.collector import ArticleCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def init_graph() -> ImpactGraph:
    """Load the merged graph. Run merge if file doesn't exist."""
    if not Path(settings.graph_path).exists():
        logger.info("Merged graph not found, running merge...")
        from graph.merge import main as run_merge
        run_merge()
    graph = ImpactGraph(settings.graph_path)
    graph.load()
    stats = graph.stats()
    logger.info("Graph loaded: %d nodes, %d edges", stats["node_count"], stats["edge_count"])
    return graph


def init_embeddings(graph: ImpactGraph) -> NodeMatcher:
    """Build or load the FAISS embedding index."""
    matcher = NodeMatcher(graph)
    index_path = Path(settings.embeddings_path) / "embeddings.faiss"
    if index_path.exists():
        matcher.load(settings.embeddings_path)
        logger.info("Embeddings loaded from disk")
    else:
        logger.info("Building embedding index...")
        matcher.build_index()
        matcher.save(settings.embeddings_path)
        logger.info("Embeddings built and saved")
    return matcher


def init_database() -> Database:
    """Initialize SQLite database."""
    db = Database(settings.db_path)
    db.init_schema()
    logger.info("Database initialized: %s", settings.db_path)
    return db


async def collect_articles(db: Database) -> None:
    """Run one collection cycle."""
    dedup = Deduplicator(db)
    collector = ArticleCollector(db, dedup)
    result = await collector.run()
    logger.info(
        "Collection: fetched=%d, after_dedup=%d, new=%d, errors=%d",
        result.total_fetched, result.after_dedup, result.new_inserted, len(result.errors),
    )


def run_bot() -> None:
    """Start the Telegram bot (delivery + feedback, no pipeline)."""
    from bot.bot import main as bot_main
    from pipeline.gemini import GeminiClient

    graph = init_graph()
    matcher = init_embeddings(graph)
    db = init_database()
    gemini = GeminiClient()

    bot_main(db=db, graph=graph, node_matcher=matcher, gemini=gemini)


def main():
    args = sys.argv[1:]

    if "run" in args:
        # Full mode: bot + periodic pipeline
        # Note: article scoring requires user profiling (not yet rebuilt for new graph)
        run_bot()
    elif "bot" in args:
        logger.info("Starting Telegram bot...")
        run_bot()
    elif "collect" in args:
        # One-shot collection
        graph = init_graph()
        init_embeddings(graph)
        db = init_database()
        asyncio.run(collect_articles(db))
        db.close()
    else:
        # Default: init everything, run one collection, print status
        graph = init_graph()
        matcher = init_embeddings(graph)
        db = init_database()

        asyncio.run(collect_articles(db))

        articles = db.get_unprocessed_articles()
        logger.info("Unprocessed articles in DB: %d", len(articles))

        test_queries = ["oil prices", "RBI rate hike", "IT layoffs"]
        for q in test_queries:
            matches = matcher.match(q, top_k=3)
            nodes = ", ".join(f"{m.node_id}({m.score:.2f})" for m in matches)
            logger.info("Match '%s': %s", q, nodes)

        db.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()
