"""Two-tier article ingestion pipeline with causal edges.

Tier 1 (flash-lite): T-tree aware classification + trigger identification + event matching
Tier 2 (pro):        Impact analysis with filtered I-tree + causal edges (upsert)

Flow:
    For each article:
        Title dedup → Tier 1 (triggers, exclude_l1s, event_match)
        → not relevant? Store and skip.
        → Build filtered I-tree (full minus excluded L1s)
        → relevant + event match? → Tier 2 analyze_update_v2 → upsert event edges
        → relevant + no match?    → Tier 2 analyze_new_v2   → create event with edges

Usage:
    python -m pipeline.ingest                    # Process 100 diverse unprocessed articles
    python -m pipeline.ingest --limit 50         # Custom limit
    python -m pipeline.ingest --all              # All unprocessed
    python -m pipeline.ingest --stats            # Show classification stats
    python -m pipeline.ingest --events           # Show active events
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections import Counter
from datetime import datetime

from config import settings
from engine.classifier import ArticleClassifier
from engine.llm_engine import ImpactAnalyzer
from engine.taxonomy_context import TaxonomyContext
from pipeline.database import Database
from pipeline.events import EventStore
from pipeline.gemini import GeminiClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Title-based near-duplicate detection (pre-Tier 1)
# ---------------------------------------------------------------------------

def _title_tokens(title: str) -> set[str]:
    """Lowercase word tokens, stripped of punctuation."""
    return {w.strip(".,;:!?\"'()[]") for w in title.lower().split()} - {""}


def _title_jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


TITLE_DEDUP_THRESHOLD = 0.6


class TitleDeduplicator:
    """Fast title similarity check against recently processed articles.

    Catches "same story, different source" before it hits Tier 1.
    Loads titles from article_impacts (already processed) + tracks
    titles within the current batch.
    """

    def __init__(self, db: Database) -> None:
        # Load titles of ALREADY PROCESSED articles from last 24 hours.
        # Within-batch dedup is handled by add() as each article is processed.
        rows = db.conn.execute(
            """SELECT a.title FROM articles a
               JOIN article_impacts ai ON a.id = ai.article_id
               WHERE ai.processed_at > datetime('now', '-1 day')"""
        ).fetchall()
        self._seen: list[set[str]] = [_title_tokens(r["title"]) for r in rows]

    def is_duplicate(self, title: str) -> bool:
        """Return True if title is >60% similar to any recently processed title."""
        tokens = _title_tokens(title)
        for seen in self._seen:
            if _title_jaccard(tokens, seen) >= TITLE_DEDUP_THRESHOLD:
                return True
        return False

    def add(self, title: str) -> None:
        """Track a title processed in this batch."""
        self._seen.append(_title_tokens(title))


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
    taxonomy: TaxonomyContext,
    classifier: ArticleClassifier,
    analyzer: ImpactAnalyzer,
    event_store: EventStore,
    articles: list[dict],
) -> dict:
    """Process articles through two-tier causal edges pipeline.

    Returns stats dict.
    """
    title_dedup = TitleDeduplicator(db)

    stats = {
        "total": len(articles),
        "relevant": 0,
        "no_impact": 0,
        "errors": 0,
        "events_created": 0,
        "events_updated": 0,
        "tier1_only": 0,
        "deduped": 0,
        "triggers": Counter(),
        "top_impacts": Counter(),
    }

    for i, article in enumerate(articles):
        aid = article["id"]
        title = article["title"]
        summary = article.get("summary", "")

        print(f"[{i+1}/{len(articles)}] {title[:80]}...", end=" ", flush=True)

        # ── Pre-Tier 1: Title dedup ──
        if title_dedup.is_duplicate(title):
            _store_result(db, aid, is_relevant=False, rejection_reason="title_near_duplicate")
            stats["deduped"] += 1
            print("DEDUP (title similarity)")
            continue
        title_dedup.add(title)

        # ── Tier 1: Classification + triggers + event matching ──
        t1_start = time.time()
        classification = classifier.classify(title, summary)
        tier1_ms = int((time.time() - t1_start) * 1000)

        if classification is None:
            logger.error("Tier 1 failed for %s", aid)
            stats["errors"] += 1
            print("ERROR (tier1)")
            continue

        if not classification["relevant"]:
            _store_result(
                db, aid,
                is_relevant=False,
                rejection_reason=classification["reason"],
                tier1_ms=tier1_ms,
            )
            stats["no_impact"] += 1
            stats["tier1_only"] += 1
            print(f"NO_IMPACT ({tier1_ms}ms) [{classification['reason']}]")
            continue

        # ── Build filtered I-tree (exclusion-based spotlight) ──
        triggers = classification["triggers"]
        exclude_l1s = classification.get("exclude_l1s", [])
        i_trees = taxonomy.format_i_trees_excluding(exclude_l1s)

        # ── Tier 2: Deep impact analysis with causal edges ──
        event_match = classification["event_match"]
        t2_start = time.time()
        event = None

        if event_match:
            event_id = event_match["event_id"]
            event = event_store.get_event(event_id)
            if event is None:
                logger.warning("Tier 1 matched non-existent event %s — treating as new", event_id)
                event_match = None

        if event_match and event:
            # Mode B: Event update (upsert)
            existing_edges = event_store.get_event_edges(event_id)
            result = analyzer.analyze_update_v2(
                title, summary, triggers, i_trees, existing_edges,
            )
            tier2_ms = int((time.time() - t2_start) * 1000)

            if result["is_relevant"]:
                event_store.upsert_event_edges(
                    event_id,
                    trigger_instances=result["trigger_instances"],
                    article_id=aid,
                    summary=result["summary"],
                    stage=result["stage"],
                )
                _store_result_v2(
                    db, aid, result,
                    event_id=event_id,
                    tier1_ms=tier1_ms, tier2_ms=tier2_ms,
                )
                stats["relevant"] += 1
                stats["events_updated"] += 1
                _update_stats_v2(stats, result)
                impact_str = _top_impacts_str(result)
                print(f"EVENT_UPDATE [{event['name'][:30]}] ({tier1_ms}+{tier2_ms}ms) [{impact_str}]")
            else:
                _store_result(
                    db, aid, is_relevant=False,
                    rejection_reason=result["rejection_reason"],
                    tier1_ms=tier1_ms, tier2_ms=tier2_ms,
                )
                stats["no_impact"] += 1
                print(f"NO_IMPACT (tier2 override, {tier1_ms}+{tier2_ms}ms) [{result['rejection_reason']}]")
        else:
            # Mode A: New event
            result = analyzer.analyze_new_v2(title, summary, triggers, i_trees)
            tier2_ms = int((time.time() - t2_start) * 1000)

            if result["is_relevant"]:
                event_name = classification.get("event_name") or title[:60]
                # Infer category from first trigger's L1
                first_trigger = triggers[0]["t_node"] if triggers else ""
                category = taxonomy.node_to_l1(first_trigger) if first_trigger else None

                event_id = event_store.create_event_v2(
                    name=event_name,
                    summary=result["summary"],
                    trigger_instances=result["trigger_instances"],
                    category=category,
                    seed_article_id=aid,
                    stage=result["stage"],
                )
                _store_result_v2(
                    db, aid, result,
                    event_id=event_id,
                    tier1_ms=tier1_ms, tier2_ms=tier2_ms,
                )
                stats["relevant"] += 1
                stats["events_created"] += 1
                _update_stats_v2(stats, result)
                impact_str = _top_impacts_str(result)
                print(f"NEW_EVENT [{event_name[:30]}] ({tier1_ms}+{tier2_ms}ms) [{impact_str}]")
            else:
                _store_result(
                    db, aid, is_relevant=False,
                    rejection_reason=result["rejection_reason"],
                    tier1_ms=tier1_ms, tier2_ms=tier2_ms,
                )
                stats["no_impact"] += 1
                print(f"NO_IMPACT (tier2, {tier1_ms}+{tier2_ms}ms) [{result['rejection_reason']}]")

    return stats


def _store_result(
    db: Database,
    article_id: str,
    *,
    is_relevant: bool,
    triggers: list[str] | None = None,
    impacts: list[dict] | None = None,
    rejection_reason: str | None = None,
    event_id: str | None = None,
    tier1_ms: int | None = None,
    tier2_ms: int | None = None,
) -> None:
    """Store classification result in article_impacts and mark article processed."""
    now = datetime.utcnow().isoformat()
    db.conn.execute(
        """INSERT OR REPLACE INTO article_impacts
           (article_id, is_relevant, triggers_json, impacts_json,
            rejection_reason, event_id, tier1_ms, tier2_ms, processed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            article_id,
            1 if is_relevant else 0,
            json.dumps(triggers) if triggers else None,
            json.dumps([dict(r) for r in impacts]) if impacts else None,
            rejection_reason,
            event_id,
            tier1_ms,
            tier2_ms,
            now,
        ),
    )
    db.conn.execute(
        "UPDATE articles SET processed = 1, processed_at = ? WHERE id = ?",
        (now, article_id),
    )
    db.conn.commit()


