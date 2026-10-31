
from collections import defaultdict


class IDGenerator:
    """
    Generates sequential, unique IDs for each entity type.

    Example:
        CPT-000001
        CPT-000002
        POL-000001
    """

    PREFIXES = {
        "claimant": "CPT",
        "provider": "PRV",
        "policy": "POL",
        "incident": "INC",
        "claim": "CLM",
        "invoice": "INV",
        "payment": "PAY",
        "network": "NET",
        "investigation": "IVG",
        "indicator": "IND",
        "exception": "EXC",
    }

    def __init__(self):
        self.counters = defaultdict(int)

    def generate(self, entity_type: str) -> str:
        """
        Generate the next ID for an entity.

        Args:
            entity_type: Entity name, such as claimant or policy.

        Returns:
            Generated ID string.
        """

        if entity_type not in self.PREFIXES:
            raise ValueError(
                f"Unknown entity type: {entity_type}"
            )

        self.counters[entity_type] += 1

        prefix = self.PREFIXES[entity_type]
        number = self.counters[entity_type]

        return f"{prefix}-{number:06d}"

    def generate_batch(self, entity_type: str, count: int) -> list[str]:
        """
        Generate multiple sequential IDs.
        """

        if count < 0:
            raise ValueError("Count cannot be negative.")

        return [
            self.generate(entity_type)
            for _ in range(count)
        ]


# Simple standalone test
if __name__ == "__main__":
    id_gen = IDGenerator()

    print(id_gen.generate("claimant"))
    print(id_gen.generate("claimant"))
    print(id_gen.generate("policy"))

    print(id_gen.generate_batch("provider", 3))
