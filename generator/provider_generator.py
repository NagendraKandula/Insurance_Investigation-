
from datetime import datetime, timezone, timedelta

from generator.config import fake
from generator.id_generator import IDGenerator
from generator.normalizers import (
    normalize_email,
    normalize_phone,
    normalize_address,
)

from generator.claimant_generator import INDIAN_CITIES


PROVIDER_TYPES = [
    "HOSPITAL",
    "CLINIC",
    "GARAGE",
    "AUTO_REPAIR",
    "PHARMACY",
    "DIAGNOSTIC_CENTER",
    "CONSTRUCTION",
    "LEGAL_SERVICE",
]

PROVIDER_STATUSES = [
    "ACTIVE",
    "ACTIVE",
    "ACTIVE",
    "INACTIVE",
]


class ProviderGenerator:

    def __init__(self, id_generator: IDGenerator):
        self.id_generator = id_generator

    def generate_provider(self) -> dict:
        """Generate one synthetic insurance service provider."""

        provider_type = fake.random_element(PROVIDER_TYPES)

        city, state = fake.random_element(INDIAN_CITIES)

        provider_name = (
            f"{fake.company()} {provider_type.replace('_', ' ').title()}"
        )

        email = fake.unique.company_email()

        phone = (
            str(fake.random_int(min=6, max=9))
            + fake.numerify("#########")
        )

        address = (
            f"{fake.street_address()}, "
            f"{city}, {state}, India"
        )

        registration_date = fake.date_between(
            start_date="-15y",
            end_date="today"
        )

        now = datetime.now(timezone.utc)

        provider = {
            "provider_id": self.id_generator.generate("provider"),
            "provider_name": provider_name,
            "provider_type": provider_type,
            "registration_number": (
                f"REG-{self.id_generator.counters['provider']:06d}"
            ),
            "email": email,
            "normalized_email": normalize_email(email),
            "phone": phone,
            "normalized_phone": normalize_phone(phone),
            "address": address,
            "normalized_address": normalize_address(address),
            "city": city,
            "state": state,
            "registration_date": registration_date,
            "status": fake.random_element(PROVIDER_STATUSES),
            "created_at": now,
        }

        return provider

    def generate_providers(self, count: int) -> list[dict]:
        """Generate multiple providers."""

        if count < 0:
            raise ValueError("Count cannot be negative.")

        return [
            self.generate_provider()
            for _ in range(count)
        ]


if __name__ == "__main__":

    id_generator = IDGenerator()

    provider_generator = ProviderGenerator(id_generator)

    providers = provider_generator.generate_providers(5)

    for provider in providers:
        print(provider)
        print("-" * 60)

    print(f"Total providers generated: {len(providers)}")
