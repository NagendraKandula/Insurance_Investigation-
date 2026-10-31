"""
Prepare, validate and write the hidden ground-truth labels.

Ground truth is written to its own directory, away from the data files the
detector reads, and is checked to make sure no label column leaks into the
input tables.
"""

import json
from collections import Counter
from pathlib import Path

from generator.export import write_table

ALLOWED_LABELS = {"SUSPICIOUS", "BENIGN", "DATA_QUALITY_EXCEPTION"}

# entity_type in ground truth -> (dataset name, id field)
ENTITY_SOURCES = {
    "CLAIMANT": ("claimants", "claimant_id"),
    "PROVIDER": ("providers", "provider_id"),
    "POLICY": ("policies", "policy_id"),
    "INCIDENT": ("incidents", "incident_id"),
    "CLAIM": ("claims", "claim_id"),
    "INVOICE": ("invoices", "invoice_id"),
    "PAYMENT": ("payments", "payment_id"),
}

# These must never appear in any input table.
LEAKY_COLUMNS = {
    "planted_network_id", "expected_label", "pattern_type",
    "role_in_network", "issue_type", "ground_truth",
}


def finalize_ground_truth(records: list[dict], generation_run_id: str) -> list[dict]:
    """Return copies of the injector's records stamped with the run id."""
    return [{**record, "generation_run_id": generation_run_id} for record in records]


def validate_ground_truth(
    records: list[dict],
    datasets: dict[str, list[dict]],
) -> list[str]:
    """Return a list of problems (empty list means the labels are consistent)."""
    problems = []

    known_ids = {
        entity_type: {row[id_field] for row in datasets[dataset]}
        for entity_type, (dataset, id_field) in ENTITY_SOURCES.items()
        if dataset in datasets
    }

    seen = set()

    for record in records:
        entity_type = record["entity_type"]
        entity_id = record["entity_id"]

        if record["expected_label"] not in ALLOWED_LABELS:
            problems.append(f"Bad label {record['expected_label']!r} on {entity_id}")

        if entity_type not in known_ids:
            problems.append(f"Unknown entity_type {entity_type!r} on {entity_id}")
        elif entity_id not in known_ids[entity_type]:
            problems.append(f"{entity_type} {entity_id} is not in the data")

        key = (
            record["planted_network_id"], entity_type, entity_id,
            record["pattern_type"], record["role_in_network"],
        )
        if key in seen:
            problems.append(f"Duplicate ground-truth row: {key}")
        seen.add(key)

    return problems


def assert_no_leakage(datasets: dict[str, list[dict]]) -> None:
    """Fail if any input table carries a ground-truth column."""
    for name, rows in datasets.items():
        if name == "ground_truth" or not rows:
            continue
        leaked = LEAKY_COLUMNS & set(rows[0].keys())
        if leaked:
            raise ValueError(f"Ground-truth columns leaked into {name}: {sorted(leaked)}")


def summarize(records: list[dict]) -> dict:
    """Counts by label, pattern and number of planted networks."""
    networks = {}
    for record in records:
        networks.setdefault(record["expected_label"], set()).add(
            record["planted_network_id"]
        )

    return {
        "records": len(records),
        "records_by_label": dict(Counter(r["expected_label"] for r in records)),
        "records_by_pattern": dict(Counter(r["pattern_type"] for r in records)),
        "networks_by_label": {label: len(ids) for label, ids in networks.items()},
    }


def write_ground_truth(
    records: list[dict],
    directory: Path,
    ignore_columns: set[str] | None = None,
) -> dict:
    """Write ground_truth.csv and ground_truth.json; return the CSV's manifest entry."""
    info = write_table("ground_truth", records, directory, ignore_columns)

    json_path = directory / "ground_truth.json"
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, default=str)

    return info