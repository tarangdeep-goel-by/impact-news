"""Bridge: article_impacts -> user scoring -> article_matches.

Scores unmatched articles against user profiles and inserts delivery candidates.

Usage:
    from pipeline.delivery import score_new_articles_for_user, score_all_users

    # Score for one user
    count = score_new_articles_for_user(db, engine, user_id)

    # Score for all users
    total = score_all_users(db, engine)
"""

from __future__ import annotations

import json
import logging

from pipeline.database import Database
from profiling.engine import ProfileEngine
from profiling.matcher import score_article_for_user, classify_delivery_tier

logger = logging.getLogger(__name__)


def score_new_articles_for_user(
    db: Database,
    engine: ProfileEngine,
    user_id: str,
) -> int:
    """Score unmatched relevant articles against a user's profile.

    Returns count of new matches inserted.
    """
    profile = db.get_user_profile(user_id)
    if not profile:
        logger.warning("No profile for user %s", user_id)
        return 0

    node_weights = profile["node_weights_json"]  # Already parsed by get_user_profile
    user_city = profile.get("city", "") or ""

    # Resolve state from city via ProfileEngine
    user_state = ""
    if user_city:
        _, user_state, _ = engine.resolve_city(user_city)

    # Get relevant articles not yet matched for this user
    rows = db.conn.execute(
        """
        SELECT ai.article_id, a.title, a.source, a.url, ai.impacts_json
        FROM article_impacts ai
        JOIN articles a ON a.id = ai.article_id
        LEFT JOIN article_matches am
            ON am.article_id = ai.article_id AND am.user_id = ?
        WHERE ai.is_relevant = 1
          AND ai.impacts_json IS NOT NULL
          AND am.id IS NULL
        ORDER BY ai.processed_at DESC
        LIMIT 50
        """,
        (user_id,),
    ).fetchall()

    if not rows:
        return 0

    inserted = 0
    for row in rows:
        impacts_raw = row["impacts_json"]
        impacts = json.loads(impacts_raw) if isinstance(impacts_raw, str) else impacts_raw
        if not impacts:
            continue

        score, matched_nodes = score_article_for_user(
            impacts, node_weights, user_city=user_city, user_state=user_state,
        )

        tier = classify_delivery_tier(score)
        if tier == "skip":
            continue

        severity = "high" if tier == "push" else "medium"

        # Build explanation from top matched nodes
        explanation_parts = []
        for m in matched_nodes:
            rationale = m.get("rationale", "")
            explanation_parts.append(
                f"{m['node']} (weight {m['user_weight']}) — {rationale[:80]}"
            )
        explanation = "\n".join(explanation_parts)

        db.insert_match(
            article_id=row["article_id"],
            user_id=user_id,
            matched_nodes=matched_nodes,
            score=score,
            explanation=explanation,
            severity=severity,
        )
        inserted += 1

    logger.info("Scored %d articles for user %s: %d matches", len(rows), user_id, inserted)
    return inserted


def score_all_users(db: Database, engine: ProfileEngine) -> int:
    """Score unmatched articles for ALL users with profiles.

    Returns total matches inserted across all users.
    """
    user_ids = db.get_all_user_ids()
    if not user_ids:
        logger.info("No user profiles found")
        return 0

    total = 0
    for uid in user_ids:
        count = score_new_articles_for_user(db, engine, uid)
        total += count

    logger.info("Scored articles for %d users: %d total matches", len(user_ids), total)
    return total
