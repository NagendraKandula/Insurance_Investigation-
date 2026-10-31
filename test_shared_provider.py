from detection.db_loader import DatabaseLoader
from detection.graph_builder import GraphBuilder
from detection.shared_provider_detector import SharedProviderDetector

# Load database
loader = DatabaseLoader()
data = loader.load_all_data()

# Build graph
builder = GraphBuilder()
graph = builder.build(data)

# Run detector
detector = SharedProviderDetector(
    graph,
    minimum_claimants=3
)

findings = detector.detect()

print("\n========== SHARED PROVIDER RESULTS ==========")

for finding in findings[:10]:

    print("\nProvider:", finding["entity_id"])

    evidence = finding["evidence"]

    print("Distinct claimants:", evidence["distinct_claimant_count"])
    print("Claimants:", evidence["claimant_ids"])
    print("Claims:", evidence["claim_ids"])
    print("Invoices:", evidence["invoice_ids"])

print("\nTotal provider clusters:", len(findings))