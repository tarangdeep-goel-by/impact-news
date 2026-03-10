"""RSS feed collection: fetch, clean, deduplicate, store."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from html import unescape
from uuid import uuid4

import feedparser

from config import RSS_FEEDS
from models import Article, CollectionResult
from pipeline.database import Database
from pipeline.dedup import Deduplicator

logger = logging.getLogger(__name__)


def clean_html(html: str) -> str:
    """Strip HTML tags, decode entities, collapse whitespace."""
    text = re.sub(r"<[^>]*>", " ", html)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class ArticleCollector:
    """Fetches RSS feeds, deduplicates, and stores articles."""

    def __init__(self, db: Database, dedup: Deduplicator) -> None:
        self.db = db
        self.dedup = dedup

    async def fetch_feed(self, feed: dict) -> list[Article]:
        """Parse a single RSS feed and return Article objects."""
        name = feed.get("name", "Unknown")
        url = feed.get("url", "")
        category = feed.get("category", "")

        loop = asyncio.get_running_loop()
        try:
            parsed = await loop.run_in_executor(None, feedparser.parse, url)
        except Exception as e:
            logger.error("Failed to fetch feed %s: %s", name, e)
            return []

        articles: list[Article] = []
        for entry in parsed.entries:
            title = clean_html(getattr(entry, "title", "") or "")
            link = getattr(entry, "link", "") or ""
            summary = clean_html(getattr(entry, "summary", "") or "")

            if len(title) < 10 or not link:
                continue

            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published_at = datetime(*entry.published_parsed[:6])
                except Exception:
                    pass

            article = Article(
                title=title,
                summary=summary,
                url=link,
                source=name,
                published_at=published_at,
            )
            articles.append(article)

        logger.info("Feed %s: fetched %d articles", name, len(articles))
        return articles

    async def fetch_all_feeds(self) -> list[Article]:
        """Fetch all configured RSS feeds concurrently."""
        tasks = [self.fetch_feed(feed) for feed in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: list[Article] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Feed %s failed: %s", RSS_FEEDS[i].get("name"), result)
                continue
            all_articles.extend(result)

        logger.info("Total fetched from all feeds: %d", len(all_articles))
        return all_articles

    async def run(self) -> CollectionResult:
        """Fetch -> dedup -> store -> log. Returns collection stats."""
        run_id = str(uuid4())
        started_at = datetime.utcnow().isoformat()
        errors: list[str] = []

        # 1. Fetch all feeds
        all_articles = await self.fetch_all_feeds()

        # 2. Deduplicate
        unique = self.dedup.deduplicate_batch(all_articles)

        # 3. Insert unique articles
        new_inserted = 0
        for article in unique:
            try:
                if self.db.insert_article(article):
                    new_inserted += 1
            except Exception as e:
                msg = f"Insert failed for {article.url}: {e}"
                logger.error(msg)
                errors.append(msg)

        # 4. Log execution
        completed_at = datetime.utcnow().isoformat()
        self.db.log_execution(run_id, {
            "started_at": started_at,
            "completed_at": completed_at,
            "articles_fetched": len(all_articles),
            "articles_new": new_inserted,
            "articles_duplicate": len(all_articles) - len(unique),
            "errors": errors,
        })

        result = CollectionResult(
            total_fetched=len(all_articles),
            after_dedup=len(unique),
            new_inserted=new_inserted,
            errors=errors,
        )
        logger.info(
            "Collection run %s complete: fetched=%d, unique=%d, inserted=%d",
            run_id, result.total_fetched, result.after_dedup, result.new_inserted,
        )
        return result
