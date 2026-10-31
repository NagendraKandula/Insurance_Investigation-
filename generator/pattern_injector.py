import random
from datetime import datetime, timezone

from generator.config import PATTERN_CONFIG
from generator.id_generator import IDGenerator
from generator.normalizers import normalize_phone, normalize_address


class PatternInjector:

    def __init__(self, id_generator: IDGenerator, seed: int = 20261031):
        self.id_generator = id_generator
        self.random = random.Random(seed)

        # Prevent entities from appearing in multiple planted networks.
        self.used_claimant_ids = set()
        self.used_provider_ids = set()
        self.used_invoice_ids = set()

    # --------------------------------------------------
    # Common ground-truth record creation
    # --------------------------------------------------

    def create_ground_truth_record(
        self,
        network_id: str,
        entity_type: str,
        entity_id: str,
        pattern_type: str,
        role: str,
        issue_type: str,
        expected_label: str,
        description: str,
    ) -> dict:

        return {
            "planted_network_id": network_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "pattern_type": pattern_type,
            "role_in_network": role,
            "issue_type": issue_type,
            "expected_label": expected_label,
            "description": description,
            "generation_run_id": None,
            "created_at": datetime.now(timezone.utc),
        }

    # --------------------------------------------------
    # Generate a unique shared phone number
    # --------------------------------------------------

    def generate_unique_phone(self, claimants: list[dict]) -> str:

        existing_phones = {
            claimant.get("normalized_phone")
            for claimant in claimants
            if claimant.get("normalized_phone")
        }

        for _ in range(1000):
            phone = str(
                self.random.randint(6, 9)
            ) + "".join(
                str(self.random.randint(0, 9))
                for _ in range(9)
            )

            normalized = normalize_phone(phone)

            if normalized not in existing_phones:
                return phone

        raise ValueError("Could not generate a unique shared phone number.")

    # --------------------------------------------------
    # Find invoices belonging to different claimants
    # --------------------------------------------------

    def get_eligible_invoices(
        self,
        claims: list[dict],
        invoices: list[dict],
    ) -> list[dict]:

        claim_lookup = {
            claim["claim_id"]: claim
            for claim in claims
        }

        eligible_invoices = []
        seen_claimants = set()

        for invoice in invoices:

            invoice_id = invoice["invoice_id"]

            if invoice_id in self.used_invoice_ids:
                continue

            claim = claim_lookup.get(invoice["claim_id"])

            if claim is None:
                continue

            claimant_id = claim["claimant_id"]

            if claimant_id in self.used_claimant_ids:
                continue

            if claimant_id in seen_claimants:
                continue

            eligible_invoices.append(invoice)
            seen_claimants.add(claimant_id)

        return eligible_invoices

    # --------------------------------------------------
    # 1. Suspicious shared-provider networks
    # --------------------------------------------------

    def inject_suspicious_networks(
        self,
        claimants: list[dict],
        claims: list[dict],
        providers: list[dict],
        invoices: list[dict],
        network_count: int | None = None,
        members_per_network: int = 3,
    ) -> list[dict]:

        if network_count is None:
            network_count = self.random.randint(
                PATTERN_CONFIG["min_suspicious_networks"],
                PATTERN_CONFIG["max_suspicious_networks"],
            )

        if network_count < 1:
            raise ValueError("Network count must be at least one.")

        if members_per_network < 2:
            raise ValueError("A network needs at least two members.")

        available_providers = [
            provider
            for provider in providers
            if provider["provider_id"] not in self.used_provider_ids
        ]

        if len(available_providers) < network_count:
            raise ValueError(
                "Not enough unique providers for suspicious networks."
            )

        ground_truth_records = []

        for network_number in range(network_count):

            eligible_invoices = self.get_eligible_invoices(
                claims,
                invoices,
            )

            if len(eligible_invoices) < members_per_network:
                raise ValueError(
                    "Not enough unused invoices belonging to "
                    "different claimants. Increase the test dataset."
                )

            selected_invoices = self.random.sample(
                eligible_invoices,
                members_per_network,
            )

            selected_provider = self.random.choice(
                available_providers
            )

            available_providers.remove(selected_provider)

            network_id = self.id_generator.generate("network")

            shared_phone = self.generate_unique_phone(claimants)
            normalized_phone = normalize_phone(shared_phone)

            claim_lookup = {
                claim["claim_id"]: claim
                for claim in claims
            }

            # Record the shared provider.
            ground_truth_records.append(
                self.create_ground_truth_record(
                    network_id=network_id,
                    entity_type="PROVIDER",
                    entity_id=selected_provider["provider_id"],
                    pattern_type="SHARED_PROVIDER_CLUSTER",
                    role="SHARED_PROVIDER",
                    issue_type="SHARED_CONTACT_AND_PROVIDER",
                    expected_label="SUSPICIOUS",
                    description=(
                        "Provider connected to multiple unrelated "
                        "claimants in a planted network."
                    ),
                )
            )

            for invoice in selected_invoices:

                claim = claim_lookup[invoice["claim_id"]]

                claimant = next(
                    (
                        item for item in claimants
                        if item["claimant_id"] == claim["claimant_id"]
                    ),
                    None,
                )

                if claimant is None:
                    raise ValueError(
                        f"Claimant not found for {claim['claim_id']}"
                    )

                # Plant shared contact information.
                claimant["phone"] = shared_phone
                claimant["normalized_phone"] = normalized_phone

                # Plant the shared provider relationship.
                invoice["provider_id"] = selected_provider["provider_id"]

                self.used_claimant_ids.add(claimant["claimant_id"])
                self.used_invoice_ids.add(invoice["invoice_id"])

                ground_truth_records.append(
                    self.create_ground_truth_record(
                        network_id=network_id,
                        entity_type="CLAIMANT",
                        entity_id=claimant["claimant_id"],
                        pattern_type="SHARED_PROVIDER_CLUSTER",
                        role="SHARED_CONTACT",
                        issue_type="SHARED_CONTACT_AND_PROVIDER",
                        expected_label="SUSPICIOUS",
                        description=(
                            "Claimant shares a contact number with "
                            "other network members."
                        ),
                    )
                )

                ground_truth_records.append(
                    self.create_ground_truth_record(
                        network_id=network_id,
                        entity_type="CLAIM",
                        entity_id=claim["claim_id"],
                        pattern_type="SHARED_PROVIDER_CLUSTER",
                        role="NETWORK_CLAIM",
                        issue_type="SHARED_CONTACT_AND_PROVIDER",
                        expected_label="SUSPICIOUS",
                        description=(
                            "Claim is associated with the shared "
                            "provider cluster."
                        ),
                    )
                )

                ground_truth_records.append(
                    self.create_ground_truth_record(
                        network_id=network_id,
                        entity_type="INVOICE",
                        entity_id=invoice["invoice_id"],
                        pattern_type="SHARED_PROVIDER_CLUSTER",
                        role="SHARED_PROVIDER_INVOICE",
                        issue_type="SHARED_CONTACT_AND_PROVIDER",
                        expected_label="SUSPICIOUS",
                        description=(
                            "Invoice was issued by the shared provider."
                        ),
                    )
                )

            self.used_provider_ids.add(selected_provider["provider_id"])

        return ground_truth_records

    # --------------------------------------------------
    # 2. Duplicate invoice-number fraud pattern
    # --------------------------------------------------

    def inject_duplicate_invoice_patterns(
        self,
        claims: list[dict],
        providers: list[dict],
        invoices: list[dict],
        group_count: int = 4,
        invoices_per_group: int = 3,
    ) -> list[dict]:

        if group_count < 1:
            raise ValueError("Group count must be at least one.")

        if invoices_per_group < 2:
            raise ValueError("A duplicate group needs at least two invoices.")

        provider_ids = {
            provider["provider_id"]
            for provider in providers
        }

        claim_lookup = {
            claim["claim_id"]: claim
            for claim in claims
        }

        ground_truth_records = []

        for group_number in range(group_count):

            # Find invoices belonging to different claimants
            # and different providers.
            eligible_invoices = []

            seen_provider_ids = set()
            seen_claimant_ids = set()

            for invoice in invoices:

                invoice_id = invoice["invoice_id"]
                provider_id = invoice["provider_id"]

                if invoice_id in self.used_invoice_ids:
                    continue

                if provider_id in self.used_provider_ids:
                    continue

                if provider_id not in provider_ids:
                    continue

                claim = claim_lookup.get(invoice["claim_id"])

                if claim is None:
                    continue

                claimant_id = claim["claimant_id"]

                if claimant_id in self.used_claimant_ids:
                    continue

                if provider_id in seen_provider_ids:
                    continue

                if claimant_id in seen_claimant_ids:
                    continue

                eligible_invoices.append(invoice)
                seen_provider_ids.add(provider_id)
                seen_claimant_ids.add(claimant_id)

            if len(eligible_invoices) < invoices_per_group:
                raise ValueError(
                    "Not enough invoices with different providers "
                    "and claimants for duplicate invoice patterns."
                )

            selected_invoices = self.random.sample(
                eligible_invoices,
                invoices_per_group,
            )

            network_id = self.id_generator.generate("network")

            # Every invoice in this group receives the same number.
            duplicate_number = f"INV-REUSED-{group_number + 1:03d}"

            for invoice in selected_invoices:

                claim = claim_lookup[invoice["claim_id"]]
                provider_id = invoice["provider_id"]

                invoice["invoice_number"] = duplicate_number

                self.used_invoice_ids.add(invoice["invoice_id"])
                self.used_claimant_ids.add(claim["claimant_id"])
                self.used_provider_ids.add(provider_id)

                # Record the provider.
                ground_truth_records.append(
                    self.create_ground_truth_record(
                        network_id=network_id,
                        entity_type="PROVIDER",
                        entity_id=provider_id,
                        pattern_type="DUPLICATE_INVOICE_NUMBER",
                        role="INVOICE_SUBMITTING_PROVIDER",
                        issue_type="DUPLICATE_INVOICE_NUMBER",
                        expected_label="SUSPICIOUS",
                        description=(
                            "Provider submitted an invoice using "
                            "a number reused by other providers."
                        ),
                    )
                )

                # Record the claim.
                ground_truth_records.append(
                    self.create_ground_truth_record(
                        network_id=network_id,
                        entity_type="CLAIM",
                        entity_id=claim["claim_id"],
                        pattern_type="DUPLICATE_INVOICE_NUMBER",
                        role="ASSOCIATED_CLAIM",
                        issue_type="DUPLICATE_INVOICE_NUMBER",
                        expected_label="SUSPICIOUS",
                        description=(
                            "Claim is associated with an invoice "
                            "number reused across different providers."
                        ),
                    )
                )

                # Record the invoice.
                ground_truth_records.append(
                    self.create_ground_truth_record(
                        network_id=network_id,
                        entity_type="INVOICE",
                        entity_id=invoice["invoice_id"],
                        pattern_type="DUPLICATE_INVOICE_NUMBER",
                        role="DUPLICATE_INVOICE",
                        issue_type="DUPLICATE_INVOICE_NUMBER",
                        expected_label="SUSPICIOUS",
                        description=(
                            f"Invoice uses duplicated invoice number "
                            f"{duplicate_number}."
                        ),
                    )
                )

        return ground_truth_records

    # --------------------------------------------------
    # 3. Benign shared-address communities
    # --------------------------------------------------

    def inject_benign_communities(
        self,
        claimants: list[dict],
        community_count: int | None = None,
        members_per_community: int = 4,
    ) -> list[dict]:

        if community_count is None:
            community_count = self.random.randint(
                PATTERN_CONFIG["min_benign_communities"],
                PATTERN_CONFIG["max_benign_communities"],
            )

        if community_count < 1:
            raise ValueError("Community count must be at least one.")

        if members_per_community < 2:
            raise ValueError("A community needs at least two members.")

        available_claimants = [
            claimant
            for claimant in claimants
            if claimant["claimant_id"] not in self.used_claimant_ids
        ]

        required_claimants = community_count * members_per_community

        if len(available_claimants) < required_claimants:
            raise ValueError(
                f"Need {required_claimants} unused claimants for "
                f"{community_count} benign communities."
            )

        selected_claimants = self.random.sample(
            available_claimants,
            required_claimants,
        )

        ground_truth_records = []

        for community_index in range(community_count):

            network_id = self.id_generator.generate("network")

            # Each community gets its own shared address.
            shared_address = (
                f"Flat {community_index + 101}, "
                "Green Residency, MG Road, Hyderabad, India"
            )

            normalized_shared_address = normalize_address(
                shared_address
            )

            start = community_index * members_per_community
            end = start + members_per_community

            community_members = selected_claimants[start:end]

            for claimant in community_members:

                # Shared address, but individual phone numbers remain.
                claimant["address"] = shared_address
                claimant["normalized_address"] = (
                    normalized_shared_address
                )
                claimant["city"] = "Hyderabad"
                claimant["state"] = "Telangana"

                self.used_claimant_ids.add(claimant["claimant_id"])

                ground_truth_records.append(
                    self.create_ground_truth_record(
                        network_id=network_id,
                        entity_type="CLAIMANT",
                        entity_id=claimant["claimant_id"],
                        pattern_type="BENIGN_SHARED_ADDRESS",
                        role="COMMUNITY_MEMBER",
                        issue_type="SHARED_RESIDENTIAL_ADDRESS",
                        expected_label="BENIGN",
                        description=(
                            "Claimant shares a legitimate residential "
                            "address with other community members."
                        ),
                    )
                )

        return ground_truth_records

    # --------------------------------------------------
    # 4. Run all currently implemented patterns
    # --------------------------------------------------

    def inject_all_patterns(
        self,
        claimants: list[dict],
        claims: list[dict],
        providers: list[dict],
        invoices: list[dict],
    ) -> list[dict]:

        # Pattern 1: Shared provider and contact information
        suspicious_records = self.inject_suspicious_networks(
            claimants=claimants,
            claims=claims,
            providers=providers,
            invoices=invoices,
        )

        # Pattern 2: Duplicate invoice numbers
        duplicate_invoice_records = self.inject_duplicate_invoice_patterns(
            claims=claims,
            providers=providers,
            invoices=invoices,
        )

        # Pattern 3: Benign shared-address communities
        benign_records = self.inject_benign_communities(
            claimants=claimants,
        )

        return (
            suspicious_records
            + duplicate_invoice_records
            + benign_records
        )


