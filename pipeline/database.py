"""SQLite database operations for Impact News."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from models import Article

_SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT UNIQUE NOT NULL,
    source TEXT,
    published_at TEXT,
    fingerprint TEXT,
    url_hash TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    processed INTEGER DEFAULT 0,
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    feed_type TEXT DEFAULT 'rss',
    category TEXT,
    reliability_score REAL DEFAULT 1.0,
    active INTEGER DEFAULT 1,
    last_fetched TEXT
);

CREATE TABLE IF NOT EXISTS seen_hashes (
    hash TEXT PRIMARY KEY,
    first_seen_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    articles_fetched INTEGER DEFAULT 0,
    articles_new INTEGER DEFAULT 0,
    articles_duplicate INTEGER DEFAULT 0,
    errors TEXT
);

CREATE TABLE IF NOT EXISTS article_tags (
    article_id TEXT PRIMARY KEY REFERENCES articles(id),
    tags_json TEXT,
    indirect_effects_json TEXT,
    domains_json TEXT,
    extracted_at TEXT
);

CREATE TABLE IF NOT EXISTS article_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT REFERENCES articles(id),
    user_id TEXT,
    matched_nodes_json TEXT,
    score REAL,
    explanation TEXT,
    severity TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(processed);
CREATE INDEX IF NOT EXISTS idx_articles_fingerprint ON articles(fingerprint);
CREATE INDEX IF NOT EXISTS idx_articles_url_hash ON articles(url_hash);
CREATE INDEX IF NOT EXISTS idx_seen_hashes ON seen_hashes(hash);
"""


class Database:
    """Synchronous SQLite database for article storage and dedup."""

    def __init__(self, db_path: str = "data/impact_news.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def init_schema(self) -> None:
        """Create all tables and indexes."""
        self.conn.executescript(_SCHEMA)

    def insert_article(self, article: Article) -> bool:
        """Insert an article. Returns False if duplicate (URL or ID)."""
        try:
            url_hash = article.id  # id is SHA256 of URL
            self.conn.execute(
                """INSERT INTO articles
                   (id, title, summary, url, source, published_at,
                    fingerprint, url_hash, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    article.id,
                    article.title,
                    article.summary,
                    article.url,
                    article.source,
                    article.published_at.isoformat() if article.published_at else None,
                    article.fingerprint,
                    url_hash,
                    article.created_at.isoformat(),
                ),
            )
            # Track fingerprint and url_hash in seen_hashes
            for h in (article.fingerprint, url_hash):
                if h:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO seen_hashes (hash) VALUES (?)",
                        (h,),
                    )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return False

    def get_unprocessed_articles(self) -> list[Article]:
        """Return all articles where processed=0."""
        rows = self.conn.execute(
            "SELECT * FROM articles WHERE processed = 0"
        ).fetchall()
        articles = []
        for row in rows:
            articles.append(
                Article(
                    id=row["id"],
                    title=row["title"],
                    summary=row["summary"] or "",
                    url=row["url"],
                    source=row["source"] or "Unknown",
                    published_at=(
                        datetime.fromisoformat(row["published_at"])
                        if row["published_at"]
                        else None
                    ),
                    fingerprint=row["fingerprint"] or "",
                    created_at=(
                        datetime.fromisoformat(row["created_at"])
                        if row["created_at"]
                        else datetime.utcnow()
                    ),
                )
            )
        return articles

    def mark_processed(self, article_id: str, tags: dict) -> None:
        """Mark article as processed and store tags."""
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "UPDATE articles SET processed = 1, processed_at = ? WHERE id = ?",
            (now, article_id),
        )
        self.conn.execute(
            """INSERT OR REPLACE INTO article_tags
               (article_id, tags_json, indirect_effects_json, domains_json, extracted_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                article_id,
                json.dumps(tags.get("tags", [])),
                json.dumps(tags.get("indirect_effects", [])),
                json.dumps(tags.get("domains", [])),
                now,
            ),
        )
        self.conn.commit()

    def log_execution(self, run_id: str, stats: dict) -> None:
        """Log a pipeline execution run."""
        self.conn.execute(
            """INSERT INTO execution_logs
               (run_id, started_at, completed_at,
                articles_fetched, articles_new, articles_duplicate, errors)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                stats.get("started_at", datetime.utcnow().isoformat()),
                stats.get("completed_at", datetime.utcnow().isoformat()),
                stats.get("articles_fetched", 0),
                stats.get("articles_new", 0),
                stats.get("articles_duplicate", 0),
                json.dumps(stats.get("errors", [])),
            ),
        )
        self.conn.commit()

    def get_seen_hashes(self) -> set[str]:
        """Return all known fingerprints and url hashes."""
        rows = self.conn.execute("SELECT hash FROM seen_hashes").fetchall()
        return {row["hash"] for row in rows}

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
