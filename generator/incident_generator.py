
from datetime import datetime, timezone
from decimal import Decimal

from generator.config import fake
from generator.id_generator import IDGenerator
from generator.claimant_generator import INDIAN_CITIES


INCIDENT_TYPES = [
    "VEHICLE_ACCIDENT",
    "FIRE",
    "THEFT",
    "MEDICAL",
    "PROPERTY_DAMAGE",
    "NATURAL_DISASTER",
]


INCIDENT_DESCRIPTIONS = {
    "VEHICLE_ACCIDENT": [
        "Vehicle collision reported on a public road",
        "Multi-vehicle accident resulting in damage",
        "Vehicle damaged in a parking area",
    ],
    "FIRE": [
        "Fire damage reported at residential property",
        "Electrical fire caused property damage",
        "Commercial building affected by fire",
    ],
    "THEFT": [
        "Theft reported by the policyholder",
        "Vehicle reported stolen",
        "Personal property reported missing",
    ],
    "MEDICAL": [
        "Emergency medical treatment reported",
        "Hospital admission following an illness",
        "Medical procedure requiring hospitalization",
    ],
    "PROPERTY_DAMAGE": [
        "Water leakage caused property damage",
        "Structural damage reported at property",
        "Building damage following an incident",
    ],
    "NATURAL_DISASTER": [
        "Flood damage reported by property owner",
        "Storm damage affected insured property",
        "Heavy rainfall caused property damage",
    ],
}


class IncidentGenerator:

    def __init__(self, id_generator: IDGenerator):
        self.id_generator = id_generator

    def generate_incident(self) -> dict:

        incident_type = fake.random_element(INCIDENT_TYPES)

        city, state = fake.random_element(INDIAN_CITIES)

        incident_date = fake.date_between(
            start_date="-3y",
            end_date="-2d"
        )

        reported_at = fake.date_between(
            start_date=incident_date,
            end_date="today"
        )

        description = fake.random_element(
            INCIDENT_DESCRIPTIONS[incident_type]
        )

        now = datetime.now(timezone.utc)

        return {
            "incident_id": self.id_generator.generate("incident"),
            "incident_type": incident_type,
            "incident_date": incident_date,
            "reported_at": reported_at,
            "description": description,
            "location": f"{city}, {state}, India",
            "city": city,
            "state": state,
            "estimated_loss": Decimal(
                str(fake.random_int(min=5000, max=2000000))
            ),
            "created_at": now,
        }

    def generate_incidents(self, count: int) -> list[dict]:

        if count < 0:
            raise ValueError("Count cannot be negative.")

        return [
            self.generate_incident()
            for _ in range(count)
        ]


if __name__ == "__main__":

    id_generator = IDGenerator()

    incident_generator = IncidentGenerator(id_generator)

    incidents = incident_generator.generate_incidents(5)

    for incident in incidents:
        print(incident)
        print("-" * 60)

    print(f"Total incidents generated: {len(incidents)}")
