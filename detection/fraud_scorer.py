
class FraudScorer:

    WEIGHTS = {
        "DUPLICATE_INVOICE_ACROSS_CLAIMANTS": 30,
        "MISSING_PHONE_RELATIONSHIP": 15,
        "PAYMENT_ON_REJECTED_INVOICE": 25,
        "PAYMENTS_EXCEED_APPROVED_AMOUNT": 25,
        "INVOICES_EXCEED_CLAIM_AMOUNT": 15,
        "PAID_INVOICE_UNDERPAYMENT": 10,
        "SHARED_PROVIDER_CLUSTER": 10,
    }

    def __init__(self):
        self.entity_scores = {}

    # --------------------------------------------------
    # ADD SIGNAL TO ENTITY
    # --------------------------------------------------

    def _add_signal(self, entity_type, entity_id, indicator_type, evidence):

        if not entity_id:
            return

        key = (entity_type, str(entity_id))

        if key not in self.entity_scores:
            self.entity_scores[key] = {
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "risk_score": 0,
                "signals": [],
                "signal_types": set()
            }

        entity = self.entity_scores[key]

        # Avoid counting the same indicator type twice.
        if indicator_type in entity["signal_types"]:
            return

        weight = self.WEIGHTS.get(indicator_type, 0)

        entity["risk_score"] += weight
        entity["signal_types"].add(indicator_type)

        entity["signals"].append({
            "indicator_type": indicator_type,
            "weight": weight,
            "evidence": evidence
        })

    # --------------------------------------------------
    # 1. MISSING PHONE RELATIONSHIP SIGNALS
    # --------------------------------------------------

    def _process_edge_gaps(self, findings):

        for finding in findings:

            evidence = finding.get("evidence", {})

            claimant_ids = {
                finding.get("entity_id"),
                finding.get("related_entity_id")
            }

            for claimant_id in claimant_ids:

                if claimant_id:

                    self._add_signal(
                        "claimant",
                        claimant_id,
                        "MISSING_PHONE_RELATIONSHIP",
                        evidence
                    )

    # --------------------------------------------------
    # 2. SHARED PROVIDER SIGNALS
    # --------------------------------------------------

    def _process_shared_providers(self, findings):

        for finding in findings:

            evidence = finding.get("evidence", {})

            provider_id = finding.get("entity_id")

            claimant_ids = evidence.get("claimant_ids", [])
            claim_ids = evidence.get("claim_ids", [])
            invoice_ids = evidence.get("invoice_ids", [])

            shared_evidence = {
                "provider_id": provider_id,
                "distinct_claimant_count": evidence.get(
                    "distinct_claimant_count", len(claimant_ids)
                ),
                "claimant_ids": claimant_ids,
                "claim_ids": claim_ids,
                "invoice_ids": invoice_ids,
                "context": "Connected to a shared provider cluster"
            }

            # Provider signal.
            self._add_signal(
                "provider",
                provider_id,
                "SHARED_PROVIDER_CLUSTER",
                shared_evidence
            )

            # Connected claimant signals.
            for claimant_id in claimant_ids:

                self._add_signal(
                    "claimant",
                    claimant_id,
                    "SHARED_PROVIDER_CLUSTER",
                    shared_evidence
                )

            # Connected claim signals.
            for claim_id in claim_ids:

                self._add_signal(
                    "claim",
                    claim_id,
                    "SHARED_PROVIDER_CLUSTER",
                    shared_evidence
                )

            # Connected invoice signals.
            for invoice_id in invoice_ids:

                self._add_signal(
                    "invoice",
                    invoice_id,
                    "SHARED_PROVIDER_CLUSTER",
                    shared_evidence
                )

    # --------------------------------------------------
    # 3. DUPLICATE INVOICE SIGNALS
    # --------------------------------------------------

    def _process_duplicate_invoices(self, findings):

        for finding in findings:

            evidence = finding.get("evidence", {})

            for invoice in evidence.get("invoices", []):

                invoice_id = invoice.get("invoice_id")
                claimant_id = invoice.get("claimant_id")
                claim_id = invoice.get("claim_id")
                provider_id = invoice.get("provider_id")

                duplicate_evidence = {
                    "invoice_number": evidence.get("invoice_number"),
                    "invoice_count": evidence.get("invoice_count"),
                    "distinct_claimant_count": evidence.get(
                        "distinct_claimant_count"
                    ),
                    "claimant_ids": evidence.get("claimant_ids", []),
                    "invoice_details": invoice
                }

                # Invoice.
                self._add_signal(
                    "invoice",
                    invoice_id,
                    "DUPLICATE_INVOICE_ACROSS_CLAIMANTS",
                    duplicate_evidence
                )

                # Claimant.
                self._add_signal(
                    "claimant",
                    claimant_id,
                    "DUPLICATE_INVOICE_ACROSS_CLAIMANTS",
                    duplicate_evidence
                )

                # Claim.
                self._add_signal(
                    "claim",
                    claim_id,
                    "DUPLICATE_INVOICE_ACROSS_CLAIMANTS",
                    duplicate_evidence
                )

                # Associated provider.
                self._add_signal(
                    "provider",
                    provider_id,
                    "DUPLICATE_INVOICE_ACROSS_CLAIMANTS",
                    duplicate_evidence
                )

    # --------------------------------------------------
    # 4. PAYMENT ANOMALY SIGNALS
    # --------------------------------------------------

    def _process_payment_anomalies(self, findings):

        for finding in findings:

            self._add_signal(
                finding["entity_type"].lower(),
                finding["entity_id"],
                finding["indicator_type"],
                finding["evidence"]
            )

    # --------------------------------------------------
    # MAIN SCORING FUNCTION
    # --------------------------------------------------

    def score(self, detector_results):

        self.entity_scores = {}

        # 1. Missing phone relationships.
        self._process_edge_gaps(
            detector_results.get("edge_gaps", [])
        )

        # 2. Shared provider clusters.
        self._process_shared_providers(
            detector_results.get("shared_providers", [])
        )

        # 3. Duplicate invoice numbers.
        self._process_duplicate_invoices(
            detector_results.get("duplicate_invoices", [])
        )

        # 4. Payment anomalies.
        self._process_payment_anomalies(
            detector_results.get("payment_anomalies", [])
        )

        # --------------------------------------------------
        # CALCULATE FINAL RISK SCORES
        # --------------------------------------------------

        results = []

        for entity in self.entity_scores.values():

            raw_score = entity["risk_score"]
            signal_types = entity["signal_types"]

            # Shared-provider evidence alone is weak evidence.
            if signal_types == {"SHARED_PROVIDER_CLUSTER"}:
                raw_score = 10

            # Independent signal corroboration bonus.
            independent_signals = len(signal_types)

            if independent_signals >= 2:

                raw_score += min(
                    (independent_signals - 1) * 10,
                    20
                )

            final_score = min(raw_score, 100)

            if final_score >= 70:
                risk_level = "HIGH"

            elif final_score >= 40:
                risk_level = "MEDIUM"

            else:
                risk_level = "LOW"

            results.append({
                "entity_type": entity["entity_type"],
                "entity_id": entity["entity_id"],
                "risk_score": final_score,
                "risk_level": risk_level,
                "signal_count": len(entity["signals"]),
                "signals": entity["signals"]
            })

        # Highest-risk entities first.
        results.sort(
            key=lambda item: item["risk_score"],
            reverse=True
        )

        print(
            f"Fraud scoring complete: "
            f"{len(results)} entities scored"
        )

        return results
