"""Event storage and lifecycle management."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from pipeline.database import Database


class EventStore:
    """SQLite-backed event storage and retrieval."""

    def __init__(self, db: Database) -> None:
        self.conn = db.conn

    def create_event(
        self,
        name: str,
        summary: str,
        triggers: list[str],
        impacts: list[dict],
        category: str | None,
        seed_article_id: str,
    ) -> str:
        """Create new event, link seed article. Returns event_id."""
        event_id = uuid.uuid4().hex[:12]
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            """INSERT INTO events
               (event_id, name, summary, triggers_json, current_impacts_json,
                stage, category, first_seen_at, last_updated_at, article_count)
               VALUES (?, ?, ?, ?, ?, 'new', ?, ?, ?, 1)""",
            (
                event_id,
                name,
                summary,
                json.dumps(triggers),
                json.dumps(impacts),
                category,
                now,
                now,
            ),
        )
        self.conn.execute(
            """INSERT INTO event_articles (event_id, article_id, is_seed)
               VALUES (?, ?, 1)""",
            (event_id, seed_article_id),
        )
        self.conn.commit()
        return event_id

    def update_event(
        self,
        event_id: str,
        summary: str,
        impacts: list[dict],
        stage: str | None = None,
        triggers: list[str] | None = None,
    ) -> None:
        """Update event summary, impacts, and optionally stage/triggers after a new article."""
        now = datetime.utcnow().isoformat()

        updates = [
            "summary = ?", "current_impacts_json = ?",
            "last_updated_at = ?", "article_count = article_count + 1",
        ]
        params: list = [summary, json.dumps(impacts), now]

        if stage:
            updates.append("stage = ?")
            params.append(stage)
        if triggers is not None:
            updates.append("triggers_json = ?")
            params.append(json.dumps(triggers))

        params.append(event_id)
        self.conn.execute(
            f"UPDATE events SET {', '.join(updates)} WHERE event_id = ?",
            params,
        )
        self.conn.commit()

    def link_article(self, event_id: str, article_id: str) -> None:
        """Link an article to an existing event."""
        self.conn.execute(
            "INSERT OR IGNORE INTO event_articles (event_id, article_id) VALUES (?, ?)",
            (event_id, article_id),
        )
        self.conn.commit()

    def get_event(self, event_id: str) -> dict | None:
        """Full event with all fields, JSON fields parsed."""
        row = self.conn.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["triggers"] = json.loads(d.pop("triggers_json"))
        d["current_impacts"] = json.loads(d.pop("current_impacts_json"))
        return d

    def get_event_articles(self, event_id: str) -> list[dict]:
        """All articles linked to this event, chronological."""
        rows = self.conn.execute(
            """SELECT ea.*, a.title, a.summary, a.url, a.source, a.published_at
               FROM event_articles ea
               JOIN articles a ON ea.article_id = a.id
               WHERE ea.event_id = ?
               ORDER BY ea.added_at""",
            (event_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_active_events(self, limit: int = 50) -> list[dict]:
        """All non-resolved events, most recent first. JSON fields parsed."""
        rows = self.conn.execute(
            """SELECT * FROM events
               WHERE stage != 'resolved'
               ORDER BY last_updated_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["triggers"] = json.loads(d.pop("triggers_json"))
            d["current_impacts"] = json.loads(d.pop("current_impacts_json"))
            results.append(d)
        return results

    def get_events_by_trigger(self, trigger_node: str) -> list[dict]:
        """Find active events that share a trigger node."""
        rows = self.conn.execute(
            """SELECT * FROM events
               WHERE stage != 'resolved'
               AND triggers_json LIKE ?""",
            (f'%"{trigger_node}"%',),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["triggers"] = json.loads(d.pop("triggers_json"))
            d["current_impacts"] = json.loads(d.pop("current_impacts_json"))
            results.append(d)
        return results

    def resolve_stale_events(self, days: int = 7) -> int:
        """Mark events with no new articles in N days as resolved. Returns count."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cursor = self.conn.execute(
            """UPDATE events SET stage = 'resolved'
               WHERE stage != 'resolved' AND last_updated_at < ?""",
            (cutoff,),
        )
        self.conn.commit()
        return cursor.rowcount

    def get_event_summary_list(self) -> list[dict]:
        """Short list of active events for Tier 1 prompt context.

        Returns: [{event_id, name, triggers, stage, category, last_updated_at}]
        """
        rows = self.conn.execute(
            """SELECT event_id, name, triggers_json, stage, category, last_updated_at
               FROM events
               WHERE stage != 'resolved'
               ORDER BY last_updated_at DESC
               LIMIT 50"""
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["triggers"] = json.loads(d.pop("triggers_json"))
            results.append(d)
        return results

    # -- V2: Causal Edges API -----------------------------------------------

    def create_event_v2(
        self,
        name: str,
        summary: str,
        trigger_instances: list[dict],
        category: str | None,
        seed_article_id: str,
        stage: str = "new",
    ) -> str:
        """Create event with hierarchical trigger instances and impact edges.

        trigger_instances: list of dicts with keys: t_node, context, edges.
            Each edge: {i_node, probability, magnitude, delay_days, polarity, mechanism}
        """
        event_id = uuid.uuid4().hex[:12]
        now = datetime.utcnow().isoformat()

        self.conn.execute(
            """INSERT INTO events
               (event_id, name, summary, triggers_json, current_impacts_json,
                stage, category, first_seen_at, last_updated_at, article_count)
               VALUES (?, ?, ?, '[]', '[]', ?, ?, ?, ?, 1)""",
            (event_id, name, summary, stage, category, now, now),
        )
        self.conn.execute(
            """INSERT INTO event_articles (event_id, article_id, is_seed)
               VALUES (?, ?, 1)""",
            (event_id, seed_article_id),
        )

        for ti in trigger_instances:
            ti_id = uuid.uuid4().hex[:12]
            self.conn.execute(
                """INSERT INTO trigger_instances (id, event_id, t_node, context)
                   VALUES (?, ?, ?, ?)""",
                (ti_id, event_id, ti["t_node"], ti.get("context", "")),
            )
            for edge in ti.get("edges", []):
                edge_id = uuid.uuid4().hex[:12]
                delay = int(edge.get("delay_days", 14))
                mat_date = (datetime.utcnow() + timedelta(days=delay)).strftime("%Y-%m-%d")
                self.conn.execute(
                    """INSERT INTO impact_edges
                       (id, trigger_instance_id, i_node, probability, magnitude,
                        delay_days, polarity, mechanism, maturity_date)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        edge_id, ti_id, edge["i_node"],
                        edge.get("probability", 0.5),
                        edge.get("magnitude", 0.5),
                        delay, edge.get("polarity", 1),
                        edge.get("mechanism", ""),
                        mat_date,
                    ),
                )
                self.conn.execute(
                    "INSERT OR IGNORE INTO edge_support (edge_id, article_id) VALUES (?, ?)",
                    (edge_id, seed_article_id),
                )

        self._recompute_event_denorm(event_id)
        self.conn.commit()
        return event_id

    def upsert_event_edges(
        self,
        event_id: str,
        trigger_instances: list[dict],
        article_id: str,
        summary: str | None = None,
        stage: str | None = None,
    ) -> None:
        """Upsert trigger instances and impact edges for an event.

        Instances/edges WITH 'id' key -> update existing.
        Instances/edges WITHOUT 'id' key -> insert new.
        """
        now = datetime.utcnow().isoformat()

        for ti in trigger_instances:
            if ti.get("id"):
                # Update existing trigger instance
                ti_id = ti["id"]
                self.conn.execute(
                    "UPDATE trigger_instances SET context = ? WHERE id = ?",
                    (ti.get("context", ""), ti_id),
                )
            else:
                # Insert new trigger instance
                ti_id = uuid.uuid4().hex[:12]
                self.conn.execute(
                    """INSERT INTO trigger_instances (id, event_id, t_node, context)
                       VALUES (?, ?, ?, ?)""",
                    (ti_id, event_id, ti["t_node"], ti.get("context", "")),
                )

            for edge in ti.get("edges", []):
                if edge.get("id"):
                    # Update existing edge
                    edge_id = edge["id"]
                    delay = int(edge.get("delay_days", 14))
                    mat_date = (datetime.utcnow() + timedelta(days=delay)).strftime("%Y-%m-%d")
                    self.conn.execute(
                        """UPDATE impact_edges SET
                           probability = ?, magnitude = ?, delay_days = ?,
                           polarity = ?, mechanism = ?, maturity_date = ?,
                           updated_at = ?
                           WHERE id = ?""",
                        (
                            edge.get("probability", 0.5),
                            edge.get("magnitude", 0.5),
                            delay, edge.get("polarity", 1),
                            edge.get("mechanism", ""),
                            mat_date, now, edge_id,
                        ),
                    )
                else:
                    # Insert new edge
                    edge_id = uuid.uuid4().hex[:12]
                    delay = int(edge.get("delay_days", 14))
                    mat_date = (datetime.utcnow() + timedelta(days=delay)).strftime("%Y-%m-%d")
                    self.conn.execute(
                        """INSERT INTO impact_edges
                           (id, trigger_instance_id, i_node, probability, magnitude,
                            delay_days, polarity, mechanism, maturity_date)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            edge_id, ti_id, edge["i_node"],
                            edge.get("probability", 0.5),
                            edge.get("magnitude", 0.5),
                            delay, edge.get("polarity", 1),
                            edge.get("mechanism", ""),
                            mat_date,
                        ),
                    )

                self.conn.execute(
                    "INSERT OR IGNORE INTO edge_support (edge_id, article_id) VALUES (?, ?)",
                    (edge_id, article_id),
                )

        # Link article to event
        self.conn.execute(
            "INSERT OR IGNORE INTO event_articles (event_id, article_id) VALUES (?, ?)",
            (event_id, article_id),
        )

        # Update event metadata
        updates = ["last_updated_at = ?", "article_count = article_count + 1"]
        params: list = [now]
        if summary:
            updates.append("summary = ?")
            params.append(summary)
        if stage:
            updates.append("stage = ?")
            params.append(stage)
        params.append(event_id)
        self.conn.execute(
            f"UPDATE events SET {', '.join(updates)} WHERE event_id = ?", params
        )

        self._recompute_event_denorm(event_id)
        self.conn.commit()

    def get_event_edges(self, event_id: str) -> list[dict]:
        """Get all trigger instances with their impact edges for an event.

        Returns list of TriggerInstance dicts with IDs populated.
        """
        ti_rows = self.conn.execute(
            """SELECT id, t_node, context FROM trigger_instances
               WHERE event_id = ? AND status = 'active'
               ORDER BY created_at""",
            (event_id,),
        ).fetchall()

        result = []
        for ti_row in ti_rows:
            edge_rows = self.conn.execute(
                """SELECT id, i_node, probability, magnitude, delay_days,
                          polarity, mechanism
                   FROM impact_edges
                   WHERE trigger_instance_id = ? AND status = 'active'
                   ORDER BY probability * magnitude DESC""",
                (ti_row["id"],),
            ).fetchall()

            result.append({
                "id": ti_row["id"],
                "t_node": ti_row["t_node"],
                "context": ti_row["context"],
                "edges": [dict(e) for e in edge_rows],
            })
        return result

    def decay_mature_edges(self, grace_days: int = 14) -> int:
        """Decay impact edges past maturity + grace period with no recent support.

        Returns count of decayed edges.
        """
        cutoff = (datetime.utcnow() - timedelta(days=grace_days)).strftime("%Y-%m-%d")
        cursor = self.conn.execute(
            """UPDATE impact_edges SET status = 'decayed'
               WHERE status = 'active'
               AND maturity_date IS NOT NULL
               AND maturity_date < ?
               AND id NOT IN (
                   SELECT edge_id FROM edge_support
                   WHERE added_at > ?
               )""",
            (cutoff, (datetime.utcnow() - timedelta(days=grace_days)).isoformat()),
        )
        self.conn.commit()
        return cursor.rowcount

    def _recompute_event_denorm(self, event_id: str) -> None:
        """Rebuild triggers_json and current_impacts_json from normalized tables."""
        edges_data = self.get_event_edges(event_id)

        triggers = list({ti["t_node"] for ti in edges_data})
        impacts = []
        for ti in edges_data:
            for e in ti.get("edges", []):
                impacts.append({
                    "node": e["i_node"],
                    "probability": e["probability"],
                    "magnitude": e["magnitude"],
                    "polarity": e.get("polarity", 1),
                    "delay_days": e.get("delay_days", 14),
                    "mechanism": e.get("mechanism", ""),
                })

        self.conn.execute(
            """UPDATE events SET triggers_json = ?, current_impacts_json = ?
               WHERE event_id = ?""",
            (json.dumps(triggers), json.dumps(impacts), event_id),
        )
