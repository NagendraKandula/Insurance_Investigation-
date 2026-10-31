
from pprint import pprint

from detection.db_loader import DatabaseLoader
from detection.graph_builder import GraphBuilder
from detection.edge_gap_detector import EdgeGapDetector
from detection.shared_provider_detector import SharedProviderDetector
from detection.duplicate_invoice_detector import DuplicateInvoiceDetector
from detection.payment_anomaly_detector import PaymentAnomalyDetector
from detection.fraud_scorer import FraudScorer


def main():

    print("\n========== FRAUD SCORER INTEGRATION TEST ==========\n")

    # --------------------------------------------------
    # 1. Load database data
    # --------------------------------------------------

    print("[1] Loading database data...")

    loader = DatabaseLoader()
    data = loader.load_all_data()

    print("Database data loaded successfully.")

    # --------------------------------------------------
    # 2. Build graph
    # --------------------------------------------------

    print("\n[2] Building relationship graph...")

    builder = GraphBuilder()
    graph = builder.build(data)

    print(f"Graph nodes: {graph.number_of_nodes()}")
    print(f"Graph edges: {graph.number_of_edges()}")

    # --------------------------------------------------
    # 3. Run Edge Gap Detector
    # --------------------------------------------------

    print("\n[3] Running Edge Gap Detector...")

    edge_detector = EdgeGapDetector(graph)

    edge_findings = edge_detector.detect_missing_phone_edges(
        data["claimants"]
    )

    print(f"Edge gap findings: {len(edge_findings)}")

    # --------------------------------------------------
    # 4. Run Shared Provider Detector
    # --------------------------------------------------

    print("\n[4] Running Shared Provider Detector...")

    provider_detector = SharedProviderDetector(graph)

    provider_findings = provider_detector.detect()

    print(f"Shared provider findings: {len(provider_findings)}")

    # --------------------------------------------------
    # 5. Run Duplicate Invoice Detector
    # --------------------------------------------------

    print("\n[5] Running Duplicate Invoice Detector...")

    duplicate_detector = DuplicateInvoiceDetector(graph)

    duplicate_findings = duplicate_detector.detect()

    print(f"Duplicate invoice findings: {len(duplicate_findings)}")

    # --------------------------------------------------
    # 6. Run Payment Anomaly Detector
    # --------------------------------------------------

    print("\n[6] Running Payment Anomaly Detector...")

    payment_detector = PaymentAnomalyDetector(graph)

    payment_findings = payment_detector.detect()

    print(f"Payment anomaly findings: {len(payment_findings)}")

    # --------------------------------------------------
    # 7. Combine detector results
    # --------------------------------------------------

    print("\n[7] Combining detector results...")

    detector_results = {
        "edge_gaps": edge_findings,
        "shared_providers": provider_findings,
        "duplicate_invoices": duplicate_findings,
        "payment_anomalies": payment_findings
    }

    total_findings = sum(
        len(findings)
        for findings in detector_results.values()
    )

    print(f"Total detector findings: {total_findings}")

    # --------------------------------------------------
    # 8. Run Fraud Scorer
    # --------------------------------------------------

    print("\n[8] Calculating entity risk scores...")

    scorer = FraudScorer()

    risk_results = scorer.score(detector_results)

    print(f"Entities scored: {len(risk_results)}")

    # --------------------------------------------------
    # 9. Display risk-level summary
    # --------------------------------------------------

    print("\n========== RISK SUMMARY ==========")

    risk_summary = {
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0
    }

    for result in risk_results:
        risk_summary[result["risk_level"]] += 1

    for level, count in risk_summary.items():
        print(f"{level}: {count}")

    # --------------------------------------------------
    # 10. Display top 20 risky entities
    # --------------------------------------------------

    print("\n========== TOP 20 RISKY ENTITIES ==========")

    for index, result in enumerate(risk_results[:20], start=1):

        print(
            f"\n{index}. "
            f"{result['entity_type']} | "
            f"{result['entity_id']}"
        )

        print(f"   Risk Score: {result['risk_score']}")
        print(f"   Risk Level: {result['risk_level']}")
        print(f"   Signal Count: {result['signal_count']}")

        print("   Signals:")

        for signal in result["signals"]:
            print(
                f"      - {signal['indicator_type']} "
                f"(weight: {signal['weight']})"
            )

    # --------------------------------------------------
    # 11. Inspect one complete result
    # --------------------------------------------------

    if risk_results:

        print("\n========== TOP ENTITY EVIDENCE ==========")

        pprint(risk_results[0], sort_dicts=False)

    print("\n========== INTEGRATION TEST COMPLETED ==========\n")


if __name__ == "__main__":
    main()