def _store_result_v2(
    db: Database,
    article_id: str,
    result,
    *,
    event_id: str | None = None,
    tier1_ms: int | None = None,
    tier2_ms: int | None = None,
) -> None:
    """Store v2 AnalysisResultV2 — flatten trigger_instances for article_impacts."""
    triggers = [ti["t_node"] for ti in result["trigger_instances"]]
    impacts = []
    for ti in result["trigger_instances"]:
        for e in ti.get("edges", []):
            impacts.append(e)
    _store_result(
        db, article_id,
        is_relevant=True,
        triggers=triggers,
        impacts=impacts,
        event_id=event_id,
        tier1_ms=tier1_ms,
        tier2_ms=tier2_ms,
    )


def _top_impacts_str(result) -> str:
    """Get top 3 impact node names from AnalysisResultV2."""
    nodes = []
    for ti in result["trigger_instances"]:
        for e in ti.get("edges", []):
            nodes.append(e["i_node"])
    return ", ".join(nodes[:3])


def _update_stats_v2(stats: dict, result) -> None:
    """Update running stats counters from an AnalysisResultV2."""
    for ti in result["trigger_instances"]:
        stats["triggers"][ti["t_node"]] += 1
        for e in ti.get("edges", [])[:3]:
            stats["top_impacts"][e["i_node"]] += 1


