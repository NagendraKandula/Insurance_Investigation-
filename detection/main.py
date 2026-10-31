"""
Run the whole detection pipeline end to end.

    python -m detection.main
    python -m detection.main --threshold 50 --top 20

Steps:
    1. Load the tables from the database
    2. Hold the answer key (ground truth) back, away from everything else
    3. Build the graph
    4. Run the four detectors
    5. Score entities
    6. Evaluate the scores against the answer key
    7. Write results to the output folder

The answer key is only handed to the evaluator, after scoring is finished.
"""

import argparse
import json
import time
from pathlib import Path

from detection.db_loader import DatabaseLoader
from detection.duplicate_invoice_detector import DuplicateInvoiceDetector
from detection.edge_gap_detector import EdgeGapDetector
from detection.evaluator import Evaluator
from detection.fraud_scorer import FraudScorer
from detection.graph_builder import GraphBuilder
from detection.payment_anomaly_detector import PaymentAnomalyDetector
from detection.shared_provider_detector import SharedProviderDetector


def _timed(label, function, *args, **kwargs):
    start = time.perf_counter()
    result = function(*args, **kwargs)
    print(f"  [{label}: {time.perf_counter() - start:.1f}s]")
    return result


def _write_json(path: Path, payload) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)


def run(threshold: int = 40, output_dir: Path = Path("output"), top: int = 10) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1-2. Load, then immediately set the answer key aside.
    data = _timed("load", DatabaseLoader().load_all_data)
    ground_truth = data.pop("ground_truth")

    # 3. Graph (built from data that no longer contains any labels).
    graph = _timed("graph", GraphBuilder().build, data)

    # 4. Detectors.
    detector_results = {
        "edge_gaps": _timed(
            "edge gaps",
            EdgeGapDetector(graph).detect_missing_phone_edges,
            data["claimants"],
        ),
        "shared_providers": _timed("shared providers", SharedProviderDetector(graph).detect),
        "duplicate_invoices": _timed("duplicate invoices", DuplicateInvoiceDetector(graph).detect),
        "payment_anomalies": _timed("payment anomalies", PaymentAnomalyDetector(graph).detect),
    }

    # 5. Scoring.
    risk_results = _timed("scoring", FraudScorer().score, detector_results)

    # 6. Evaluation: the first and only place the answer key is used.
    report = Evaluator(threshold=threshold).evaluate(risk_results, ground_truth)

    # 7. Outputs.
    _write_json(output_dir / "risk_scores.json", risk_results)
    _write_json(output_dir / "evaluation_report.json", report)
    _write_json(output_dir / "detector_counts.json",
                {name: len(items) for name, items in detector_results.items()})

    print("\n========== TOP RISK ENTITIES ==========")
    for result in risk_results[:top]:
        kinds = ", ".join(s["indicator_type"] for s in result["signals"])
        print(f"{result['risk_score']:>5}  {result['risk_level']:<6} "
              f"{result['entity_type']:<9} {result['entity_id']:<16} {kinds}")

    levels = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for result in risk_results:
        levels[result["risk_level"]] += 1

    print("\n========== RUN SUMMARY ==========")
    for name, items in detector_results.items():
        print(f"  {name:<20}{len(items):>8} findings")
    print(f"  entities scored     {len(risk_results):>8}")
    print(f"  risk levels         {levels}")
    print(f"\nResults written to: {output_dir.resolve()}")

    return {"detector_results": detector_results, "risk_results": risk_results, "report": report}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the fraud detection pipeline")
    parser.add_argument("--threshold", type=int, default=40,
                        help="Risk score at or above this counts as suspicious")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--top", type=int, default=10,
                        help="How many top-risk entities to print")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.threshold, args.output_dir, args.top)