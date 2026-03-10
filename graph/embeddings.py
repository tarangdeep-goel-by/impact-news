"""FAISS index over node aliases for fast tag→node matching."""

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from graph.graph import ImpactGraph
from models import NodeMatch


class NodeMatcher:
    """Embeds node aliases and matches tags via FAISS cosine similarity."""

    def __init__(self, graph: ImpactGraph, model_name: str = "all-MiniLM-L6-v2"):
        self.graph = graph
        self.model_name = model_name
        self.encoder = SentenceTransformer(model_name)
        self.index: faiss.IndexFlatIP | None = None
        self.alias_mapping: list[dict[str, str]] = []  # [{node_id, alias}, ...]

    def build_index(self) -> None:
        """Embed all aliases and build FAISS IndexFlatIP."""
        pairs = self.graph.get_all_aliases()
        if not pairs:
            self.alias_mapping = []
            self.index = faiss.IndexFlatIP(384)
            return

        self.alias_mapping = [{"node_id": nid, "alias": alias} for nid, alias in pairs]
        aliases = [alias for _, alias in pairs]

        embeddings = self.encoder.encode(aliases, show_progress_bar=False)
        embeddings = embeddings.astype(np.float32)
        faiss.normalize_L2(embeddings)

        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

    def save(self, path: str) -> None:
        """Save FAISS index, alias mapping, and model name to disk."""
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(p / "embeddings.faiss"))
        payload = {"model_name": self.model_name, "aliases": self.alias_mapping}
        (p / "alias_mapping.json").write_text(json.dumps(payload, ensure_ascii=False))

    def load(self, path: str) -> None:
        """Load FAISS index and alias mapping from disk."""
        p = Path(path)

        self.index = faiss.read_index(str(p / "embeddings.faiss"))
        payload = json.loads((p / "alias_mapping.json").read_text())
        self.model_name = payload["model_name"]
        self.alias_mapping = payload["aliases"]
        self.encoder = SentenceTransformer(self.model_name)

    def match(self, tag: str, top_k: int = 5, threshold: float = 0.55) -> list[NodeMatch]:
        """Match a tag against the alias index, return results above threshold."""
        if self.index is None or self.index.ntotal == 0:
            return []

        vec = self.encoder.encode([tag], show_progress_bar=False).astype(np.float32)
        faiss.normalize_L2(vec)

        scores, indices = self.index.search(vec, min(top_k, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score < threshold:
                continue
            entry = self.alias_mapping[idx]
            results.append(NodeMatch(
                node_id=entry["node_id"],
                alias_matched=entry["alias"],
                score=float(score),
            ))

        return sorted(results, key=lambda m: m.score, reverse=True)

    def match_batch(
        self, tags: list[str], top_k: int = 5, threshold: float = 0.55
    ) -> dict[str, list[NodeMatch]]:
        """Match multiple tags, return dict of tag → matches."""
        return {tag: self.match(tag, top_k=top_k, threshold=threshold) for tag in tags}