def _update_stats(stats: dict, result) -> None:
    """Update running stats counters from an AnalysisResult (legacy)."""
    for t in result.get("triggers", []):
        stats["triggers"][t] += 1
    for r in result.get("impacts", [])[:3]:
        stats["top_impacts"][r.get("node", "")] += 1


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
    if impacts:
        print(f"Relevant:           {relevant} ({relevant/impacts*100:.0f}%)")
        print(f"No impact:          {no_impact} ({no_impact/impacts*100:.0f}%)")

    # Latency stats
    rows = db.conn.execute(
        "SELECT tier1_ms, tier2_ms FROM article_impacts WHERE tier1_ms IS NOT NULL"
    ).fetchall()
    if rows:
        t1_times = [r["tier1_ms"] for r in rows]
        t2_times = [r["tier2_ms"] for r in rows if r["tier2_ms"] is not None]
        print(f"\n=== Latency ===")
        print(f"Tier 1 avg:         {sum(t1_times)/len(t1_times):.0f}ms ({len(t1_times)} calls)")
        if t2_times:
            print(f"Tier 2 avg:         {sum(t2_times)/len(t2_times):.0f}ms ({len(t2_times)} calls)")
            print(f"Tier 1 only:        {len(t1_times) - len(t2_times)} ({(len(t1_times) - len(t2_times))/len(t1_times)*100:.0f}% filtered at Tier 1)")

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
            """SELECT a.title, ai.triggers_json, ai.impacts_json, ai.event_id
               FROM article_impacts ai JOIN articles a ON ai.article_id = a.id
               WHERE ai.is_relevant = 1 ORDER BY ai.processed_at DESC LIMIT 5"""
        ).fetchall()
        print(f"\n=== Recent Relevant Articles ===")
        for r in rows:
            impacts_data = json.loads(r["impacts_json"] or "[]")
            impact_nodes = [i.get("i_node") or i.get("node", "?") for i in impacts_data[:3]]
            event_tag = f" [event:{r['event_id']}]" if r["event_id"] else ""
            print(f"  {r['title'][:70]}{event_tag}")
            print(f"    T: {r['triggers_json']}  I: {impact_nodes}")


