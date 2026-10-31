from collections import defaultdict
from itertools import combinations


class EdgeGapDetector:

    def __init__(self, graph):
        self.graph = graph

    def detect_missing_phone_edges(self, claimants):

        print("Checking for missing phone relationships...")

        phone_groups = defaultdict(list)

        # Group claimants by normalized phone number
        for claimant in claimants:

            phone = claimant.get("normalized_phone")

            if not phone:
                continue

            phone_groups[phone].append(claimant)

        findings = []

        for phone, group in phone_groups.items():

            if len(group) < 2:
                continue

            # Check every claimant pair
            for claimant_a, claimant_b in combinations(group, 2):

                id_a = str(claimant_a["claimant_id"])
                id_b = str(claimant_b["claimant_id"])

                # Check whether SHARES_PHONE already exists
                existing = self.graph.get_edge_data(id_a, id_b, default={})
                reverse = self.graph.get_edge_data(id_b, id_a, default={})

                has_phone_edge = any(
                    edge.get("relationship_type") == "SHARES_PHONE"
                    for edge in list(existing.values()) + list(reverse.values())
                )

                if not has_phone_edge:

                    findings.append({
                        "entity_type": "claimant",
                        "entity_id": id_a,
                        "related_entity_id": id_b,
                        "indicator_type": "MISSING_PHONE_RELATIONSHIP",
                        "evidence": {
                            "shared_phone": phone,
                            "claimant_count": len(group)
                        }
                    })

        print(f"Missing phone relationships detected: {len(findings)}")

        return findings