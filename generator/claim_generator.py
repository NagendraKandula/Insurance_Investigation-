
from datetime import datetime, timezone
from decimal import Decimal

from generator.config import fake
from generator.id_generator import IDGenerator


CLAIM_STATUSES = [
    "PENDING",
    "PENDING",
    "UNDER_REVIEW",
    "APPROVED",
    "APPROVED",
    "REJECTED",
]


class ClaimGenerator:

    def __init__(self, id_generator: IDGenerator):
        self.id_generator = id_generator

    def generate_claim(
        self,
        claimant: dict,
        policy: dict,
        incident: dict,
    ) -> dict:

        if policy["claimant_id"] != claimant["claimant_id"]:
            raise ValueError(
                "The policy does not belong to the selected claimant."
            )

        # The incident must have occurred during the policy coverage period.
        if not (
            policy["start_date"]
            <= incident["incident_date"]
            <= policy["end_date"]
        ):
            raise ValueError(
                "The incident date is outside the policy coverage period."
            )

        # The claim must be filed after the incident was reported.
        claim_date = fake.date_between(
            start_date=incident["reported_at"],
            end_date="today",
        )

        # Keep normal claim amounts within policy coverage.
        maximum_claim_amount = min(
            policy["coverage_amount"],
            incident["estimated_loss"] * Decimal("1.20"),
        )

        claim_amount = Decimal(
            str(
                fake.random_int(
                    min=5000,
                    max=int(maximum_claim_amount),
                )
            )
        )

        status = fake.random_element(CLAIM_STATUSES)

        if status == "APPROVED":
            approved_amount = Decimal(
                str(
                    fake.random_int(
                        min=1,
                        max=int(claim_amount),
                    )
                )
            )
        else:
            approved_amount = Decimal("0")

        now = datetime.now(timezone.utc)

        return {
            "claim_id": self.id_generator.generate("claim"),
            "claimant_id": claimant["claimant_id"],
            "policy_id": policy["policy_id"],
            "incident_id": incident["incident_id"],
            "claim_number": (
                f"CLAIM-{self.id_generator.counters['claim']:06d}"
            ),
            "claim_amount": claim_amount,
            "approved_amount": approved_amount,
            "claim_date": claim_date,
            "description": (
                f"Insurance claim for {incident['incident_type']}"
            ),
            "status": status,
            "created_at": now,
            "updated_at": now,
        }

    def generate_claims(
        self,
        claimants: list[dict],
        policies: list[dict],
        incidents: list[dict],
        count: int,
    ) -> list[dict]:

        if count < 0:
            raise ValueError("Count cannot be negative.")

        if count == 0:
            return []

        if not claimants or not policies or not incidents:
            raise ValueError(
                "Claimants, policies, and incidents are required."
            )

        claimant_lookup = {
            claimant["claimant_id"]: claimant
            for claimant in claimants
        }

        # Group incidents that occurred during each policy's coverage period.
        eligible_data = []

        for policy in policies:

            claimant = claimant_lookup.get(policy["claimant_id"])

            if claimant is None:
                raise ValueError(
                    f"Claimant not found for policy {policy['policy_id']}"
                )

            eligible_incidents = [
                incident
                for incident in incidents
                if (
                    policy["start_date"]
                    <= incident["incident_date"]
                    <= policy["end_date"]
                )
            ]

            if eligible_incidents:
                eligible_data.append(
                    (claimant, policy, eligible_incidents)
                )

        if not eligible_data:
            raise ValueError(
                "No policies have incidents within their coverage periods."
            )

        claims = []

        for _ in range(count):

            claimant, policy, eligible_incidents = (
                fake.random_element(eligible_data)
            )

            incident = fake.random_element(eligible_incidents)

            claim = self.generate_claim(
                claimant,
                policy,
                incident,
            )

            claims.append(claim)

        return claims


if __name__ == "__main__":

    from generator.claimant_generator import ClaimantGenerator
    from generator.policy_generator import PolicyGenerator
    from generator.incident_generator import IncidentGenerator

    id_generator = IDGenerator()

    # Generate parent records first.
    claimant_generator = ClaimantGenerator(id_generator)
    claimants = claimant_generator.generate_claimants(100)

    policy_generator = PolicyGenerator(id_generator)
    policies = policy_generator.generate_policies(claimants, 150)

    incident_generator = IncidentGenerator(id_generator)
    incidents = incident_generator.generate_incidents(200)

    # Generate claims using existing records.
    claim_generator = ClaimGenerator(id_generator)

    claims = claim_generator.generate_claims(
        claimants,
        policies,
        incidents,
        10,
    )

    for claim in claims:
        print(claim)
        print("-" * 60)

    print(f"Total claims generated: {len(claims)}")
