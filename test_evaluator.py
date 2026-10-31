
from detection.db_loader import DatabaseLoader
from detection.graph_builder import GraphBuilder
from detection.edge_gap_detector import EdgeGapDetector
from detection.shared_provider_detector import SharedProviderDetector
from detection.duplicate_invoice_detector import DuplicateInvoiceDetector
from detection.payment_anomaly_detector import PaymentAnomalyDetector
from detection.fraud_scorer import FraudScorer
from detection.evaluator import Evaluator


def main():

    print("\n========== COMPLETE FRAUD EVALUATION ==========\n")

    # 1. Load data
    loader = DatabaseLoader()
    data = loader.load_all_data()

    # 2. Build graph
    graph = GraphBuilder().build(data)

    # 3. Run detectors
    edge_findings = EdgeGapDetector(graph).detect_missing_phone_edges(
        data["claimants"]
    )

    provider_findings = SharedProviderDetector(graph).detect()

    duplicate_findings = DuplicateInvoiceDetector(graph).detect()

    payment_findings = PaymentAnomalyDetector(graph).detect()

    # 4. Combine detector results
    detector_results = {
        "edge_gaps": edge_findings,
        "shared_providers": provider_findings,
        "duplicate_invoices": duplicate_findings,
        "payment_anomalies": payment_findings
    }

    # 5. Calculate risk scores WITHOUT ground truth
    scorer = FraudScorer()
    risk_results = scorer.score(detector_results)

    # 6. Evaluate using ground truth
    evaluator = Evaluator(threshold=40)

    report = evaluator.evaluate(
        risk_results=risk_results,
        ground_truth=data["ground_truth"]
    )

    print("\n========== EVALUATION COMPLETED ==========")


if __name__ == "__main__":
    main()
