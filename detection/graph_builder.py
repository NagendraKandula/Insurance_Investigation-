import networkx as nx


class GraphBuilder:

    ENTITY_TABLES = {
        "claimants": ("claimant", "claimant_id"),
        "policies": ("policy", "policy_id"),
        "incidents": ("incident", "incident_id"),
        "claims": ("claim", "claim_id"),
        "providers": ("provider", "provider_id"),
        "invoices": ("invoice", "invoice_id"),
        "payments": ("payment", "payment_id"),
    }

    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def normalize_type(self, entity_type):
        return str(entity_type).strip().lower()

    def build_nodes(self, data):

        print("Building graph nodes...")

        for table_name, (entity_type, id_field) in self.ENTITY_TABLES.items():

            records = data.get(table_name, [])

            for record in records:
                entity_id = str(record[id_field])

                self.graph.add_node(
                    entity_id,
                    entity_type=entity_type,
                    data=dict(record)
                )

            print(f"Added {len(records)} {entity_type} nodes")

    def build_edges(self, data):

        print("Building graph edges...")

        for edge in data.get("relationship_edges", []):

            source_id = str(edge["source_id"])
            target_id = str(edge["target_id"])

            source_type = self.normalize_type(edge["source_type"])
            target_type = self.normalize_type(edge["target_type"])

            if source_id not in self.graph:
                raise ValueError(
                    f"Missing source node: {source_type}:{source_id}"
                )

            if target_id not in self.graph:
                raise ValueError(
                    f"Missing target node: {target_type}:{target_id}"
                )

            if self.graph.nodes[source_id]["entity_type"] != source_type:
                raise ValueError(
                    f"Source type mismatch for {source_id}"
                )

            if self.graph.nodes[target_id]["entity_type"] != target_type:
                raise ValueError(
                    f"Target type mismatch for {target_id}"
                )

            self.graph.add_edge(
                source_id,
                target_id,
                key=edge["edge_id"],
                relationship_type=edge["relationship_type"],
                confidence=edge["confidence"],
                source=edge["source"],
                valid_from=edge["valid_from"],
                valid_to=edge["valid_to"],
            )

        print(
            f"Added {self.graph.number_of_edges()} relationship edges"
        )

    def build(self, data):

        self.graph.clear()

        self.build_nodes(data)
        self.build_edges(data)

        print("\n========== GRAPH SUMMARY ==========")
        print(f"Total nodes: {self.graph.number_of_nodes()}")
        print(f"Total edges: {self.graph.number_of_edges()}")

        print("\nNodes by entity type:")

        for entity_type in self.ENTITY_TABLES.values():
            name = entity_type[0]

            count = sum(
                1
                for _, attrs in self.graph.nodes(data=True)
                if attrs["entity_type"] == name
            )

            print(f"{name:15} {count:>8}")

        return self.graph