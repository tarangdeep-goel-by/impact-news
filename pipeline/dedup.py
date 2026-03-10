"""Two-layer article deduplication: exact (URL hash + fingerprint) and near (MinHash LSH)."""

from __future__ import annotations

import logging

from datasketch import MinHash, MinHashLSH

from models import Article
from pipeline.database import Database

logger = logging.getLogger(__name__)

NUM_PERM = 128
JACCARD_THRESHOLD = 0.8


def _minhash_from_title(title: str) -> MinHash:
    """Build a MinHash signature from word-level shingles of the title."""
    m = MinHash(num_perm=NUM_PERM)
    for token in title.lower().split():
        m.update(token.encode("utf-8"))
    return m


class Deduplicator:
    """Two-layer deduplication: exact hash lookup then MinHash near-duplicate detection."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self._seen_hashes: set[str] = set()
        self._lsh = MinHashLSH(threshold=JACCARD_THRESHOLD, num_perm=NUM_PERM)
        self._minhashes: dict[str, MinHash] = {}

    # ------------------------------------------------------------------
    # Layer 1: exact dedup
    # ------------------------------------------------------------------

    def is_duplicate_exact(self, article: Article) -> bool:
        """Return True if the article's URL hash or fingerprint is already seen."""
        return article.id in self._seen_hashes or article.fingerprint in self._seen_hashes

    # ------------------------------------------------------------------
    # Layer 2: near dedup
    # ------------------------------------------------------------------

    def is_duplicate_near(self, article: Article) -> bool:
        """Return True if a near-duplicate title exists in the LSH index (Jaccard > 0.8)."""
        mh = _minhash_from_title(article.title)
        return len(self._lsh.query(mh)) > 0

    # ------------------------------------------------------------------
    # Batch
    # ------------------------------------------------------------------

    def deduplicate_batch(self, articles: list[Article]) -> list[Article]:
        """Run both dedup layers and return unique articles."""
        self._seen_hashes = self.db.get_seen_hashes()
        self._lsh = MinHashLSH(threshold=JACCARD_THRESHOLD, num_perm=NUM_PERM)
        self._minhashes = {}

        unique: list[Article] = []

        for article in articles:
            if self.is_duplicate_exact(article):
                continue
            if self.is_duplicate_near(article):
                continue

            # Not a duplicate — keep it
            unique.append(article)
            self._seen_hashes.add(article.id)
            self._seen_hashes.add(article.fingerprint)

            mh = _minhash_from_title(article.title)
            self._lsh.insert(article.id, mh)
            self._minhashes[article.id] = mh

        logger.info("Dedup: %d -> %d articles", len(articles), len(unique))
        return unique