def print_events(event_store: EventStore) -> None:
    """Print active events with article counts."""
    events = event_store.search_active_events()
    if not events:
        print("No active events.")
        return

    print(f"\n=== Active Events ({len(events)}) ===")
    for ev in events:
        triggers = ", ".join(ev["triggers"][:3])
        n_impacts = len(ev.get("current_impacts", []))
        print(f"  [{ev['event_id']}] {ev['name']}")
        print(f"    Stage: {ev['stage']} | Articles: {ev['article_count']} | Impacts: {n_impacts}")
        print(f"    Triggers: [{triggers}]")
        print(f"    Last updated: {ev['last_updated_at']}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-tier article ingestion pipeline")
    parser.add_argument("--limit", type=int, default=100, help="Max articles to process")
    parser.add_argument("--all", action="store_true", help="Process all unprocessed")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    parser.add_argument("--events", action="store_true", help="Show active events")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    db = Database(settings.db_path)
    db.init_schema()
    event_store = EventStore(db)

    if args.events:
        print_events(event_store)
        db.close()
        return

    if args.stats:
        print_stats(db)
        print_events(event_store)
        db.close()
        return

    # Resolve stale events and decay mature edges before processing
    resolved = event_store.resolve_stale_events()
    if resolved:
        print(f"Resolved {resolved} stale event(s).")
    decayed = event_store.decay_mature_edges(grace_days=14)
    if decayed:
        print(f"Decayed {decayed} mature impact edge(s).")
    if resolved or decayed:
        print()

    # Select articles
    limit = 999999 if args.all else args.limit
    articles = select_diverse_articles(db, limit)
    if not articles:
        print("No unprocessed articles.")
        db.close()
        return

    print(f"Selected {len(articles)} articles from {len(set(a['source'] for a in articles))} sources\n")

    # Init components
    print("Loading taxonomy...", end=" ", flush=True)
    taxonomy = TaxonomyContext.from_merged_graph(settings.graph_path)
    print("done.")

    gemini = GeminiClient()
    classifier = ArticleClassifier(gemini, event_store, taxonomy)
    analyzer = ImpactAnalyzer(taxonomy, gemini)

    active = event_store.search_active_events()
    print(f"Active events: {len(active)}")
    print(f"Tier 1 model: {settings.gemini_model} (+ T-tree ~6K tokens)")
    print(f"Tier 2 model: {settings.gemini_pro_model} (filtered I-tree)\n")

    # Process
    stats = process_articles(db, taxonomy, classifier, analyzer, event_store, articles)

    # Summary
    print(f"\n{'='*60}")
    print(f"DONE: {stats['total']} articles")
    print(f"  Relevant:       {stats['relevant']}")
    print(f"  No impact:      {stats['no_impact']}")
    print(f"  Deduped:        {stats['deduped']}")
    print(f"  Errors:         {stats['errors']}")
    print(f"  Tier 1 only:    {stats['tier1_only']}")
    print(f"  Events created: {stats['events_created']}")
    print(f"  Events updated: {stats['events_updated']}")

    if stats["triggers"]:
        print(f"\nTop triggers:")
        for t, c in stats["triggers"].most_common(10):
            print(f"  {t}: {c}")

    print_stats(db)
    db.close()


if __name__ == "__main__":
    main()
