"""Impact News — Entry point.

Wires together graph loading, embedding index, article ingestion, bot, and pipeline.

CLI:
    python main.py run      — bot + periodic pipeline (collect + process + deliver)
    python main.py bot      — bot only (onboarding + delivery jobs)
    python main.py collect  — one-shot article collection
    python main.py process  — one-shot tag extraction + matching
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from config import settings
from graph.graph import ImpactGraph
from graph.embeddings import NodeMatcher
from models import UserGraph
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


def load_user_graph() -> UserGraph | None:
    """Load saved user graph from data/user_graph.json."""
    path = Path("data/user_graph.json")
    if not path.exists():
        logger.warning("No user graph found at %s — run /start in bot first", path)
        return None
    with open(path) as f:
        data = json.load(f)
    # UserGraph.reachable_nodes is a set, JSON stores it as list
    if "reachable_nodes" in data and isinstance(data["reachable_nodes"], list):
        data["reachable_nodes"] = set(data["reachable_nodes"])
    return UserGraph(**data)


async def pipeline_job(context) -> None:
    """Periodic job: collect articles + process matches."""
    db = context.bot_data.get("db")
    matcher = context.bot_data.get("matcher")
    graph = context.bot_data.get("graph")
    user_graph = context.bot_data.get("user_graph")
    gemini = context.bot_data.get("gemini")

    if not all([db, matcher, graph, user_graph, gemini]):
        logger.warning("Pipeline job skipped — missing dependencies")
        return

    from pipeline.collector import ArticleCollector
    from pipeline.dedup import Deduplicator
    from pipeline.matcher import process_articles

    # Collect
    dedup = Deduplicator(db)
    collector = ArticleCollector(db, dedup)
    result = await collector.run()
    logger.info(
        "Pipeline collect: fetched=%d, new=%d",
        result.total_fetched, result.new_inserted,
    )

    # Process
    impacts = process_articles(db, matcher, graph, user_graph, gemini)
    high = sum(1 for i in impacts if i.severity == "high")
    medium = sum(1 for i in impacts if i.severity == "medium")
    logger.info("Pipeline process: %d articles → %d HIGH, %d MEDIUM", len(impacts), high, medium)


def run_all() -> None:
    """Start bot with periodic pipeline collection + processing."""
    from bot.bot import main as bot_main
    from pipeline.gemini import GeminiClient

    graph = init_graph()
    matcher = init_embeddings(graph)
    db = init_database()
    user_graph = load_user_graph()
    gemini = GeminiClient()

    if user_graph is None:
        logger.warning("No user profile yet — bot will start but pipeline won't score articles")

    # bot_main now accepts shared state and wires up delivery jobs
    # We also need to register the pipeline job on the bot's job queue
    from telegram.ext import Application
    from bot.bot import (
        main as _unused,
        start, handle_answer, handle_feedback,
        check_high_priority, send_daily_digest,
    )
    from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler
    import datetime as dt

    app = Application.builder().token(settings.telegram_bot_token).build()

    # Shared state
    app.bot_data["db"] = db
    app.bot_data["graph"] = graph
    app.bot_data["matcher"] = matcher
    app.bot_data["user_graph"] = user_graph
    app.bot_data["gemini"] = gemini

    # Onboarding conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("profile", start),
        ],
        states={i: [CallbackQueryHandler(handle_answer)] for i in range(9)},
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(conv_handler)

    # Feedback handler
    app.add_handler(CallbackQueryHandler(handle_feedback, pattern=r"^fb\|"))

    # Delivery jobs
    if user_graph:
        app.job_queue.run_repeating(check_high_priority, interval=300, first=10)
        app.job_queue.run_daily(send_daily_digest, time=dt.time(settings.digest_hour, 0))
        logger.info("Delivery jobs registered")

    # Pipeline job: collect + process every N seconds
    app.job_queue.run_repeating(
        pipeline_job,
        interval=settings.pipeline_interval_seconds,
        first=30,
    )
    logger.info("Pipeline job registered: every %ds", settings.pipeline_interval_seconds)

    logger.info("Starting Impact News (bot + pipeline)...")
    app.run_polling()


def run_bot() -> None:
    """Start the Telegram bot only (onboarding + delivery, no pipeline)."""
    from bot.bot import main as bot_main
    from pipeline.gemini import GeminiClient

    graph = init_graph()
    matcher = init_embeddings(graph)
    db = init_database()
    user_graph = load_user_graph()
    gemini = GeminiClient()

    bot_main(db=db, graph=graph, node_matcher=matcher, user_graph=user_graph, gemini=gemini)


def main():
    args = sys.argv[1:]

    if "run" in args:
        # Full mode: bot + periodic pipeline
        run_all()
    elif "bot" in args:
        # Bot only (onboarding + delivery jobs)
        logger.info("Starting Telegram bot...")
        run_bot()
    elif "process" in args:
        # One-shot processing
        from pipeline.gemini import GeminiClient
        from pipeline.matcher import process_articles

        graph = init_graph()
        matcher = init_embeddings(graph)
        db = init_database()
        user_graph = load_user_graph()
        gemini = GeminiClient()

        if user_graph is None:
            logger.error("Cannot process without user profile. Run /start in bot first.")
            sys.exit(1)

        impacts = process_articles(db, matcher, graph, user_graph, gemini)
        for imp in impacts:
            logger.info(
                "  %s: score=%.3f severity=%s",
                imp.article_id[:12], imp.top_score, imp.severity,
            )
        db.close()
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
