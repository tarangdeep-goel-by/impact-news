"""Full pipeline trace: RSS → T1 → T2 → confidence filter → user match → delivery.

Generates a readable markdown log of the entire flow for a given user profile.

Usage:
    python -m scripts.pipeline_trace --limit 15
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from engine.classifier import ArticleClassifier
from engine.confidence_filter import filter_impacts, classify_confidence, compute_score
from engine.llm_engine import ImpactAnalyzer
from engine.taxonomy_context import TaxonomyContext
from pipeline.database import Database
from pipeline.gemini import GeminiClient
from pipeline.events import EventStore
from profiling.engine import ProfileEngine
from profiling.matcher import score_article_for_user, classify_delivery_tier
from profiling.universals import UNIVERSAL_NODES


def run_trace(limit: int = 15, user_answers: dict | None = None):
    """Run full pipeline trace and return markdown string."""

    # ── Setup ──
    # Use main repo DB which has collected articles
    import os
    main_db = os.path.join(os.path.dirname(__file__), "../../impact-news/data/impact_news.db")
    db = Database(main_db)
    db.init_schema()
    taxonomy = TaxonomyContext.from_merged_graph()
    gemini = GeminiClient()
    event_store = EventStore(db)
    classifier = ArticleClassifier(gemini, event_store, taxonomy)
    analyzer = ImpactAnalyzer(taxonomy, gemini)

    engine = ProfileEngine()

    if user_answers is None:
        user_answers = {
            "s0_city": "Bangalore",
            "s0_work": "corporate",
            "s0_transport": ["petrol_vehicle"],
            "s0_housing": "rent",
            "s0_family": ["none"],
        }

    user_profile = engine.compute_profile(user_answers)
    city_tier = engine.resolve_city(user_answers.get("s0_city", ""))[0]

    # ── Select articles ──
    articles = db.conn.execute(
        """SELECT id, title, summary, source, url
           FROM articles WHERE processed = 0
           ORDER BY RANDOM() LIMIT ?""",
        (limit,),
    ).fetchall()

    lines = []
    w = lines.append

    w(f"# Impact News — Full Pipeline Trace")
    w(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    w(f"**Articles:** {len(articles)} sampled from {db.conn.execute('SELECT COUNT(*) FROM articles').fetchone()[0]} collected")
    w(f"**Models:** Tier 1 = `{settings.gemini_model}`, Tier 2 = `{settings.gemini_pro_model}`")
    w("")

    # ── User profile section ──
    w("---")
    w("## User Profile")
    w("")
    w(f"| Field | Value |")
    w(f"|-------|-------|")
    w(f"| City | {user_answers.get('s0_city', '?')} ({city_tier}) |")
    w(f"| Work | {user_answers.get('s0_work', '?')} |")
    transport = user_answers.get("s0_transport", [])
    w(f"| Transport | {', '.join(transport) if isinstance(transport, list) else transport} |")
    w(f"| Housing | {user_answers.get('s0_housing', '?')} |")
    family = user_answers.get("s0_family", [])
    w(f"| Dependents | {', '.join(family) if isinstance(family, list) else family} |")
    w(f"| **Nodes activated** | **{len(user_profile)}** (17 universal + {len(user_profile) - 17} personal) |")
    w("")

    non_univ = {k: v for k, v in user_profile.items() if k not in UNIVERSAL_NODES}
    top_nodes = sorted(non_univ.items(), key=lambda x: -x[1])[:10]
    w("**Top personal nodes:**")
    for node, weight in top_nodes:
        w(f"- `{node}`: {weight}")
    w("")

    # ── Process articles ──
    w("---")
    w("## Pipeline Trace")
    w("")

    delivery_results = []
    stats = {"total": len(articles), "relevant": 0, "no_impact": 0, "errors": 0, "deduped": 0}

    for i, article in enumerate(articles):
        aid = article["id"]
        title = article["title"]
        summary = article["summary"] or ""
        source = article["source"]

        w(f"### Article {i+1}: {title}")
        w(f"**Source:** {source}  ")
        if summary:
            w(f"**Summary:** {summary[:200]}{'...' if len(summary) > 200 else ''}")
        w("")

        # ── TIER 1: Classification ──
        w("#### Tier 1: Classification")
        t1_start = time.time()
        try:
            classification = classifier.classify_v3(title, summary)
        except Exception as e:
            w(f"**ERROR:** `{e}`")
            w("")
            stats["errors"] += 1
            continue
        tier1_ms = int((time.time() - t1_start) * 1000)

        if classification is None:
            w(f"**Result:** ERROR (null response) | {tier1_ms}ms")
            w("")
            stats["errors"] += 1
            continue

        w(f"- **Relevant:** {'Yes' if classification['relevant'] else 'No'}")
        w(f"- **Latency:** {tier1_ms}ms")

        if not classification["relevant"]:
            reason = classification.get("reason", "unknown")
            w(f"- **Rejection:** {reason}")
            w(f"- **Verdict:** FILTERED — does not affect citizens at scale")
            w("")
            stats["no_impact"] += 1
            # Store
            db.conn.execute(
                "INSERT OR REPLACE INTO article_impacts (article_id, is_relevant, rejection_reason, processed_at) VALUES (?, 0, ?, ?)",
                (aid, reason, datetime.utcnow().isoformat()),
            )
            db.conn.execute("UPDATE articles SET processed = 1 WHERE id = ?", (aid,))
            db.conn.commit()
            continue

        # Show T1 details
        macro_shifts = classification.get("macro_shifts", [])
        exclude_l1s = classification.get("exclude_l1s", [])
        event_name = classification.get("event_name", "")

        w(f"- **Macro shifts:** {len(macro_shifts)}")
        for ms in macro_shifts:
            w(f"  - `{ms['t_node']}` ({ms.get('trajectory', '?')})")
        if exclude_l1s:
            w(f"- **Excluded I-world L1s:** {', '.join(exclude_l1s)}")
        if event_name:
            w(f"- **Event name:** {event_name}")
        w("")

        # ── TIER 2: Impact Analysis ──
        w("#### Tier 2: Impact Analysis")
        i_trees = taxonomy.format_i_trees_excluding(exclude_l1s)

        t2_start = time.time()
        try:
            result = analyzer.analyze_new_v3(title, summary, macro_shifts, i_trees)
        except Exception as e:
            w(f"**ERROR:** `{e}`")
            w("")
            stats["errors"] += 1
            continue
        tier2_ms = int((time.time() - t2_start) * 1000)

        if not result["is_relevant"]:
            w(f"- **Result:** Tier 2 override — NOT RELEVANT")
            w(f"- **Reason:** {result.get('rejection_reason', '?')}")
            w(f"- **Latency:** {tier2_ms}ms")
            w("")
            stats["no_impact"] += 1
            db.conn.execute(
                "INSERT OR REPLACE INTO article_impacts (article_id, is_relevant, rejection_reason, tier1_ms, tier2_ms, processed_at) VALUES (?, 0, ?, ?, ?, ?)",
                (aid, result.get("rejection_reason"), tier1_ms, tier2_ms, datetime.utcnow().isoformat()),
            )
            db.conn.execute("UPDATE articles SET processed = 1 WHERE id = ?", (aid,))
            db.conn.commit()
            continue

        micro_impacts = result.get("micro_impacts", [])
        w(f"- **Latency:** {tier2_ms}ms")
        w(f"- **Summary:** {result.get('summary', 'N/A')}")
        w(f"- **Micro-impacts:** {len(micro_impacts)}")
        w("")

        if micro_impacts:
            w("| I-Node | Prob | Mag | Score | Trajectory | Rationale |")
            w("|--------|------|-----|-------|------------|-----------|")
            for imp in sorted(micro_impacts, key=lambda x: x.get("probability", 0) * x.get("magnitude", 0), reverse=True):
                node = imp.get("i_node", "?")
                prob = imp.get("probability", 0)
                mag = imp.get("magnitude", 0)
                score = round(prob * mag, 3)
                traj = imp.get("trajectory", "?")
                rationale = imp.get("rationale", "")[:80]
                w(f"| `{node}` | {prob} | {mag} | {score} | {traj} | {rationale} |")
            w("")

        # ── Confidence Filter ──
        w("#### Confidence Filter")
        filtered = filter_impacts(micro_impacts, min_tier="low")
        tier_counts = {"high": 0, "medium": 0, "low": 0}
        for f_imp in filtered:
            tier_counts[f_imp["confidence_tier"]] += 1

        w(f"- **High confidence:** {tier_counts['high']} impacts")
        w(f"- **Medium confidence:** {tier_counts['medium']} impacts")
        w(f"- **Low confidence:** {tier_counts['low']} impacts")
        w("")

        # ── User Matching ──
        w("#### User Match")
        user_score, matched_nodes = score_article_for_user(micro_impacts, user_profile)
        delivery_tier = classify_delivery_tier(user_score)

        w(f"- **Personal relevance:** {user_score:.3f}")
        w(f"- **Delivery tier:** `{delivery_tier}`")
        w("")

        if matched_nodes:
            w("| Matched Node | Impact Score | User Weight | Personal Score |")
            w("|-------------|-------------|-------------|----------------|")
            for m in matched_nodes:
                w(f"| `{m['node']}` | {m['impact_score']} | {m['user_weight']} | {m['personal_score']} |")
            w("")

        if not matched_nodes:
            w("_No impact nodes overlap with user profile._")
            w("")

        # Store in DB
        triggers_json = json.dumps([ms["t_node"] for ms in macro_shifts])
        impacts_json = json.dumps(micro_impacts)
        event_id_str = None
        if event_name:
            category = taxonomy.node_to_l1(macro_shifts[0]["t_node"]) if macro_shifts else None
            event_id_str = event_store.create_event_v3(
                name=event_name,
                summary=result.get("summary", ""),
                macro_shifts=macro_shifts,
                micro_impacts=micro_impacts,
                category=category,
                seed_article_id=aid,
                stage=result.get("stage", "new"),
            )

        db.conn.execute(
            """INSERT OR REPLACE INTO article_impacts
               (article_id, is_relevant, triggers_json, impacts_json, event_id, tier1_ms, tier2_ms, processed_at)
               VALUES (?, 1, ?, ?, ?, ?, ?, ?)""",
            (aid, triggers_json, impacts_json, event_id_str, tier1_ms, tier2_ms, datetime.utcnow().isoformat()),
        )
        db.conn.execute("UPDATE articles SET processed = 1 WHERE id = ?", (aid,))
        db.conn.commit()

        stats["relevant"] += 1
        delivery_results.append({
            "title": title,
            "source": source,
            "score": user_score,
            "tier": delivery_tier,
            "matched": matched_nodes,
            "impacts_count": len(micro_impacts),
        })

    # ── Summary ──
    w("---")
    w("## Summary")
    w("")
    w(f"| Metric | Count |")
    w(f"|--------|-------|")
    w(f"| Articles processed | {stats['total']} |")
    w(f"| Relevant (passed T1+T2) | {stats['relevant']} |")
    w(f"| Filtered (no citizen impact) | {stats['no_impact']} |")
    w(f"| Errors | {stats['errors']} |")
    w("")

    # ── Delivery Feed ──
    w("## Your Personalized Feed")
    w(f"_Profile: {user_answers.get('s0_city', '?')} / {user_answers.get('s0_work', '?')} / {', '.join(transport) if isinstance(transport, list) else transport} / {user_answers.get('s0_housing', '?')}_")
    w("")

    delivery_results.sort(key=lambda x: -x["score"])

    push = [r for r in delivery_results if r["tier"] == "push"]
    digest = [r for r in delivery_results if r["tier"] == "digest"]
    skip = [r for r in delivery_results if r["tier"] == "skip"]

    if push:
        w("### Push Notifications (score >= 0.5)")
        for r in push:
            top_nodes = ", ".join(f"`{m['node']}`" for m in r["matched"])
            w(f"- **[{r['score']:.2f}]** {r['title']}  ")
            w(f"  _{r['source']}_ | Why: {top_nodes}")
        w("")

    if digest:
        w("### Daily Digest (score 0.2 - 0.5)")
        for r in digest:
            top_nodes = ", ".join(f"`{m['node']}`" for m in r["matched"])
            w(f"- **[{r['score']:.2f}]** {r['title']}  ")
            w(f"  _{r['source']}_ | Why: {top_nodes}")
        w("")

    if skip:
        w("### Skipped (score < 0.2)")
        for r in skip:
            top_nodes = ", ".join(f"`{m['node']}`" for m in r["matched"]) if r["matched"] else "no overlap"
            w(f"- [{r['score']:.2f}] {r['title']} — {top_nodes}")
        w("")

    if not delivery_results:
        w("_No relevant articles found in this batch._")
        w("")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--output", type=str, default="data/pipeline_trace.md")
    args = parser.parse_args()

    print(f"Running pipeline trace on {args.limit} articles...")
    md = run_trace(limit=args.limit)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    print(f"\nTrace written to {out} ({len(md)} chars)")