# --------------------------------------------------
# Independent test
# --------------------------------------------------

if __name__ == "__main__":

    from generator.claimant_generator import ClaimantGenerator
    from generator.provider_generator import ProviderGenerator
    from generator.policy_generator import PolicyGenerator
    from generator.incident_generator import IncidentGenerator
    from generator.claim_generator import ClaimGenerator
    from generator.invoice_generator import InvoiceGenerator

    id_generator = IDGenerator()

    print("Generating test dataset...")

    # Generate enough records for 20-30 suspicious
    # networks and 10-15 benign communities.
    claimants = ClaimantGenerator(
        id_generator
    ).generate_claimants(600)

    providers = ProviderGenerator(
        id_generator
    ).generate_providers(250)

    policies = PolicyGenerator(
        id_generator
    ).generate_policies(
        claimants,
        900,
    )

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

    print("Base test dataset generated.")

    injector = PatternInjector(id_generator)

    ground_truth = injector.inject_all_patterns(
        claimants=claimants,
        claims=claims,
        providers=providers,
        invoices=invoices,
    )

    suspicious_network_ids = {
        record["planted_network_id"]
        for record in ground_truth
        if record["expected_label"] == "SUSPICIOUS"
    }

    benign_network_ids = {
        record["planted_network_id"]
        for record in ground_truth
        if record["expected_label"] == "BENIGN"
    }

    suspicious_records = [
        record for record in ground_truth
        if record["expected_label"] == "SUSPICIOUS"
    ]

    benign_records = [
        record for record in ground_truth
        if record["expected_label"] == "BENIGN"
    ]

    print("\n========== PATTERN INJECTION SUMMARY ==========")

    print(f"Suspicious networks: {len(suspicious_network_ids)}")
    print(f"Benign communities: {len(benign_network_ids)}")

    print(f"Suspicious ground-truth records: {len(suspicious_records)}")
    print(f"Benign ground-truth records: {len(benign_records)}")

    print(f"Total ground-truth records: {len(ground_truth)}")

    print(
        "\nUnique claimants used: "
        f"{len(injector.used_claimant_ids)}"
    )

    print(
        "Unique providers used: "
        f"{len(injector.used_provider_ids)}"
    )

    print(
        "Unique invoices used: "
        f"{len(injector.used_invoice_ids)}"
    )

    from collections import defaultdict

    duplicate_groups = defaultdict(list)

    for invoice in invoices:
        if invoice["invoice_number"].startswith("INV-REUSED-"):
            duplicate_groups[invoice["invoice_number"]].append(invoice)

    print("\n========== DUPLICATE INVOICE VALIDATION ==========")

    for invoice_number, group in duplicate_groups.items():
        provider_ids = {
            invoice["provider_id"] for invoice in group
        }
        claim_ids = {
            invoice["claim_id"] for invoice in group
        }

        print(f"\nInvoice number: {invoice_number}")
        print(f"Invoice count: {len(group)}")
        print(f"Unique providers: {len(provider_ids)}")
        print(f"Unique claims: {len(claim_ids)}")

        assert len(group) == 3
        assert len(provider_ids) == 3
        assert len(claim_ids) == 3

    print("\nAll duplicate invoice patterns validated.")