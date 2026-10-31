
from datetime import datetime, timezone
from decimal import Decimal

from generator.config import fake
from generator.id_generator import IDGenerator


TRANSACTION_TYPES = ["REFUND", "REVERSAL"]


class PaymentGenerator:

    def __init__(self, id_generator: IDGenerator):
        self.id_generator = id_generator

    def generate_payment(
        self,
        invoice: dict,
        transaction_type: str = "PAYMENT",
        amount: Decimal | None = None,
        payment_date=None,
    ) -> dict:

        if not invoice or not invoice.get("invoice_id"):
            raise ValueError("A valid invoice is required.")

        if transaction_type not in ["PAYMENT", "REFUND", "REVERSAL"]:
            raise ValueError("Invalid transaction type.")

        invoice_amount = Decimal(str(invoice["invoice_amount"]))

        if amount is None:
            amount = Decimal(
                str(
                    fake.random_int(
                        min=1,
                        max=int(invoice_amount),
                    )
                )
            )

        amount = Decimal(str(amount))

        if amount <= 0:
            raise ValueError("Payment amount must be positive.")

        if amount > invoice_amount:
            raise ValueError("Payment cannot exceed invoice amount.")

        if payment_date is None:
            payment_date = fake.date_between(
                start_date=invoice["invoice_date"],
                end_date="today",
            )

        now = datetime.now(timezone.utc)

        payment_number = self.id_generator.counters["payment"]

        return {
            "payment_id": self.id_generator.generate("payment"),
            "invoice_id": invoice["invoice_id"],
            "transaction_reference": f"TXN-{payment_number + 1:06d}",
            "payment_amount": amount,
            "payment_date": payment_date,
            "payment_method": fake.random_element([
                "BANK_TRANSFER",
                "UPI",
                "CREDIT_CARD",
                "DEBIT_CARD",
                "CHEQUE",
            ]),
            "transaction_type": transaction_type,
            "status": "COMPLETED",
            "created_at": now,
        }

    def generate_payments(
        self,
        invoices: list[dict],
        count: int,
    ) -> list[dict]:

        if count < 0:
            raise ValueError("Count cannot be negative.")

        if count == 0:
            return []

        if not invoices:
            raise ValueError("Invoices are required.")

        if count < len(invoices):
            raise ValueError(
                "Payment count must be at least the number of invoices "
                "so every invoice receives an initial payment."
            )

        payments = []
        completed_payments = []

        # Generate one initial payment for every invoice.
        for invoice in invoices:

            invoice_amount = Decimal(str(invoice["invoice_amount"]))

            payment_amount = Decimal(
                str(
                    fake.random_int(
                        min=1,
                        max=int(invoice_amount),
                    )
                )
            )

            payment = self.generate_payment(
                invoice,
                "PAYMENT",
                payment_amount,
            )

            payments.append(payment)

            completed_payments.append({
                "invoice": invoice,
                "remaining_refundable": payment_amount,
                "original_payment_date": payment["payment_date"],
            })

        # Generate additional refund/reversal transactions.
        extra_count = count - len(invoices)

        eligible_payments = [
            item for item in completed_payments
            if item["remaining_refundable"] > 0
        ]

        if extra_count > len(eligible_payments):
            raise ValueError(
                "Not enough eligible payments for additional "
                "refund/reversal transactions."
            )

        selected_payments = fake.random_sample(
            eligible_payments,
            length=extra_count,
        )

        for item in selected_payments:

            invoice = item["invoice"]
            refundable_amount = item["remaining_refundable"]

            refund_amount = Decimal(
                str(
                    fake.random_int(
                        min=1,
                        max=int(refundable_amount),
                    )
                )
            )

            transaction_type = fake.random_element(TRANSACTION_TYPES)

            transaction = self.generate_payment(
                invoice,
                transaction_type,
                refund_amount,
                payment_date=fake.date_between(
                    start_date=item["original_payment_date"],
                    end_date="today",
                ),
            )

            payments.append(transaction)

        return payments


if __name__ == "__main__":

    from generator.claimant_generator import ClaimantGenerator
    from generator.provider_generator import ProviderGenerator
    from generator.policy_generator import PolicyGenerator
    from generator.incident_generator import IncidentGenerator
    from generator.claim_generator import ClaimGenerator
    from generator.invoice_generator import InvoiceGenerator

    id_generator = IDGenerator()

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

    invoice_generator = InvoiceGenerator(id_generator)
    invoices = invoice_generator.generate_invoices(
        claims,
        providers,
        10,
    )

    payment_generator = PaymentGenerator(id_generator)

    payments = payment_generator.generate_payments(
        invoices,
        15,
    )

    for payment in payments:
        print(payment)
        print("-" * 60)

    print(f"Total payment transactions generated: {len(payments)}")
