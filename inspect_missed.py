
from detection.db_loader import DatabaseLoader
from detection.graph_builder import GraphBuilder
from detection.edge_gap_detector import EdgeGapDetector
from detection.shared_provider_detector import SharedProviderDetector
from detection.duplicate_invoice_detector import DuplicateInvoiceDetector
from detection.payment_anomaly_detector import PaymentAnomalyDetector
from detection.fraud_scorer import FraudScorer
from detection.evaluator import Evaluator

loader = DatabaseLoader()
data = loader.load_all_data()

# Keep ground truth isolated from detection logic.
ground_truth = data["ground_truth"]
detection_data = {
    key: value for key, value in data.items()
    if key != "ground_truth"
}

graph = GraphBuilder().build(detection_data)

edge_findings = EdgeGapDetector(
    graph
).detect_missing_phone_edges(detection_data["claimants"])

provider_findings = SharedProviderDetector(graph).detect()
duplicate_findings = DuplicateInvoiceDetector(graph).detect()
payment_findings = PaymentAnomalyDetector(graph).detect()

detector_results = {
    "edge_gaps": edge_findings,
    "shared_providers": provider_findings,
    "duplicate_invoices": duplicate_findings,
    "payment_anomalies": payment_findings,
}

risk_results = FraudScorer().score(detector_results)

report = Evaluator(threshold=40).evaluate(
    risk_results=risk_results,
    ground_truth=ground_truth,
)

predictions = {
    (item["entity_type"].lower(), item["entity_id"]): item
    for item in risk_results
}

missed = []

for row in ground_truth:
    if row["expected_label"] != "SUSPICIOUS":
        continue

    key = (
        row["entity_type"].lower(),
        str(row["entity_id"])
    )

    prediction = predictions.get(key)
    score = prediction["risk_score"] if prediction else 0

    if score < 40:
        missed.append({
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "pattern": row["pattern_type"],
            "network": row["planted_network_id"],
            "score": score,
            "signals": prediction["signals"] if prediction else []
        })

print("\n========== MISSED SUSPICIOUS RECORDS ==========")

for item in missed[:30]:
    print(
        f'{item["entity_type"]} | {item["entity_id"]} | '
        f'{item["pattern"]} | {item["network"]} | '
        f'Score: {item["score"]} | Signals: {item["signals"]}'
    )

print(f"\nTotal missed records: {len(missed)}")
