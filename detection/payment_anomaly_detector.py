
class PaymentAnomalyDetector:
    def __init__(self, graph):
        self.graph = graph
        self.findings = []

    def _get_node_data(self, node_id):
        if node_id not in self.graph:
            return None
        return self.graph.nodes[node_id].get("data", {})

    def _get_related_nodes(self, node_id, relationship_type, direction="out"):
        results = []

        if direction == "out":
            edges = self.graph.out_edges(node_id, keys=True, data=True)
            for source, target, _, edge_data in edges:
                if edge_data.get("relationship_type") == relationship_type:
                    results.append(target)

        else:
            edges = self.graph.in_edges(node_id, keys=True, data=True)
            for source, target, _, edge_data in edges:
                if edge_data.get("relationship_type") == relationship_type:
                    results.append(source)

        return results

    def _net_payment(self, invoice_id):
        payment_ids = self._get_related_nodes(
            invoice_id, "HAS_PAYMENT", "out"
        )

        net_amount = 0
        payment_details = []

        for payment_id in payment_ids:
            payment = self._get_node_data(payment_id)

            if not payment or payment.get("status") != "COMPLETED":
                continue

            amount = float(payment.get("payment_amount") or 0)
            transaction_type = payment.get("transaction_type")

            if transaction_type == "PAYMENT":
                net_amount += amount
            elif transaction_type in ("REFUND", "REVERSAL"):
                net_amount -= amount

            payment_details.append({
                "payment_id": payment_id,
                "amount": amount,
                "transaction_type": transaction_type,
                "status": payment.get("status")
            })

        return net_amount, payment_details

    def detect(self):
        self.findings = []

        # Check invoices and calculate their net payments.
        invoice_financials = {}

        for invoice_id, node_data in self.graph.nodes(data=True):
            if node_data.get("entity_type") != "invoice":
                continue

            invoice = node_data.get("data", {})
            net_amount, payment_details = self._net_payment(invoice_id)

            invoice_financials[invoice_id] = {
                "invoice": invoice,
                "net_amount": net_amount,
                "payment_details": payment_details
            }

            # Rule 1: Money paid against a rejected invoice.
            if invoice.get("status") == "REJECTED" and net_amount > 0:
                self.findings.append({
                    "entity_type": "invoice",
                    "entity_id": invoice_id,
                    "indicator_type": "PAYMENT_ON_REJECTED_INVOICE",
                    "evidence": {
                        "invoice_number": invoice.get("invoice_number"),
                        "invoice_status": invoice.get("status"),
                        "invoice_amount": float(invoice.get("invoice_amount") or 0),
                        "net_paid_amount": round(net_amount, 2),
                        "payments": payment_details
                    }
                })

            # Rule 2: Invoice marked PAID but not fully paid.
            invoice_amount = float(invoice.get("invoice_amount") or 0)

            if (
                invoice.get("status") == "PAID"
                and net_amount < invoice_amount - 0.01
            ):
                self.findings.append({
                    "entity_type": "invoice",
                    "entity_id": invoice_id,
                    "indicator_type": "PAID_INVOICE_UNDERPAYMENT",
                    "evidence": {
                        "invoice_number": invoice.get("invoice_number"),
                        "invoice_amount": invoice_amount,
                        "net_paid_amount": round(net_amount, 2),
                        "shortfall": round(invoice_amount - net_amount, 2),
                        "payments": payment_details
                    }
                })

        # Group invoices by claim.
        claim_invoices = {}

        for invoice_id, financials in invoice_financials.items():
            invoice = financials["invoice"]
            claim_id = invoice.get("claim_id")

            if not claim_id:
                continue

            claim_invoices.setdefault(claim_id, []).append(
                (invoice_id, financials)
            )

        # Rule 3 and Rule 4: Claim-level financial anomalies.
        for claim_id, invoices in claim_invoices.items():
            claim_node = self._get_node_data(claim_id)

            if not claim_node:
                continue

            claim_amount = float(claim_node.get("claim_amount") or 0)
            approved_amount = float(claim_node.get("approved_amount") or 0)

            total_invoice_amount = sum(
                float(item["invoice"].get("invoice_amount") or 0)
                for _, item in invoices
            )

            total_net_paid = sum(
                item["net_amount"] for _, item in invoices
            )

            invoice_details = [
                {
                    "invoice_id": invoice_id,
                    "invoice_number": item["invoice"].get("invoice_number"),
                    "invoice_amount": float(
                        item["invoice"].get("invoice_amount") or 0
                    ),
                    "net_paid_amount": round(item["net_amount"], 2)
                }
                for invoice_id, item in invoices
            ]

            # Rule 3: Total invoices exceed the claim amount.
            if total_invoice_amount > claim_amount + 0.01:
                self.findings.append({
                    "entity_type": "claim",
                    "entity_id": claim_id,
                    "indicator_type": "INVOICES_EXCEED_CLAIM_AMOUNT",
                    "evidence": {
                        "claim_amount": claim_amount,
                        "total_invoice_amount": round(total_invoice_amount, 2),
                        "excess_amount": round(
                            total_invoice_amount - claim_amount, 2
                        ),
                        "invoices": invoice_details
                    }
                })

            # Rule 4: Net payments exceed the approved claim amount.
            if total_net_paid > approved_amount + 0.01:
                self.findings.append({
                    "entity_type": "claim",
                    "entity_id": claim_id,
                    "indicator_type": "PAYMENTS_EXCEED_APPROVED_AMOUNT",
                    "evidence": {
                        "approved_amount": approved_amount,
                        "total_net_paid": round(total_net_paid, 2),
                        "excess_amount": round(
                            total_net_paid - approved_amount, 2
                        ),
                        "invoices": invoice_details
                    }
                })

        print(f"Payment anomaly detection complete: {len(self.findings)} findings")

        return self.findings
