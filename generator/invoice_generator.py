
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from generator.config import fake
from generator.id_generator import IDGenerator


INVOICE_STATUSES = [
    "SUBMITTED",
    "SUBMITTED",
    "PENDING",
    "PAID",
    "PAID",
    "REJECTED",
]


class InvoiceGenerator:

    def __init__(self, id_generator: IDGenerator):
        self.id_generator = id_generator

    def generate_invoice(self, claim: dict, provider: dict) -> dict:

        if not claim or not claim.get("claim_id"):
            raise ValueError("A valid claim is required.")

        if not provider or not provider.get("provider_id"):
            raise ValueError("A valid provider is required.")

        claim_amount = Decimal(str(claim["claim_amount"]))

        invoice_amount = Decimal(
            str(
                fake.random_int(
                    min=5000,
                    max=int(claim_amount),
                )
            )
        )

        invoice_date = fake.date_between(
            start_date=claim["claim_date"],
            end_date="today",
        )

        due_date = invoice_date + timedelta(days=30)

        now = datetime.now(timezone.utc)

        return {
            "invoice_id": self.id_generator.generate("invoice"),
            "provider_id": provider["provider_id"],
            "claim_id": claim["claim_id"],
            "invoice_number": (
                f"INV-NORMAL-{self.id_generator.counters['invoice']:06d}"
            ),
            "invoice_amount": invoice_amount,
            "invoice_date": invoice_date,
            "due_date": due_date,
            "description": (
                f"Invoice for claim {claim['claim_number']}"
            ),
            "status": fake.random_element(INVOICE_STATUSES),
            "created_at": now,
            "updated_at": now,
        }

    def generate_invoices(
        self,
        claims: list[dict],
        providers: list[dict],
        count: int,
    ) -> list[dict]:

        if count < 0:
            raise ValueError("Count cannot be negative.")

        if count == 0:
            return []

        if not claims or not providers:
            raise ValueError(
                "Claims and providers are required to generate invoices."
            )

        invoices = []

        for _ in range(count):

            claim = fake.random_element(claims)
            provider = fake.random_element(providers)

            invoice = self.generate_invoice(claim, provider)

            invoices.append(invoice)

        return invoices


if __name__ == "__main__":

    from generator.claimant_generator import ClaimantGenerator
    from generator.provider_generator import ProviderGenerator
    from generator.policy_generator import PolicyGenerator
    from generator.incident_generator import IncidentGenerator
    from generator.claim_generator import ClaimGenerator

    id_generator = IDGenerator()

    # Generate parent records first.
    claimant_generator = ClaimantGenerator(id_generator)
    claimants = claimant_generator.generate_claimants(100)

    provider_generator = ProviderGenerator(id_generator)
    providers = provider_generator.generate_providers(20)

    policy_generator = PolicyGenerator(id_generator)
    policies = policy_generator.generate_policies(claimants, 150)

    incident_generator = IncidentGenerator(id_generator)
    incidents = incident_generator.generate_incidents(200)

    claim_generator = ClaimGenerator(id_generator)
    claims = claim_generator.generate_claims(
        claimants,
        policies,
        incidents,
        100,
    )

    # Generate invoices.
    invoice_generator = InvoiceGenerator(id_generator)

    invoices = invoice_generator.generate_invoices(
        claims,
        providers,
        10,
    )

    for invoice in invoices:
        print(invoice)
        print("-" * 60)

    print(f"Total invoices generated: {len(invoices)}")
