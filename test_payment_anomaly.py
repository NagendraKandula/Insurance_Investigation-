from detection.db_loader import DatabaseLoader
from detection.graph_builder import GraphBuilder
from detection.payment_anomaly_detector import PaymentAnomalyDetector

data = DatabaseLoader().load_all_data()

graph_builder = GraphBuilder()
graph = graph_builder.build(data)

detector = PaymentAnomalyDetector(graph)
findings = detector.detect()

print("\nFinding counts by indicator:")

counts = {}

for finding in findings:
    indicator = finding["indicator_type"]
    counts[indicator] = counts.get(indicator, 0) + 1

for indicator, count in counts.items():
    print(f"{indicator}: {count}")

print("\nSample findings:")

for finding in findings[:5]:
    print(finding)