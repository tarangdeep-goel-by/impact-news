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
    created_at TEXT DEFAULT (datetime('now')),
    delivered_at TEXT,
    feedback TEXT
);

CREATE TABLE IF NOT EXISTS article_impacts (
    article_id TEXT PRIMARY KEY REFERENCES articles(id),
    is_relevant INTEGER NOT NULL DEFAULT 0,
    triggers_json TEXT,
    impacts_json TEXT,
    rejection_reason TEXT,
    event_id TEXT REFERENCES events(event_id),
    tier1_ms INTEGER,
    tier2_ms INTEGER,
    processed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    summary TEXT NOT NULL,
    triggers_json TEXT NOT NULL,
    current_impacts_json TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'new',
    category TEXT,
    first_seen_at TEXT NOT NULL,
    last_updated_at TEXT NOT NULL,
    article_count INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS event_articles (
    event_id TEXT NOT NULL REFERENCES events(event_id),
    article_id TEXT NOT NULL REFERENCES articles(id),
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_seed INTEGER DEFAULT 0,
    PRIMARY KEY (event_id, article_id)
);

CREATE TABLE IF NOT EXISTS trigger_instances (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id),
    t_node TEXT NOT NULL,
    context TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS impact_edges (
    id TEXT PRIMARY KEY,
    trigger_instance_id TEXT NOT NULL REFERENCES trigger_instances(id),
    i_node TEXT NOT NULL,
    probability REAL NOT NULL,
    magnitude REAL NOT NULL,
    delay_days INTEGER NOT NULL,
    polarity INTEGER NOT NULL DEFAULT 1,
    mechanism TEXT NOT NULL,
    maturity_date TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS edge_support (
    edge_id TEXT NOT NULL REFERENCES impact_edges(id),
    article_id TEXT NOT NULL REFERENCES articles(id),
    added_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (edge_id, article_id)
);

CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(processed);
CREATE INDEX IF NOT EXISTS idx_articles_fingerprint ON articles(fingerprint);
CREATE INDEX IF NOT EXISTS idx_articles_url_hash ON articles(url_hash);
CREATE INDEX IF NOT EXISTS idx_seen_hashes ON seen_hashes(hash);
CREATE INDEX IF NOT EXISTS idx_matches_severity ON article_matches(severity, delivered_at);
CREATE INDEX IF NOT EXISTS idx_impacts_relevant ON article_impacts(is_relevant);
CREATE INDEX IF NOT EXISTS idx_events_stage ON events(stage);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
CREATE INDEX IF NOT EXISTS idx_events_last_updated ON events(last_updated_at);
CREATE INDEX IF NOT EXISTS idx_event_articles_event ON event_articles(event_id);
CREATE INDEX IF NOT EXISTS idx_event_articles_article ON event_articles(article_id);
CREATE INDEX IF NOT EXISTS idx_trigger_instances_event ON trigger_instances(event_id);
CREATE INDEX IF NOT EXISTS idx_trigger_instances_t_node ON trigger_instances(t_node);
CREATE INDEX IF NOT EXISTS idx_impact_edges_trigger ON impact_edges(trigger_instance_id);
CREATE INDEX IF NOT EXISTS idx_impact_edges_i_node ON impact_edges(i_node);
CREATE INDEX IF NOT EXISTS idx_impact_edges_status ON impact_edges(status);
CREATE INDEX IF NOT EXISTS idx_impact_edges_maturity ON impact_edges(maturity_date);
CREATE INDEX IF NOT EXISTS idx_edge_support_article ON edge_support(article_id);
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

    def insert_match(
        self,
        article_id: str,
        user_id: str,
        matched_nodes: list[dict],
        score: float,
        explanation: str,
        severity: str,
    ) -> int:
        """Insert a scored match into article_matches. Returns match ID."""
        cursor = self.conn.execute(
            """INSERT INTO article_matches
               (article_id, user_id, matched_nodes_json, score, explanation, severity)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (article_id, user_id, json.dumps(matched_nodes), score, explanation, severity),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_pending_deliveries(
        self, user_id: str, min_severity: str = "medium"
    ) -> list[dict]:
        """Get undelivered matches above severity threshold, ordered by score desc."""
        severity_order = {"high": 3, "medium": 2, "low": 1}
        min_rank = severity_order.get(min_severity, 2)

        rows = self.conn.execute(
            """SELECT m.*, a.title, a.url, a.source, a.published_at
               FROM article_matches m
               JOIN articles a ON m.article_id = a.id
               WHERE m.user_id = ? AND m.delivered_at IS NULL
               ORDER BY m.score DESC""",
            (user_id,),
        ).fetchall()

        results = []
        for row in rows:
            sev = row["severity"] or "low"
            if severity_order.get(sev, 1) >= min_rank:
                results.append(dict(row))
        return results

    def mark_delivered(self, match_id: int) -> None:
        """Set delivered_at = now for a match."""
        self.conn.execute(
            "UPDATE article_matches SET delivered_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), match_id),
        )
        self.conn.commit()

    def save_feedback(self, match_id: int, feedback_type: str) -> None:
        """Store user feedback (relevant/not_relevant)."""
        self.conn.execute(
            "UPDATE article_matches SET feedback = ? WHERE id = ?",
            (feedback_type, match_id),
        )
        self.conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
