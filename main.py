"""Impact News — Entry point.

CLI:
    python main.py collect  — one-shot article collection from RSS feeds
    python main.py bot      — start Telegram bot (delivery + feedback)
"""

import asyncio
import logging
import sys

from config import settings
from pipeline.database import Database
from pipeline.dedup import Deduplicator
from pipeline.collector import ArticleCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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


def main():
    args = sys.argv[1:]

    if "collect" in args:
        db = init_database()
        asyncio.run(collect_articles(db))
        db.close()
    elif "bot" in args or "run" in args:
        from bot.bot import main as bot_main
        db = init_database()
        bot_main(db=db)
    else:
        print("Usage: python main.py [collect|bot|run]")
        sys.exit(1)


if __name__ == "__main__":
    main()
