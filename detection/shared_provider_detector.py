class SharedProviderDetector:

    def __init__(self, graph, minimum_claimants=3):
        self.graph = graph
        self.minimum_claimants = minimum_claimants

    def get_neighbors(self, node_id, direction, relationship_type):

        if direction == "out":
            edges = self.graph.out_edges(node_id, keys=True, data=True)
        else:
            edges = self.graph.in_edges(node_id, keys=True, data=True)

        neighbors = []

        for source, target, key, attrs in edges:

            if attrs.get("relationship_type") != relationship_type:
                continue

            neighbor = target if direction == "out" else source
            neighbors.append(neighbor)

        return neighbors

    def detect(self):

        print("Detecting shared provider clusters...")

        findings = []

        providers = [
            node_id
            for node_id, attrs in self.graph.nodes(data=True)
            if attrs.get("entity_type") == "provider"
        ]

        for provider_id in providers:

            claimant_claims = {}

            # Provider -> Invoice
            invoice_ids = self.get_neighbors(
                provider_id,
                "out",
                "ISSUED_INVOICE"
            )

            for invoice_id in invoice_ids:

                # Invoice <- Claim
                claim_ids = self.get_neighbors(
                    invoice_id,
                    "in",
                    "HAS_INVOICE"
                )

                for claim_id in claim_ids:

                    # Claim <- Claimant
                    claimant_ids = self.get_neighbors(
                        claim_id,
                        "in",
                        "FILED_CLAIM"
                    )

                    for claimant_id in claimant_ids:

                        claimant_claims.setdefault(
                            claimant_id, set()
                        ).add(claim_id)

            if len(claimant_claims) < self.minimum_claimants:
                continue

            findings.append({
                "entity_type": "provider",
                "entity_id": provider_id,
                "indicator_type": "SHARED_PROVIDER_CLUSTER",
                "evidence": {
                    "distinct_claimant_count": len(claimant_claims),
                    "claimant_ids": sorted(claimant_claims.keys()),
                    "claim_ids": sorted({
                        claim_id
                        for claim_ids in claimant_claims.values()
                        for claim_id in claim_ids
                    }),
                    "invoice_ids": sorted(set(invoice_ids))
                }
            })

        findings.sort(
            key=lambda item: item["evidence"]["distinct_claimant_count"],
            reverse=True
        )

        print(f"Shared provider clusters detected: {len(findings)}")

        return findings