from detection.db_loader import DatabaseLoader
from detection.graph_builder import GraphBuilder
from detection.edge_gap_detector import EdgeGapDetector

# Load database
loader = DatabaseLoader()
data = loader.load_all_data()

# Build graph
builder = GraphBuilder()
graph = builder.build(data)

# Run detector
detector = EdgeGapDetector(graph)

findings = detector.detect_missing_phone_edges(
    data["claimants"]
)

print("\n========== DETECTION RESULTS ==========")

for finding in findings[:10]:
    print(finding)

print(f"\nTotal findings: {len(findings)}")