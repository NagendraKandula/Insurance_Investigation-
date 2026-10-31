
from datetime import datetime, timezone
from collections import Counter


class RelationshipEdgeGenerator:

    def __init__(self):
        self.created_at = datetime.now(timezone.utc)

    def create_edge(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relationship_type: str,
    ) -> dict:

        if not source_id or not target_id:
            raise ValueError("Source and target IDs are required.")

        return {
            "source_type": source_type,
            "source_id": source_id,
            "target_type": target_type,
            "target_id": target_id,
            "relationship_type": relationship_type,
            "confidence": 1.0,
            "source": "GENERATED_FOREIGN_KEY",
            "valid_from": None,
            "valid_to": None,
            "created_at": self.created_at,
        }

    def build_lookup(self, records, id_field, entity_name):

        lookup = {}

        for record in records:
            entity_id = record[id_field]

            if entity_id in lookup:
                raise ValueError(
                    f"Duplicate {entity_name} ID: {entity_id}"
                )

            lookup[entity_id] = record

        return lookup

    def generate_edges(
        self,
        claimants: list[dict],
        policies: list[dict],
        incidents: list[dict],
        claims: list[dict],
        providers: list[dict],
        invoices: list[dict],
        payments: list[dict],
    ) -> list[dict]:

        edges = []

        # Build lookups and validate unique entity IDs.
        claimant_lookup = self.build_lookup(
            claimants, "claimant_id", "claimant"
        )

        policy_lookup = self.build_lookup(
            policies, "policy_id", "policy"
        )

        incident_lookup = self.build_lookup(
            incidents, "incident_id", "incident"
        )

        claim_lookup = self.build_lookup(
            claims, "claim_id", "claim"
        )

        provider_lookup = self.build_lookup(
            providers, "provider_id", "provider"
        )

        invoice_lookup = self.build_lookup(
            invoices, "invoice_id", "invoice"
        )

        self.build_lookup(
            payments, "payment_id", "payment"
        )

        # 1. Claimant -> Policy
        for policy in policies:

            claimant_id = policy["claimant_id"]

            if claimant_id not in claimant_lookup:
                raise ValueError(
                    f"Invalid claimant reference in policy "
                    f"{policy['policy_id']}"
                )

            edges.append(
                self.create_edge(
                    "CLAIMANT",
                    claimant_id,
                    "POLICY",
                    policy["policy_id"],
                    "OWNS_POLICY",
                )
            )

        # 2. Claimant -> Claim
        # 3. Policy -> Claim
        # 4. Incident -> Claim
        for claim in claims:

            claimant_id = claim["claimant_id"]
            policy_id = claim["policy_id"]
            incident_id = claim["incident_id"]

            if claimant_id not in claimant_lookup:
                raise ValueError(
                    f"Invalid claimant in claim {claim['claim_id']}"
                )

            if policy_id not in policy_lookup:
                raise ValueError(
                    f"Invalid policy in claim {claim['claim_id']}"
                )

            if incident_id not in incident_lookup:
                raise ValueError(
                    f"Invalid incident in claim {claim['claim_id']}"
                )

            policy = policy_lookup[policy_id]

            if policy["claimant_id"] != claimant_id:
                raise ValueError(
                    f"Claimant-policy mismatch in {claim['claim_id']}"
                )

            edges.append(
                self.create_edge(
                    "CLAIMANT",
                    claimant_id,
                    "CLAIM",
                    claim["claim_id"],
                    "FILED_CLAIM",
                )
            )

            edges.append(
                self.create_edge(
                    "POLICY",
                    policy_id,
                    "CLAIM",
                    claim["claim_id"],
                    "COVERS_CLAIM",
                )
            )

            edges.append(
                self.create_edge(
                    "INCIDENT",
                    incident_id,
                    "CLAIM",
                    claim["claim_id"],
                    "REPORTED_IN_CLAIM",
                )
            )

        # 5. Provider -> Invoice
        # 6. Claim -> Invoice
        for invoice in invoices:

            provider_id = invoice["provider_id"]
            claim_id = invoice["claim_id"]

            if provider_id not in provider_lookup:
                raise ValueError(
                    f"Invalid provider in invoice "
                    f"{invoice['invoice_id']}"
                )

            if claim_id not in claim_lookup:
                raise ValueError(
                    f"Invalid claim in invoice "
                    f"{invoice['invoice_id']}"
                )

            edges.append(
                self.create_edge(
                    "PROVIDER",
                    provider_id,
                    "INVOICE",
                    invoice["invoice_id"],
                    "ISSUED_INVOICE",
                )
            )

            edges.append(
                self.create_edge(
                    "CLAIM",
                    claim_id,
                    "INVOICE",
                    invoice["invoice_id"],
                    "HAS_INVOICE",
                )
            )

        # 7. Invoice -> Payment
        for payment in payments:

            invoice_id = payment["invoice_id"]

            if invoice_id not in invoice_lookup:
                raise ValueError(
                    f"Invalid invoice in payment "
                    f"{payment['payment_id']}"
                )

            edges.append(
                self.create_edge(
                    "INVOICE",
                    invoice_id,
                    "PAYMENT",
                    payment["payment_id"],
                    "HAS_PAYMENT",
                )
            )

        return edges


