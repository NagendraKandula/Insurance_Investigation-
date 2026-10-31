
from datetime import datetime, timezone

from generator.config import fake
from generator.id_generator import IDGenerator
from generator.normalizers import (
    normalize_email,
    normalize_phone,
    normalize_address,
)


# Keep city and state combinations geographically consistent.
INDIAN_CITIES = [
    ("Visakhapatnam", "Andhra Pradesh"),
    ("Vijayawada", "Andhra Pradesh"),
    ("Proddatur", "Andhra Pradesh"),
    ("Hyderabad", "Telangana"),
    ("Warangal", "Telangana"),
    ("Bengaluru", "Karnataka"),
    ("Mysuru", "Karnataka"),
    ("Chennai", "Tamil Nadu"),
    ("Coimbatore", "Tamil Nadu"),
    ("Mumbai", "Maharashtra"),
    ("Pune", "Maharashtra"),
    ("Nagpur", "Maharashtra"),
    ("Aligarh", "Uttar Pradesh"),
    ("Lucknow", "Uttar Pradesh"),
    ("Delhi", "Delhi"),
    ("Jaipur", "Rajasthan"),
    ("Kolkata", "West Bengal"),
    ("Bhubaneswar", "Odisha"),
    ("Kochi", "Kerala"),
    ("Ahmedabad", "Gujarat"),
]


class ClaimantGenerator:

    def __init__(self, id_generator: IDGenerator):
        self.id_generator = id_generator

    def generate_claimant(self) -> dict:

        first_name = fake.first_name()
        last_name = fake.last_name()

        email = fake.unique.email()

        # Generate a 10-digit, Indian-style mobile number.
        phone = (
            str(fake.random_int(min=6, max=9))
            + fake.numerify("#########")
        )

        city, state = fake.random_element(INDIAN_CITIES)

        street = fake.street_address()
        address = f"{street}, {city}, {state}, India"

        # Generate a six-digit postal-code-shaped value.
        postal_code = (
            str(fake.random_int(min=1, max=9))
            + fake.numerify("#####")
        )

        now = datetime.now(timezone.utc)

        claimant = {
            "claimant_id": self.id_generator.generate("claimant"),
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": fake.date_of_birth(
                minimum_age=18,
                maximum_age=85
            ),
            "gender": fake.random_element(
                elements=("Male", "Female", "Other")
            ),
            "email": email,
            "normalized_email": normalize_email(email),
            "phone": phone,
            "normalized_phone": normalize_phone(phone),
            "address": address,
            "normalized_address": normalize_address(address),
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "created_at": now,
            "updated_at": now,
        }

        return claimant

    def generate_claimants(self, count: int) -> list[dict]:

        if count < 0:
            raise ValueError("Count cannot be negative.")

        return [
            self.generate_claimant()
            for _ in range(count)
        ]


if __name__ == "__main__":

    id_generator = IDGenerator()
    claimant_generator = ClaimantGenerator(id_generator)

    claimants = claimant_generator.generate_claimants(5)

    for claimant in claimants:
        print(claimant)
        print("-" * 60)

    print(f"Total claimants generated: {len(claimants)}")
