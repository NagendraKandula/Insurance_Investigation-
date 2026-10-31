from detection.db_loader import DatabaseLoader
from detection.graph_builder import GraphBuilder

loader = DatabaseLoader()
data = loader.load_all_data()

builder = GraphBuilder()
graph = builder.build(data)

assert graph.number_of_nodes() == 28500
assert graph.number_of_edges() == 38000

print("\nGraph construction completed successfully!")