from collections import defaultdict


class DuplicateInvoiceDetector:

    def __init__(self, graph):
        self.graph = graph

    def detect(self):

        print("Detecting duplicate invoice numbers...")

        invoice_groups = defaultdict(list)

        # Group invoices by invoice_number
        for node_id, attrs in self.graph.nodes(data=True):

            if attrs.get("entity_type") != "invoice":
                continue

            invoice_data = attrs["data"]

            invoice_number = invoice_data.get("invoice_number")

            if invoice_number:
                invoice_groups[invoice_number].append(invoice_data)

        findings = []

        for invoice_number, invoices in invoice_groups.items():

            if len(invoices) < 2:
                continue

            invoice_evidence = []

            for invoice in invoices:

                invoice_id = str(invoice["invoice_id"])

                # Invoice <- Claim
                claim_ids = [
                    source
                    for source, _, _, edge_data in
                    self.graph.in_edges(
                        invoice_id,
                        keys=True,
                        data=True
                    )
                    if edge_data.get("relationship_type") == "HAS_INVOICE"
                ]

                for claim_id in claim_ids:

                    claim_data = self.graph.nodes[claim_id]["data"]

                    invoice_evidence.append({
                        "invoice_id": invoice_id,
                        "provider_id": str(invoice["provider_id"]),
                        "claim_id": claim_id,
                        "claimant_id": str(claim_data["claimant_id"]),
                        "invoice_amount": float(invoice["invoice_amount"])
                    })

            # Only flag when different claimants are involved
            claimant_ids = {
                item["claimant_id"]
                for item in invoice_evidence
            }

            if len(claimant_ids) < 2:
                continue

            findings.append({
                "entity_type": "invoice",
                "entity_id": invoice_number,
                "indicator_type": "DUPLICATE_INVOICE_NUMBER",
                "evidence": {
                    "invoice_number": invoice_number,
                    "invoice_count": len(invoices),
                    "distinct_claimant_count": len(claimant_ids),
                    "claimant_ids": sorted(claimant_ids),
                    "invoices": invoice_evidence
                }
            })

        findings.sort(
            key=lambda item: item["evidence"]["distinct_claimant_count"],
            reverse=True
        )

        print(f"Duplicate invoice numbers detected: {len(findings)}")

        return findings