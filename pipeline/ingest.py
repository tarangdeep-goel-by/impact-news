"""Article ingestion pipeline — classify articles via LLM engine and store results.

Each article gets ONE Gemini call that returns:
- triggers (T-nodes) + impacts (I-nodes) for relevant articles
- no_impact flag for irrelevant articles (sports, arts, petty crime, etc.)

Usage:
    python -m pipeline.ingest                    # Process 100 diverse unprocessed articles
    python -m pipeline.ingest --limit 50         # Process 50
    python -m pipeline.ingest --all              # Process all unprocessed
    python -m pipeline.ingest --stats            # Show processing stats
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import time
from collections import Counter
from datetime import datetime

from config import settings
from engine.llm_engine import LLMImpactEngine
from engine.taxonomy_context import TaxonomyContext
from pipeline.database import Database

logger = logging.getLogger(__name__)


def select_diverse_articles(db: Database, limit: int) -> list[dict]:
    """Select unprocessed articles with source diversity.

    Distributes evenly across sources, then fills remaining with largest sources.
    """
    rows = db.conn.execute(
        """SELECT id, title, summary, source FROM articles
           WHERE processed = 0
           ORDER BY source, published_at DESC"""
    ).fetchall()

    if not rows:
        return []

    # Group by source
    by_source: dict[str, list[dict]] = {}
    for r in rows:
        src = r["source"] or "Unknown"
        by_source.setdefault(src, []).append(dict(r))

    # Round-robin across sources
    selected: list[dict] = []
    source_names = sorted(by_source.keys())
    idx = {s: 0 for s in source_names}

    while len(selected) < limit:
        added_this_round = False
        for src in source_names:
            if len(selected) >= limit:
                break
            articles = by_source[src]
            if idx[src] < len(articles):
                selected.append(articles[idx[src]])
                idx[src] += 1
                added_this_round = True
        if not added_this_round:
            break

    return selected


def process_articles(
    db: Database,
    engine: LLMImpactEngine,
    articles: list[dict],
) -> dict:
    """Process articles through LLM engine and store results.

    Returns stats dict.
    """
    stats = {
        "total": len(articles),
        "relevant": 0,
        "no_impact": 0,
        "errors": 0,
        "triggers": Counter(),
        "top_impacts": Counter(),
    }

    for i, article in enumerate(articles):
        aid = article["id"]
        title = article["title"]
        summary = article.get("summary", "")

        print(f"[{i+1}/{len(articles)}] {title[:80]}...", end=" ", flush=True)

        t0 = time.time()
        try:
            results, meta = engine.evaluate_article(title, summary)
        except Exception as e:
            logger.error("Failed on %s: %s", aid, e)
            stats["errors"] += 1
            print("ERROR")
            continue
        elapsed = time.time() - t0

        is_relevant = meta["is_relevant"]
        triggers = meta.get("triggers", [])
        rejection_reason = meta.get("rejection_reason")

        # Store in article_impacts
        db.conn.execute(
            """INSERT OR REPLACE INTO article_impacts
               (article_id, is_relevant, triggers_json, impacts_json, rejection_reason, processed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                aid,
                1 if is_relevant else 0,
                json.dumps(triggers),
                json.dumps([dict(r) for r in results]) if results else None,
                rejection_reason,
                datetime.utcnow().isoformat(),
            ),
        )
        # Mark article as processed
        db.conn.execute(
            "UPDATE articles SET processed = 1, processed_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), aid),
        )
        db.conn.commit()

        if is_relevant:
            stats["relevant"] += 1
            for t in triggers:
                stats["triggers"][t] += 1
            for r in results[:3]:
                stats["top_impacts"][r["node"]] += 1
            impact_str = ", ".join(r["node"] for r in results[:3])
            print(f"RELEVANT ({len(results)} impacts, {elapsed:.1f}s) [{impact_str}]")
        else:
            stats["no_impact"] += 1
            print(f"NO_IMPACT ({elapsed:.1f}s) [{rejection_reason}]")

    return stats