# --------------------------------------------------
# Independent integration test
# --------------------------------------------------

if __name__ == "__main__":

    from generator.id_generator import IDGenerator
    from generator.claimant_generator import ClaimantGenerator
    from generator.provider_generator import ProviderGenerator
    from generator.policy_generator import PolicyGenerator
    from generator.incident_generator import IncidentGenerator
    from generator.claim_generator import ClaimGenerator
    from generator.invoice_generator import InvoiceGenerator
    from generator.payment_generator import PaymentGenerator
    from generator.pattern_injector import PatternInjector

    id_generator = IDGenerator()

    print("Generating test dataset...")

    claimants = ClaimantGenerator(
        id_generator
    ).generate_claimants(600)

    providers = ProviderGenerator(
        id_generator
    ).generate_providers(250)

    policies = PolicyGenerator(
        id_generator
    ).generate_policies(claimants, 900)

    incidents = IncidentGenerator(
        id_generator
    ).generate_incidents(1200)

    claims = ClaimGenerator(
        id_generator
    ).generate_claims(
        claimants,
        policies,
        incidents,
        900,
    )

    invoices = InvoiceGenerator(
        id_generator
    ).generate_invoices(
        claims,
        providers,
        250,
    )

    payments = PaymentGenerator(
        id_generator
    ).generate_payments(
        invoices,
        400,
    )

    print("Base dataset generated.")

    # Important: Inject patterns BEFORE generating edges.
    injector = PatternInjector(id_generator)

    ground_truth = injector.inject_all_patterns(
        claimants=claimants,
        claims=claims,
        providers=providers,
        invoices=invoices,
    )

    print(f"Ground-truth records: {len(ground_truth)}")

    # Generate edges from the final modified records.
    edge_generator = RelationshipEdgeGenerator()

    edges = edge_generator.generate_edges(
        claimants=claimants,
        policies=policies,
        incidents=incidents,
        claims=claims,
        providers=providers,
        invoices=invoices,
        payments=payments,
    )

    expected_edges = (
        len(policies)
        + (3 * len(claims))
        + (2 * len(invoices))
        + len(payments)
    )

    print("\n========== RELATIONSHIP SUMMARY ==========")

    print(f"Expected edges: {expected_edges}")
    print(f"Generated edges: {len(edges)}")

    assert len(edges) == expected_edges, (
        "Relationship edge count mismatch."
    )

    relationship_counts = Counter(
        edge["relationship_type"]
        for edge in edges
    )

    print("\nRelationship type counts:")

    for relationship_type, count in sorted(
        relationship_counts.items()
    ):
        print(f"{relationship_type}: {count}")

    # Validate that all modified invoice-provider
    # relationships are reflected in generated edges.
    provider_invoice_edges = {
        (edge["source_id"], edge["target_id"])
        for edge in edges
        if edge["relationship_type"] == "ISSUED_INVOICE"
    }

    for invoice in invoices:
        assert (
            invoice["provider_id"],
            invoice["invoice_id"],
        ) in provider_invoice_edges

    print("\nAll invoice-provider relationships validated.")
    print("Relationship generation completed successfully.")
