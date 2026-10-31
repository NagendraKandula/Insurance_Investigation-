
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from generator.config import fake
from generator.id_generator import IDGenerator


POLICY_TYPES = [
    "HEALTH",
    "MOTOR",
    "HOME",
    "LIFE",
    "TRAVEL",
]


class PolicyGenerator:

    def __init__(self, id_generator: IDGenerator):
        self.id_generator = id_generator

    def generate_policy(self, claimant: dict) -> dict:
        """
        Generate a policy linked to an existing claimant.
        """

        if not claimant or not claimant.get("claimant_id"):
            raise ValueError("A valid claimant is required.")

        policy_type = fake.random_element(POLICY_TYPES)

        coverage_amount = Decimal(
            str(fake.random_int(min=100000, max=10000000))
        )

        deductible_amount = Decimal(
            str(fake.random_int(min=1000, max=50000))
        )

        premium_amount = (
            coverage_amount * Decimal("0.02")
        ).quantize(Decimal("0.01"))

        start_date = fake.date_between(
            start_date="-5y",
            end_date="-30d"
        )

        end_date = start_date + timedelta(days=365)
 
        # Ensure policy status matches its dates.
        from datetime import date
        today = date.today()

        if end_date < today:
            policy_status = "EXPIRED"
        else:
            policy_status = fake.random_element([
                "ACTIVE",
                "ACTIVE",
                "ACTIVE",
                "CANCELLED",
            ])

        now = datetime.now(timezone.utc)

        policy = {
            "policy_id": self.id_generator.generate("policy"),
            "claimant_id": claimant["claimant_id"],
            "policy_number": (
                f"POLICY-{self.id_generator.counters['policy']:06d}"
            ),
            "policy_type": policy_type,
            "coverage_amount": coverage_amount,
            "premium_amount": premium_amount,
            "deductible_amount": deductible_amount,
            "start_date": start_date,
            "end_date": end_date,
            "status": policy_status,
            "created_at": now,
            "updated_at": now,
        }

        return policy

    def generate_policies(
        self,
        claimants: list[dict],
        count: int
    ) -> list[dict]:
        """
        Generate policies using existing claimant records.
        """

        if count < 0:
            raise ValueError("Count cannot be negative.")

        if count > 0 and not claimants:
            raise ValueError(
                "Claimants are required to generate policies."
            )

        policies = []

        for _ in range(count):
            claimant = fake.random_element(claimants)

            policy = self.generate_policy(claimant)

            policies.append(policy)

        return policies


if __name__ == "__main__":

    id_generator = IDGenerator()

    from generator.claimant_generator import ClaimantGenerator

    claimant_generator = ClaimantGenerator(id_generator)

    claimants = claimant_generator.generate_claimants(5)

    policy_generator = PolicyGenerator(id_generator)

    policies = policy_generator.generate_policies(
        claimants,
        10
    )

    for policy in policies:
        print(policy)
        print("-" * 60)

    print(f"Total policies generated: {len(policies)}")
