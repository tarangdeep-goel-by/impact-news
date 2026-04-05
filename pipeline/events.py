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

        Returns: [{event_id, name, summary, triggers, stage, category, last_updated_at}]
        """
        rows = self.conn.execute(
            """SELECT event_id, name, summary, triggers_json, stage, category, last_updated_at
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

    # -- V3: MacroShift + MicroImpact (flat M:N) ------------------------------

    def create_event_v3(
        self,
        name: str,
        summary: str,
        macro_shifts: list[dict],
        micro_impacts: list[dict],
        category: str | None,
        seed_article_id: str,
        stage: str = "new",
    ) -> str:
        """Create event with flat MacroShift + MicroImpact model.

        macro_shifts: list of {t_node, trajectory, context}
        micro_impacts: list of {i_node, trajectory, probability, magnitude,
                                delay_days, rationale, driving_t_nodes}
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

        for ms in macro_shifts:
            shift_id = uuid.uuid4().hex[:12]
            self.conn.execute(
                """INSERT INTO macro_shifts (id, event_id, t_node, trajectory, context)
                   VALUES (?, ?, ?, ?, ?)""",
                (shift_id, event_id, ms["t_node"], ms["trajectory"], ms.get("context", "")),
            )
            self.conn.execute(
                "INSERT INTO shift_support (macro_shift_id, article_id) VALUES (?, ?)",
                (shift_id, seed_article_id),
            )

        for mi in micro_impacts:
            self.conn.execute(
                """INSERT INTO micro_impact_revisions
                   (event_id, i_node, article_id, trajectory, probability,
                    magnitude, delay_days, rationale, driving_t_nodes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_id, mi["i_node"], seed_article_id,
                    mi.get("trajectory", "escalating"),
                    mi.get("probability", 0.5),
                    mi.get("magnitude", 0.5),
                    mi.get("delay_days", 14),
                    mi.get("rationale", ""),
                    json.dumps(mi.get("driving_t_nodes", [])),
                ),
            )
            self.conn.execute(
                """INSERT OR IGNORE INTO impact_support
                   (event_id, i_node, article_id) VALUES (?, ?, ?)""",
                (event_id, mi["i_node"], seed_article_id),
            )
            for t_node in mi.get("driving_t_nodes", []):
                row = self.conn.execute(
                    "SELECT id FROM macro_shifts WHERE event_id = ? AND t_node = ?",
                    (event_id, t_node),
                ).fetchone()
                if row:
                    self.conn.execute(
                        """INSERT OR IGNORE INTO impact_drivers
                           (event_id, i_node, macro_shift_id) VALUES (?, ?, ?)""",
                        (event_id, mi["i_node"], row["id"]),
                    )

        self._recompute_event_denorm_v3(event_id)
        self.conn.commit()
        return event_id

    def upsert_event_v3(
        self,
        event_id: str,
        macro_shifts: list[dict],
        micro_impacts: list[dict],
        article_id: str,
        summary: str | None = None,
        stage: str | None = None,
    ) -> None:
        """Upsert macro shifts and append micro impact revisions for an event."""
        now = datetime.utcnow().isoformat()

        # Link article
        self.conn.execute(
            "INSERT OR IGNORE INTO event_articles (event_id, article_id) VALUES (?, ?)",
            (event_id, article_id),
        )

        # Upsert macro shifts
        for ms in macro_shifts:
            shift_id = uuid.uuid4().hex[:12]
            self.conn.execute(
                """INSERT INTO macro_shifts (id, event_id, t_node, trajectory, context, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(event_id, t_node) DO UPDATE SET
                     trajectory = excluded.trajectory,
                     context = excluded.context,
                     updated_at = excluded.updated_at""",
                (shift_id, event_id, ms["t_node"], ms["trajectory"], ms.get("context", ""), now),
            )
            # Get the actual shift id (may be existing)
            row = self.conn.execute(
                "SELECT id FROM macro_shifts WHERE event_id = ? AND t_node = ?",
                (event_id, ms["t_node"]),
            ).fetchone()
            if row:
                self.conn.execute(
                    "INSERT OR IGNORE INTO shift_support (macro_shift_id, article_id) VALUES (?, ?)",
                    (row["id"], article_id),
                )

        # Append micro impact revisions (immutable)
        for mi in micro_impacts:
            self.conn.execute(
                """INSERT INTO micro_impact_revisions
                   (event_id, i_node, article_id, trajectory, probability,
                    magnitude, delay_days, rationale, driving_t_nodes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_id, mi["i_node"], article_id,
                    mi.get("trajectory", "escalating"),
                    mi.get("probability", 0.5),
                    mi.get("magnitude", 0.5),
                    mi.get("delay_days", 14),
                    mi.get("rationale", ""),
                    json.dumps(mi.get("driving_t_nodes", [])),
                ),
            )
            self.conn.execute(
                """INSERT OR IGNORE INTO impact_support
                   (event_id, i_node, article_id) VALUES (?, ?, ?)""",
                (event_id, mi["i_node"], article_id),
            )

        # Rebuild impact_drivers for this event
        self.conn.execute(
            "DELETE FROM impact_drivers WHERE event_id = ?", (event_id,)
        )
        cmi_rows = self.conn.execute(
            "SELECT i_node, driving_t_nodes FROM current_micro_impacts WHERE event_id = ?",
            (event_id,),
        ).fetchall()
        for cmi in cmi_rows:
            t_nodes = json.loads(cmi["driving_t_nodes"])
            for t_node in t_nodes:
                ms_row = self.conn.execute(
                    "SELECT id FROM macro_shifts WHERE event_id = ? AND t_node = ?",
                    (event_id, t_node),
                ).fetchone()
                if ms_row:
                    self.conn.execute(
                        """INSERT OR IGNORE INTO impact_drivers
                           (event_id, i_node, macro_shift_id) VALUES (?, ?, ?)""",
                        (event_id, cmi["i_node"], ms_row["id"]),
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

        self._recompute_event_denorm_v3(event_id)
        self.conn.commit()

    def get_event_state(self, event_id: str) -> dict:
        """Full current state: active macro shifts + latest micro impacts."""
        ms_rows = self.conn.execute(
            """SELECT id, t_node, trajectory, context FROM macro_shifts
               WHERE event_id = ? AND status = 'active'
               ORDER BY created_at""",
            (event_id,),
        ).fetchall()

        cmi_rows = self.conn.execute(
            """SELECT i_node, trajectory, probability, magnitude,
                      delay_days, rationale, driving_t_nodes
               FROM current_micro_impacts WHERE event_id = ?""",
            (event_id,),
        ).fetchall()

        return {
            "macro_shifts": [dict(r) for r in ms_rows],
            "micro_impacts": [
                {
                    "i_node": r["i_node"],
                    "trajectory": r["trajectory"],
                    "probability": r["probability"],
                    "magnitude": r["magnitude"],
                    "delay_days": r["delay_days"],
                    "rationale": r["rationale"],
                    "driving_t_nodes": json.loads(r["driving_t_nodes"]),
                }
                for r in cmi_rows
            ],
        }

    def get_compressed_state(self, event_id: str) -> str:
        """Compressed text summary of event state for Tier 2 prompt."""
        state = self.get_event_state(event_id)

        shifts = ", ".join(
            f"{ms['t_node']} ({ms['trajectory']})"
            for ms in state["macro_shifts"]
        )
        impacts = ", ".join(
            f"{mi['i_node']} (prob={mi['probability']}, mag={mi['magnitude']}, {mi['delay_days']}d)"
            for mi in state["micro_impacts"]
        )

        lines = []
        if shifts:
            lines.append(f"Active Shifts: {shifts}")
        if impacts:
            lines.append(f"Active Impacts: {impacts}")
        return "\n".join(lines)

    def _recompute_event_denorm_v3(self, event_id: str) -> None:
        """Rebuild triggers_json and current_impacts_json from V3 tables."""
        t_rows = self.conn.execute(
            "SELECT DISTINCT t_node FROM macro_shifts WHERE event_id = ?",
            (event_id,),
        ).fetchall()
        triggers = [r["t_node"] for r in t_rows]

        cmi_rows = self.conn.execute(
            """SELECT i_node, probability, magnitude, delay_days, rationale
               FROM current_micro_impacts WHERE event_id = ?""",
            (event_id,),
        ).fetchall()
        impacts = [
            {
                "node": r["i_node"],
                "probability": r["probability"],
                "magnitude": r["magnitude"],
                "delay_days": r["delay_days"],
                "rationale": r["rationale"],
            }
            for r in cmi_rows
        ]

        self.conn.execute(
            """UPDATE events SET triggers_json = ?, current_impacts_json = ?
               WHERE event_id = ?""",
            (json.dumps(triggers), json.dumps(impacts), event_id),
        )

    def get_event_summary_list_v3(self) -> list[dict]:
        """Active events with macro shift details for Tier 1 prompt context."""
        rows = self.conn.execute(
            """SELECT event_id, name, summary, stage, category, last_updated_at
               FROM events
               WHERE stage != 'resolved'
               ORDER BY last_updated_at DESC
               LIMIT 50"""
        ).fetchall()

        results = []
        for row in rows:
            d = dict(row)
            ms_rows = self.conn.execute(
                """SELECT t_node, trajectory FROM macro_shifts
                   WHERE event_id = ? AND status = 'active'""",
                (d["event_id"],),
            ).fetchall()
            d["macro_shifts"] = [dict(r) for r in ms_rows]
            results.append(d)
        return results
