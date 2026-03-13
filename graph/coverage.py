"""Coverage tracker for the impact graph.

Tracks unmatched article tags, aggregates coverage gaps, and reports
per-persona reachability.

CLI usage:
    python3 -m graph.coverage gaps          # top unmatched concepts
    python3 -m graph.coverage user-detail   # per-persona coverage
    python3 -m graph.coverage summary       # overall coverage health
    python3 -m graph.coverage clear         # reset gap log
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class GapEntry(BaseModel):
    tag: str
    count: int
    example_article: str
    best_score: float
    best_node: str


class GapReport(BaseModel):
    total_unmatched: int
    top_gaps: list[GapEntry]


class PersonaCoverage(BaseModel):
    name: str
    direct_nodes: int
    reachable_nodes: int
    reachable_pct: float
    top_unreachable: list[str]  # High-degree nodes not in reachable set


class UserCoverageDetail(BaseModel):
    personas: list[PersonaCoverage]
    avg_reachable_pct: float


class CoverageSummary(BaseModel):
    total_logged: int
    unique_tags: int
    top_gap_domains: list[str]


# ---------------------------------------------------------------------------
# CoverageTracker
# ---------------------------------------------------------------------------


class CoverageTracker:
    GAP_LOG = Path("data/unmatched_tags.jsonl")

    def __init__(self, root: Path = Path.cwd()):
        self.root = root

    @property
    def _log_path(self) -> Path:
        return self.root / self.GAP_LOG

    # -- gap logging --------------------------------------------------------

    def log_unmatched(
        self,
        tag: str,
        article_title: str,
        best_score: float,
        best_node: str,
    ) -> None:
        """Append unmatched tag to JSONL log file. Called by article pipeline."""
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "tag": tag,
            "article": article_title,
            "best_score": best_score,
            "best_node": best_node,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _read_log(self) -> list[dict]:
        """Read all JSONL entries. Returns empty list if file missing."""
        if not self._log_path.exists():
            return []
        entries: list[dict] = []
        with open(self._log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    # -- aggregation --------------------------------------------------------

    def aggregate_gaps(self, top_n: int = 20) -> GapReport:
        """Read JSONL, aggregate by tag, return top gaps sorted by frequency."""
        entries = self._read_log()
        if not entries:
            return GapReport(total_unmatched=0, top_gaps=[])

        tag_counts: Counter[str] = Counter()
        tag_example: dict[str, str] = {}
        tag_best: dict[str, tuple[float, str]] = {}

        for e in entries:
            tag = e["tag"]
            tag_counts[tag] += 1
            # Keep first example article per tag
            if tag not in tag_example:
                tag_example[tag] = e["article"]
            # Keep highest best_score per tag
            score = e["best_score"]
            if tag not in tag_best or score > tag_best[tag][0]:
                tag_best[tag] = (score, e["best_node"])

        top_gaps: list[GapEntry] = []
        for tag, count in tag_counts.most_common(top_n):
            best_score, best_node = tag_best[tag]
            top_gaps.append(
                GapEntry(
                    tag=tag,
                    count=count,
                    example_article=tag_example[tag],
                    best_score=best_score,
                    best_node=best_node,
                )
            )

        return GapReport(total_unmatched=len(entries), top_gaps=top_gaps)

    def clear_gaps(self) -> None:
        """Reset gap log after addressing gaps."""
        if self._log_path.exists():
            self._log_path.unlink()

    # -- user coverage detail -----------------------------------------------

    def user_coverage_detail(self) -> UserCoverageDetail:
        """Detailed per-persona coverage using personas from quality.py."""
        from graph.graph import ImpactGraph
        from graph.merge import TaxonomyMerger
        from graph.migrate_weights import apply_defaults, apply_fan_out_penalty
        from graph.quality import PERSONAS
        from user.inference import connect_user_to_graph

        merger = TaxonomyMerger(root=self.root)
        G = merger.merge()
        apply_defaults(G)
        apply_fan_out_penalty(G)

        # Build ImpactGraph backed by the merged DiGraph
        ig = ImpactGraph.__new__(ImpactGraph)
        ig.g = G

        total_nodes = G.number_of_nodes()
        all_node_ids = set(G.nodes())

        # Pre-compute degree for unreachable ranking
        degree_map = {n: G.in_degree(n) + G.out_degree(n) for n in G.nodes()}

        results: list[PersonaCoverage] = []
        for name, answers in PERSONAS.items():
            ug = connect_user_to_graph(answers, ig, user_id=name)
            direct = len(ug.edges)
            reachable = len(ug.reachable_nodes)
            pct = round(reachable / total_nodes * 100, 2) if total_nodes else 0.0

            # Top unreachable high-degree nodes
            unreachable = all_node_ids - ug.reachable_nodes
            top_unreachable = sorted(unreachable, key=lambda n: degree_map[n], reverse=True)[:10]

            results.append(
                PersonaCoverage(
                    name=name,
                    direct_nodes=direct,
                    reachable_nodes=reachable,
                    reachable_pct=pct,
                    top_unreachable=top_unreachable,
                )
            )

        avg = round(sum(p.reachable_pct for p in results) / len(results), 2) if results else 0.0
        return UserCoverageDetail(personas=results, avg_reachable_pct=avg)

    # -- summary ------------------------------------------------------------

    def summary(self) -> CoverageSummary:
        """Overall coverage health."""
        entries = self._read_log()
        total = len(entries)
        tag_counts: Counter[str] = Counter()
        for e in entries:
            tag_counts[e["tag"]] += 1

        unique = len(tag_counts)

        # Top gap domains: extract domain-like groupings from tag names
        # Use first word / underscore-prefix as a rough domain bucket
        domain_counts: Counter[str] = Counter()
        for tag, count in tag_counts.items():
            domain = tag.split("_")[0].split()[0].lower() if tag else "unknown"
            domain_counts[domain] += count

        top_domains = [
            f"{domain} ({count})"
            for domain, count in domain_counts.most_common(5)
        ]

        return CoverageSummary(
            total_logged=total,
            unique_tags=unique,
            top_gap_domains=top_domains,
        )


# ---------------------------------------------------------------------------
# CLI display helpers
# ---------------------------------------------------------------------------


def _print_gaps(tracker: CoverageTracker, args: argparse.Namespace) -> None:
    report = tracker.aggregate_gaps(top_n=getattr(args, "top_n", 20))
    if not report.top_gaps:
        print("No unmatched tags logged yet.")
        return

    print(f"Top unmatched concepts (from {report.total_unmatched} logged):")
    for i, gap in enumerate(report.top_gaps, 1):
        print(
            f"  {i:>3}. \"{gap.tag}\" "
            f"({gap.count} articles, best: {gap.best_node} @ {gap.best_score:.2f})"
        )


def _print_user_detail(tracker: CoverageTracker, _args: argparse.Namespace) -> None:
    detail = tracker.user_coverage_detail()

    header = f"{'Persona':<24} {'Direct':>7}  {'Reachable':>10}  {'Coverage':>8}"
    print(header)
    print("\u2500" * len(header))
    for p in detail.personas:
        print(
            f"{p.name:<24} {p.direct_nodes:>7}  "
            f"{p.reachable_nodes:>10}  {p.reachable_pct:>7.1f}%"
        )
    print(f"\nAverage coverage: {detail.avg_reachable_pct:.1f}%")


def _print_summary(tracker: CoverageTracker, _args: argparse.Namespace) -> None:
    s = tracker.summary()
    print(f"Total tags logged: {s.total_logged}")
    print(f"Unique unmatched tags: {s.unique_tags}")
    if s.top_gap_domains:
        print(f"Top gap domains: {', '.join(s.top_gap_domains)}")
    else:
        print("Top gap domains: (none)")


def _clear_gaps(tracker: CoverageTracker, _args: argparse.Namespace) -> None:
    tracker.clear_gaps()
    print("Gap log cleared.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python3 -m graph.coverage",
        description="Coverage tracker for the impact graph",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root")
    sub = parser.add_subparsers(dest="command", required=True)

    # gaps
    gaps_parser = sub.add_parser("gaps", help="Show top unmatched concepts")
    gaps_parser.add_argument("-n", "--top-n", type=int, default=20, help="Number of gaps to show")

    # user-detail
    sub.add_parser("user-detail", help="Per-persona coverage detail")

    # summary
    sub.add_parser("summary", help="Overall coverage health")

    # clear
    sub.add_parser("clear", help="Reset gap log")

    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    tracker = CoverageTracker(root=args.root)

    dispatch = {
        "gaps": _print_gaps,
        "user-detail": _print_user_detail,
        "summary": _print_summary,
        "clear": _clear_gaps,
    }
    dispatch[args.command](tracker, args)


if __name__ == "__main__":
    main()
