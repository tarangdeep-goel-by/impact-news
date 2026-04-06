"""Unified pipeline: collect → T1 → T2 → score → deliver to Telegram.

Single-pass flow that processes articles end-to-end and delivers
matched ones to the user. Logs every step at the article level.

Usage:
    python -m pipeline.run                     # 20 articles
    python -m pipeline.run --limit 50          # custom limit
    python -m pipeline.run --collect           # collect fresh articles first
    python -m pipeline.run --dry-run           # score + log but don't send to Telegram
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from collections import Counter
from datetime import datetime

from config import settings
from engine.classifier import ArticleClassifier
from engine.confidence_filter import filter_impacts
from engine.llm_engine import ImpactAnalyzer
from engine.taxonomy_context import TaxonomyContext
from pipeline.database import Database
from pipeline.events import EventStore
from pipeline.gemini import GeminiClient
from pipeline.ingest import select_diverse_articles, TitleDeduplicator, _store_result, _store_result_v3
from profiling.engine import ProfileEngine
from profiling.matcher import score_article_for_user, classify_delivery_tier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline(
    limit: int = 20,
    collect_first: bool = False,
    dry_run: bool = False,
) -> None:
    """Run the complete pipeline: collect → classify → analyze → score → deliver."""

    # ── Setup ──
    db = Database(settings.db_path)
    db.init_schema()
    taxonomy = TaxonomyContext.from_merged_graph()
    gemini = GeminiClient()
    event_store = EventStore(db)
    classifier = ArticleClassifier(gemini, event_store, taxonomy)
    analyzer = ImpactAnalyzer(taxonomy, gemini)
    engine = ProfileEngine()

    # ── Collect if requested ──
    if collect_first:
        from pipeline.collector import ArticleCollector
        from pipeline.dedup import Deduplicator
        dedup = Deduplicator(db)
        collector = ArticleCollector(db, dedup)
        result = asyncio.run(collector.run())
        logger.info("Collected: %d fetched, %d new", result.total_fetched, result.new_inserted)

    # ── Load user profile (single user for now) ──
    user_ids = db.get_all_user_ids()
    if not user_ids:
        logger.warning("No user profiles found. Run the bot and /start first.")
        return

    user_id = user_ids[0]
    profile = db.get_user_profile(user_id)
    node_weights = profile["node_weights_json"]
    user_city = profile.get("city", "")
    user_state = ""
    if user_city:
        _, user_state, _ = engine.resolve_city(user_city)

    chat_id = profile.get("telegram_chat_id", settings.telegram_chat_id)

    logger.info("User: %s (%s, %s) — %d nodes active", user_id, user_city, user_state, len(node_weights))

    # ── Select articles ──
    articles = select_diverse_articles(db, limit)
    if not articles:
        logger.info("No unprocessed articles")
        return

    logger.info("Processing %d articles", len(articles))

    # ── Telegram bot (for delivery) ──
    bot = None
    if not dry_run:
        try:
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
            bot = Bot(token=settings.telegram_bot_token)
        except Exception as e:
            logger.warning("Telegram bot init failed: %s — will log only", e)

    title_dedup = TitleDeduplicator(db)
    stats = Counter()
    delivered = []

    for i, article in enumerate(articles):
        aid = article["id"]
        title = article["title"]
        summary = article.get("summary", "")
        source = article.get("source", "Unknown")

        print(f"\n[{i+1}/{len(articles)}] {title[:75]}")
        print(f"  Source: {source}")

        # ── Dedup ──
        if title_dedup.is_duplicate(title):
            _store_result(db, aid, is_relevant=False, rejection_reason="title_near_duplicate")
            stats["deduped"] += 1
            print(f"  T1: DEDUP (title similarity)")
            continue
        title_dedup.add(title)

        # ── TIER 1 ──
        t1_start = time.time()
        try:
            classification = classifier.classify_v3(title, summary)
        except Exception as e:
            logger.error("T1 error for %s: %s", aid[:12], e)
            stats["errors"] += 1
            print(f"  T1: ERROR — {e}")
            continue

        tier1_ms = int((time.time() - t1_start) * 1000)

        if classification is None:
            stats["errors"] += 1
            print(f"  T1: ERROR (null response) [{tier1_ms}ms]")
            continue

        if not classification["relevant"]:
            reason = classification.get("reason", "?")
            _store_result(db, aid, is_relevant=False, rejection_reason=reason, tier1_ms=tier1_ms)
            stats["filtered"] += 1
            print(f"  T1: FILTERED [{tier1_ms}ms] — {reason[:80]}")
            continue

        macro_shifts = classification.get("macro_shifts", [])
        exclude_l1s = classification.get("exclude_l1s", [])
        triggers = [s["t_node"] for s in macro_shifts]

        print(f"  T1: RELEVANT [{tier1_ms}ms] triggers={triggers}")

        # ── TIER 2 ──
        i_trees = taxonomy.format_i_trees_excluding(exclude_l1s)
        t2_start = time.time()
        try:
            result = analyzer.analyze_new_v3(title, summary, macro_shifts, i_trees)
        except Exception as e:
            logger.error("T2 error for %s: %s", aid[:12], e)
            stats["errors"] += 1
            print(f"  T2: ERROR — {e}")
            continue

        tier2_ms = int((time.time() - t2_start) * 1000)

        if not result["is_relevant"]:
            _store_result(db, aid, is_relevant=False,
                         rejection_reason=result.get("rejection_reason"),
                         tier1_ms=tier1_ms, tier2_ms=tier2_ms)
            stats["t2_filtered"] += 1
            print(f"  T2: FILTERED [{tier2_ms}ms] — {result.get('rejection_reason', '?')}")
            continue

        micro_impacts = result.get("micro_impacts", [])

        # Store in DB
        event_name = classification.get("event_name") or title[:60]
        first_t = macro_shifts[0]["t_node"] if macro_shifts else ""
        category = taxonomy.node_to_l1(first_t) if first_t else None

        event_id = event_store.create_event_v3(
            name=event_name,
            summary=result.get("summary", ""),
            macro_shifts=macro_shifts,
            micro_impacts=micro_impacts,
            category=category,
            seed_article_id=aid,
            stage=result.get("stage", "new"),
        )
        _store_result_v3(db, aid, macro_shifts, result,
                         event_id=event_id, tier1_ms=tier1_ms, tier2_ms=tier2_ms)

        stats["relevant"] += 1

        # Show impacts
        print(f"  T2: {len(micro_impacts)} impacts [{tier2_ms}ms]")
        for imp in sorted(micro_impacts, key=lambda x: x.get("probability", 0) * x.get("magnitude", 0), reverse=True)[:5]:
            node = imp.get("i_node", "?")
            prob = imp.get("probability", 0)
            mag = imp.get("magnitude", 0)
            scope = imp.get("scope", "national")
            print(f"      {node}: p={prob} m={mag} scope={scope}")

        # ── SCORE against user profile ──
        score, matched = score_article_for_user(micro_impacts, node_weights,
                                                 user_city=user_city, user_state=user_state)
        tier = classify_delivery_tier(score)

        print(f"  Match: score={score:.3f} tier={tier}")
        if matched:
            for m in matched:
                print(f"      {m['node']}: impact={m['impact_score']} × weight={m['user_weight']} = {m['personal_score']}")

        if tier == "skip":
            print(f"  → Skipped (below threshold)")
            continue

        # ── INSERT MATCH ──
        severity = "high" if tier == "push" else "medium"
        explanation = "\n".join(
            f"{m['node']} — {m.get('rationale', '')[:80]}" for m in matched
        )
        db.insert_match(
            article_id=aid, user_id=user_id, matched_nodes=matched,
            score=score, explanation=explanation, severity=severity,
        )

        # ── DELIVER to Telegram ──
        if bot and not dry_run:
            emoji = "\U0001f534" if tier == "push" else "\U0001f7e1"
            tier_label = "PUSH" if tier == "push" else "DIGEST"

            why_parts = []
            for m in matched[:3]:
                why_parts.append(f"\u2022 {m['node']} \u2014 {m.get('rationale', '')[:80]}")
            why_text = "\n".join(why_parts)

            url = article.get("url", "")
            url_line = f"\n\n[Read Article]({url})" if url else ""

            text = (
                f"{emoji} {tier_label} | Score: {score:.2f}\n\n"
                f"*{title}*\n"
                f"_{source}_\n\n"
                f"Why this affects you:\n"
                f"{why_text}"
                f"{url_line}"
            )

            try:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                # Get match_id for feedback buttons
                match_row = db.conn.execute(
                    "SELECT id FROM article_matches WHERE article_id = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
                    (aid, user_id),
                ).fetchone()
                match_id = match_row["id"] if match_row else 0

                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("\U0001f44d Relevant", callback_data=f"fb|{match_id}|rel"),
                        InlineKeyboardButton("\U0001f44e Not Relevant", callback_data=f"fb|{match_id}|not"),
                    ]
                ])

                asyncio.run(bot.send_message(
                    chat_id=chat_id, text=text, parse_mode="Markdown",
                    disable_web_page_preview=True, reply_markup=keyboard,
                ))
                db.mark_delivered(match_id)
                print(f"  → DELIVERED to Telegram")
                delivered.append({"title": title, "score": score, "tier": tier})
            except Exception as e:
                logger.warning("Delivery failed: %s", e)
                print(f"  → Delivery failed: {e}")
        else:
            print(f"  → Would deliver ({tier})")
            delivered.append({"title": title, "score": score, "tier": tier})

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE")
    print(f"  Processed: {len(articles)}")
    print(f"  Deduped: {stats['deduped']}")
    print(f"  T1 filtered: {stats['filtered']}")
    print(f"  T2 filtered: {stats['t2_filtered']}")
    print(f"  Relevant: {stats['relevant']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Delivered: {len(delivered)}")
    if delivered:
        print(f"\n  Your feed:")
        for d in sorted(delivered, key=lambda x: -x["score"]):
            icon = "*" if d["tier"] == "push" else "+"
            print(f"  {icon} [{d['score']:.2f}] {d['title'][:65]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified pipeline: collect → T1 → T2 → score → deliver")
    parser.add_argument("--limit", type=int, default=20, help="Articles to process")
    parser.add_argument("--collect", action="store_true", help="Collect fresh articles from RSS first")
    parser.add_argument("--dry-run", action="store_true", help="Score and log but don't send to Telegram")
    args = parser.parse_args()

    run_pipeline(limit=args.limit, collect_first=args.collect, dry_run=args.dry_run)
