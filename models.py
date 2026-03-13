"""Pydantic models for Impact News."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

from pydantic import BaseModel, Field


class Node(BaseModel):
    id: str
    aliases: list[str] = []
    category: str = ""          # T1-T5, I1-I11
    is_category: bool = False
    status: str = "active"      # active | deprecated | merged
    merged_into: str | None = None  # For Rule 16 mergers
    port: bool = False          # Receives bridge edges (T→I)
    portal: bool = False        # Has cross-L1 edges within same world
    secondary_tags: list[str] = []  # Rule 4: secondary L1 relevance
    level: int | None = None    # L1=1, L2=2, L3=3


class Edge(BaseModel):
    from_node: str
    to_node: str
    type: str
    description: str = ""
    weight: float = 1.0
    polarity: int = 0
    delay: str = "SHORT_TERM"


class Article(BaseModel):
    id: str = ""
    title: str
    summary: str = ""
    url: str
    source: str = "Unknown"
    published_at: datetime | None = None
    fingerprint: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def model_post_init(self, __context: object) -> None:
        if not self.id:
            self.id = hashlib.sha256(self.url.encode()).hexdigest()
        if not self.fingerprint:
            normalized = re.sub(r"[^a-z0-9]", "", self.title.lower())
            self.fingerprint = normalized[:50]


class Source(BaseModel):
    id: str = ""
    name: str
    url: str
    feed_type: str = "rss"
    category: str = ""
    reliability_score: float = 1.0
    active: bool = True


class UserEdge(BaseModel):
    node_id: str
    relation: str
    importance: float = 1.0


class UserGraph(BaseModel):
    user_id: str
    edges: list[UserEdge] = []
    reachable_nodes: set[str] = set()
    completed_tiers: list[str] = []  # ["tier1", "investments", "health", ...]
    income_multiplier: float = 1.0  # importance scaling based on income range


class NodeMatch(BaseModel):
    node_id: str
    alias_matched: str
    score: float


class TagExtractionResult(BaseModel):
    article_id: str
    tags: list[str] = []
    indirect_effects: list[str] = []
    domains: list[str] = []


class ArticleImpact(BaseModel):
    article_id: str
    matched_nodes: list[dict] = []  # [{node_id, tag, match_score, graph_score, combined}]
    top_score: float = 0.0
    severity: str = "low"
    explanation: str = ""


class CollectionResult(BaseModel):
    total_fetched: int = 0
    after_dedup: int = 0
    new_inserted: int = 0
    errors: list[str] = []
