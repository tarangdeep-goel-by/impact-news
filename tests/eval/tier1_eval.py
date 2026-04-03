"""Tier 1 evaluation — relevance classification + trigger identification.

Runs Tier 1 classifier on labeled articles and reports:
- Relevance: precision, recall, F1, confusion matrix
- Triggers: precision, recall (exact + ancestor match)
- Per-difficulty breakdown
- False positive/negative analysis

Usage:
    python -m tests.eval.tier1_eval                    # Run all cases
    python -m tests.eval.tier1_eval --limit 20         # First 20 cases
    python -m tests.eval.tier1_eval --difficulty hard   # Only hard cases
    python -m tests.eval.tier1_eval --dry-run           # Show cases without calling LLM
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections import Counter
from pathlib import Path

from config import settings
from engine.classifier import ArticleClassifier
from engine.taxonomy_context import TaxonomyContext
from pipeline.database import Database
from pipeline.events import EventStore
from pipeline.gemini import GeminiClient

logger = logging.getLogger(__name__)

CASES_PATH = Path(__file__).parent / "tier1_cases.json"


def load_cases(
    path: Path = CASES_PATH,
    difficulty: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    with open(path) as f:
        cases = json.load(f)
    if difficulty:
        cases = [c for c in cases if c.get("difficulty") == difficulty]
    if limit:
        cases = cases[:limit]
    return cases


def run_eval(
    cases: list[dict],
    classifier: ArticleClassifier,
    taxonomy: TaxonomyContext,
) -> dict:
    """Run Tier 1 on all cases and collect results."""
    results = []

    for i, case in enumerate(cases):
        title = case["title"]
        summary = case.get("summary", "")

        print(f"[{i+1}/{len(cases)}] {title[:70]}...", end=" ", flush=True)

        t0 = time.time()
        output = classifier.classify(title, summary)
        elapsed_ms = int((time.time() - t0) * 1000)

        if output is None:
            print(f"ERROR ({elapsed_ms}ms)")
            results.append({**case, "pred_relevant": None, "pred_triggers": [], "error": True, "ms": elapsed_ms})
            continue

        pred_relevant = output["relevant"]
        pred_triggers = [t["t_node"] for t in output.get("triggers", [])]

        expected = "REL" if case["relevant"] else "IRR"
        predicted = "REL" if pred_relevant else "IRR"
        match = "OK" if expected == predicted else "MISS"

        trigger_str = ", ".join(pred_triggers[:3]) if pred_triggers else "-"
        print(f"{match} ({elapsed_ms}ms) [{predicted}] T:[{trigger_str}]")

        if match == "MISS":
            if pred_relevant and not case["relevant"]:
                print(f"  FP: predicted relevant but expected irrelevant — reason: {case.get('reason', '?')}")
            else:
                print(f"  FN: predicted irrelevant but expected relevant — triggers: {case.get('triggers', [])}")
                if output.get("reason"):
                    print(f"  Tier 1 reason: {output['reason']}")

        results.append({
            **case,
            "pred_relevant": pred_relevant,
            "pred_triggers": pred_triggers,
            "pred_reason": output.get("reason"),
            "pred_exclude_l1s": output.get("exclude_l1s", []),
            "error": False,
            "ms": elapsed_ms,
        })

    return results


def compute_metrics(results: list[dict], taxonomy: TaxonomyContext) -> dict:
    """Compute relevance and trigger metrics."""
    # Filter errors
    valid = [r for r in results if not r.get("error")]

    # --- Relevance metrics ---
    tp = sum(1 for r in valid if r["relevant"] and r["pred_relevant"])
    fp = sum(1 for r in valid if not r["relevant"] and r["pred_relevant"])
    fn = sum(1 for r in valid if r["relevant"] and not r["pred_relevant"])
    tn = sum(1 for r in valid if not r["relevant"] and not r["pred_relevant"])

    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    # --- Trigger metrics (for correctly classified relevant articles) ---
    trigger_hits = 0
    trigger_expected = 0
    trigger_predicted = 0
    trigger_ancestor_hits = 0

    for r in valid:
        if not r["relevant"] or not r["pred_relevant"]:
            continue

        expected = set(r.get("triggers", []))
        predicted = set(r.get("pred_triggers", []))
        trigger_expected += len(expected)
        trigger_predicted += len(predicted)

        # Exact match
        exact = expected & predicted
        trigger_hits += len(exact)

        # Ancestor match: predicted trigger is ancestor or descendant of expected
        for exp_t in expected - exact:
            for pred_t in predicted - exact:
                if taxonomy.is_ancestor_of(pred_t, exp_t) or taxonomy.is_ancestor_of(exp_t, pred_t):
                    trigger_ancestor_hits += 1
                    break

    trigger_precision = trigger_hits / trigger_predicted if trigger_predicted else 0
    trigger_recall = trigger_hits / trigger_expected if trigger_expected else 0
    trigger_recall_with_ancestors = (trigger_hits + trigger_ancestor_hits) / trigger_expected if trigger_expected else 0

    return {
        "total": len(valid),
        "errors": len(results) - len(valid),
        "relevance": {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "triggers": {
            "exact_precision": trigger_precision,
            "exact_recall": trigger_recall,
            "ancestor_recall": trigger_recall_with_ancestors,
            "total_expected": trigger_expected,
            "total_predicted": trigger_predicted,
            "exact_hits": trigger_hits,
            "ancestor_hits": trigger_ancestor_hits,
        },
    }


def print_report(results: list[dict], metrics: dict) -> None:
    """Print evaluation report."""
    rel = metrics["relevance"]
    trg = metrics["triggers"]

    print(f"\n{'='*60}")
    print(f"TIER 1 EVALUATION — {metrics['total']} cases ({metrics['errors']} errors)")
    print(f"{'='*60}")

    print(f"\n--- Relevance ---")
    print(f"  Precision: {rel['precision']:.1%}  (of predicted relevant, how many actually are)")
    print(f"  Recall:    {rel['recall']:.1%}  (of actually relevant, how many we catch)")
    print(f"  F1:        {rel['f1']:.1%}")
    print(f"  Confusion: TP={rel['tp']} FP={rel['fp']} FN={rel['fn']} TN={rel['tn']}")

    print(f"\n--- Triggers (on true positive articles) ---")
    print(f"  Exact precision: {trg['exact_precision']:.1%}  ({trg['exact_hits']}/{trg['total_predicted']})")
    print(f"  Exact recall:    {trg['exact_recall']:.1%}  ({trg['exact_hits']}/{trg['total_expected']})")
    print(f"  Ancestor recall: {trg['ancestor_recall']:.1%}  ({trg['exact_hits']+trg['ancestor_hits']}/{trg['total_expected']})")

    # Per-difficulty breakdown
    valid = [r for r in results if not r.get("error")]
    by_diff = {}
    for r in valid:
        d = r.get("difficulty", "?")
        by_diff.setdefault(d, []).append(r)

    print(f"\n--- By Difficulty ---")
    for d in ["easy", "medium", "hard"]:
        group = by_diff.get(d, [])
        if not group:
            continue
        correct = sum(1 for r in group if r["relevant"] == r["pred_relevant"])
        print(f"  {d:>6}: {correct}/{len(group)} correct ({correct/len(group)*100:.0f}%)")

    # False negatives (missed relevant articles)
    fns = [r for r in valid if r["relevant"] and not r["pred_relevant"]]
    if fns:
        print(f"\n--- False Negatives ({len(fns)}) — relevant articles we missed ---")
        for r in fns[:10]:
            print(f"  [{r['source']}] {r['title'][:70]}")
            print(f"    Expected triggers: {r.get('triggers', [])}")
            print(f"    Tier 1 said: {r.get('pred_reason', '?')}")

    # False positives (irrelevant articles we let through)
    fps = [r for r in valid if not r["relevant"] and r["pred_relevant"]]
    if fps:
        print(f"\n--- False Positives ({len(fps)}) — irrelevant articles we let through ---")
        for r in fps[:10]:
            print(f"  [{r['source']}] {r['title'][:70]}")
            print(f"    Ground truth reason: {r.get('reason', '?')}")
            print(f"    Tier 1 triggers: {r.get('pred_triggers', [])}")

    # Latency
    times = [r["ms"] for r in valid]
    print(f"\n--- Latency ---")
    print(f"  Avg: {sum(times)/len(times):.0f}ms")
    print(f"  P50: {sorted(times)[len(times)//2]}ms")
    print(f"  P95: {sorted(times)[int(len(times)*0.95)]}ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tier 1 evaluation")
    parser.add_argument("--limit", type=int, default=None, help="Max cases to run")
    parser.add_argument("--difficulty", type=str, default=None, help="Filter by difficulty")
    parser.add_argument("--dry-run", action="store_true", help="Show cases without calling LLM")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    cases = load_cases(difficulty=args.difficulty, limit=args.limit)
    print(f"Loaded {len(cases)} eval cases")

    if args.dry_run:
        relevant = sum(1 for c in cases if c["relevant"])
        diff = Counter(c.get("difficulty", "?") for c in cases)
        print(f"Relevant: {relevant}, Irrelevant: {len(cases)-relevant}")
        print(f"Difficulty: {dict(diff)}")
        for c in cases[:10]:
            status = "REL" if c["relevant"] else "IRR"
            triggers = ", ".join(c.get("triggers", [])[:3])
            print(f"  [{status}] {c['title'][:60]}  T:[{triggers}]")
        return

    # Init
    print("Loading taxonomy...", end=" ", flush=True)
    taxonomy = TaxonomyContext.from_merged_graph(settings.graph_path)
    print("done.")

    db = Database(settings.db_path)
    db.init_schema()
    event_store = EventStore(db)
    gemini = GeminiClient()
    classifier = ArticleClassifier(gemini, event_store, taxonomy)

    print(f"Model: {settings.gemini_model}\n")

    # Run
    results = run_eval(cases, classifier, taxonomy)
    metrics = compute_metrics(results, taxonomy)
    print_report(results, metrics)

    # Save detailed results
    out_path = Path(__file__).parent / "tier1_results.json"
    with open(out_path, "w") as f:
        json.dump({"metrics": metrics, "results": results}, f, indent=2)
    print(f"\nDetailed results saved to {out_path}")

    db.close()


if __name__ == "__main__":
    main()
