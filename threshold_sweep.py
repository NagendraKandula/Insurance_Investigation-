
from detection.db_loader import DatabaseLoader
from detection.graph_builder import GraphBuilder
from detection.edge_gap_detector import EdgeGapDetector
from detection.shared_provider_detector import SharedProviderDetector
from detection.duplicate_invoice_detector import DuplicateInvoiceDetector
from detection.payment_anomaly_detector import PaymentAnomalyDetector
from detection.fraud_scorer import FraudScorer

loader = DatabaseLoader()
data = loader.load_all_data()

ground_truth = data["ground_truth"]

# Never expose ground truth to detection components.
detection_data = {
    key: value for key, value in data.items()
    if key != "ground_truth"
}

graph = GraphBuilder().build(detection_data)

detector_results = {
    "edge_gaps": EdgeGapDetector(graph).detect_missing_phone_edges(
        detection_data["claimants"]
    ),
    "shared_providers": SharedProviderDetector(graph).detect(),
    "duplicate_invoices": DuplicateInvoiceDetector(graph).detect(),
    "payment_anomalies": PaymentAnomalyDetector(graph).detect(),
}

risk_results = FraudScorer().score(detector_results)

predictions = {
    (item["entity_type"].lower(), str(item["entity_id"])):
        item["risk_score"]
    for item in risk_results
}

print("\n========== THRESHOLD COMPARISON ==========")

for threshold in [10, 20, 25, 30, 35, 40, 45, 50]:
    tp = fp = tn = fn = 0

    for row in ground_truth:
        key = (
            row["entity_type"].lower(),
            str(row["entity_id"])
        )

        score = predictions.get(key, 0)
        predicted = score >= threshold
        actual = row["expected_label"] == "SUSPICIOUS"

        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and not actual:
            tn += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )

    print(
        f"Threshold: {threshold:2} | "
        f"TP: {tp:3} | FP: {fp:3} | "
        f"TN: {tn:3} | FN: {fn:3} | "
        f"Precision: {precision:.4f} | "
        f"Recall: {recall:.4f} | F1: {f1:.4f}"
    )