def print_stats(db: Database) -> None:
    """Print processing statistics from the database."""
    total = db.conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    processed = db.conn.execute("SELECT COUNT(*) FROM articles WHERE processed = 1").fetchone()[0]
    unprocessed = total - processed

    impacts = db.conn.execute("SELECT COUNT(*) FROM article_impacts").fetchone()[0]
    relevant = db.conn.execute("SELECT COUNT(*) FROM article_impacts WHERE is_relevant = 1").fetchone()[0]
    no_impact = db.conn.execute("SELECT COUNT(*) FROM article_impacts WHERE is_relevant = 0").fetchone()[0]

    print(f"\n=== Article Stats ===")
    print(f"Total articles:     {total}")
    print(f"Processed:          {processed}")
    print(f"Unprocessed:        {unprocessed}")
    print(f"\n=== Impact Classification ===")
    print(f"Classified:         {impacts}")
    print(f"Relevant:           {relevant} ({relevant/impacts*100:.0f}%)" if impacts else "")
    print(f"No impact:          {no_impact} ({no_impact/impacts*100:.0f}%)" if impacts else "")

    if relevant:
        # Top triggers
        rows = db.conn.execute(
            "SELECT triggers_json FROM article_impacts WHERE is_relevant = 1"
        ).fetchall()
        trigger_counts: Counter = Counter()
        for r in rows:
            for t in json.loads(r["triggers_json"] or "[]"):
                trigger_counts[t] += 1

        print(f"\n=== Top Triggers ===")
        for t, c in trigger_counts.most_common(15):
            print(f"  {t}: {c}")

        # Top rejection reasons
        rows = db.conn.execute(
            "SELECT rejection_reason, COUNT(*) as cnt FROM article_impacts WHERE is_relevant = 0 GROUP BY rejection_reason ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        if rows:
            print(f"\n=== Top Rejection Reasons ===")
            for r in rows:
                print(f"  {r['rejection_reason']}: {r['cnt']}")

        # Sample relevant articles
        rows = db.conn.execute(
            """SELECT a.title, ai.triggers_json, ai.impacts_json
               FROM article_impacts ai JOIN articles a ON ai.article_id = a.id
               WHERE ai.is_relevant = 1 ORDER BY ai.processed_at DESC LIMIT 5"""
        ).fetchall()
        print(f"\n=== Recent Relevant Articles ===")
        for r in rows:
            impacts = json.loads(r["impacts_json"] or "[]")
            impact_nodes = [i["node"] for i in impacts[:3]]
            print(f"  {r['title'][:70]}")
            print(f"    T: {r['triggers_json']}  I: {impact_nodes}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Article ingestion via LLM engine")
    parser.add_argument("--limit", type=int, default=100, help="Max articles to process")
    parser.add_argument("--all", action="store_true", help="Process all unprocessed")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    db = Database(settings.db_path)
    db.init_schema()

    if args.stats:
        print_stats(db)
        db.close()
        return

    # Select articles
    limit = 999999 if args.all else args.limit
    articles = select_diverse_articles(db, limit)
    if not articles:
        print("No unprocessed articles.")
        db.close()
        return

    print(f"Selected {len(articles)} articles from {len(set(a['source'] for a in articles))} sources\n")

    # Init engine
    print("Loading taxonomy...", end=" ", flush=True)
    taxonomy = TaxonomyContext.from_merged_graph(settings.graph_path)
    print("done.")
    print("Initializing LLM engine...", end=" ", flush=True)
    engine = LLMImpactEngine(taxonomy)
    print("done.\n")

    # Process
    stats = process_articles(db, engine, articles)

    # Summary
    print(f"\n{'='*60}")
    print(f"DONE: {stats['total']} articles")
    print(f"  Relevant:  {stats['relevant']}")
    print(f"  No impact: {stats['no_impact']}")
    print(f"  Errors:    {stats['errors']}")

    if stats["triggers"]:
        print(f"\nTop triggers:")
        for t, c in stats["triggers"].most_common(10):
            print(f"  {t}: {c}")

    print_stats(db)
    db.close()


if __name__ == "__main__":
    main()
