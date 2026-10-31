"""
Export generated datasets to CSV and write a manifest with checksums.

The CSV files are the single source of truth: load_neon.py loads exactly
these files, so the checksums describe exactly what ends up in the database.
"""

import csv
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# Column order here must match the CREATE TABLE definitions.
# Identity columns (edge_id, ground_truth_id, event_id) are omitted on
# purpose: the database assigns them.
TABLE_COLUMNS = {
    "users": [
        "user_id", "full_name", "email", "role", "status", "created_at",
    ],
    "claimants": [
        "claimant_id", "first_name", "last_name", "date_of_birth", "gender",
        "email", "normalized_email", "phone", "normalized_phone",
        "address", "normalized_address", "city", "state", "postal_code",
        "created_at", "updated_at",
    ],
    "providers": [
        "provider_id", "provider_name", "provider_type",
        "registration_number", "email", "normalized_email", "phone",
        "normalized_phone", "address", "normalized_address", "city",
        "state", "registration_date", "status", "created_at",
    ],
    "policies": [
        "policy_id", "claimant_id", "policy_number", "policy_type",
        "coverage_amount", "premium_amount", "deductible_amount",
        "start_date", "end_date", "status", "created_at", "updated_at",
    ],
    "incidents": [
        "incident_id", "incident_type", "incident_date", "reported_at",
        "description", "location", "city", "state", "estimated_loss",
        "created_at",
    ],
    "claims": [
        "claim_id", "claimant_id", "policy_id", "incident_id",
        "claim_number", "claim_amount", "approved_amount", "claim_date",
        "description", "status", "created_at", "updated_at",
    ],
    "invoices": [
        "invoice_id", "provider_id", "claim_id", "invoice_number",
        "invoice_amount", "invoice_date", "due_date", "description",
        "status", "created_at", "updated_at",
    ],
    "payments": [
        "payment_id", "invoice_id", "transaction_reference",
        "payment_amount", "payment_date", "payment_method",
        "transaction_type", "status", "created_at",
    ],
    "relationship_edges": [
        "source_type", "source_id", "target_type", "target_id",
        "relationship_type", "confidence", "source", "valid_from",
        "valid_to", "created_at",
    ],
    "claim_status_events": [
        "claim_id", "from_status", "to_status", "event_time",
        "actor_id", "remarks",
    ],
    "payment_status_events": [
        "payment_id", "from_status", "to_status", "event_time",
        "actor_id", "remarks",
    ],
    "ground_truth": [
        "planted_network_id", "entity_type", "entity_id", "pattern_type",
        "role_in_network", "issue_type", "expected_label", "description",
        "generation_run_id", "created_at",
    ],
}

# Parents before children, so foreign keys are satisfied on load.
LOAD_ORDER = [
    "users", "claimants", "providers", "policies", "incidents", "claims",
    "invoices", "payments", "relationship_edges",
    "claim_status_events", "payment_status_events", "ground_truth",
]

# Timestamps taken from the wall clock. Excluded from checksums unless
# time was frozen during generation (see main.py).
VOLATILE_COLUMNS = {"created_at", "updated_at"}


def _format(value) -> str:
    """Convert a Python value to a CSV cell. None becomes an empty cell."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def stable_checksum(path: Path, ignore_columns: set[str]) -> str:
    """SHA-256 of a CSV's content, optionally ignoring some columns."""
    digest = hashlib.sha256()

    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        keep = [i for i, name in enumerate(header) if name not in ignore_columns]

        digest.update(",".join(header[i] for i in keep).encode())
        for row in reader:
            digest.update(b"\n")
            digest.update("\x1f".join(row[i] for i in keep).encode())

    return digest.hexdigest()


def write_table(
    name: str,
    rows: list[dict],
    directory: Path,
    ignore_columns: set[str] | None = None,
) -> dict:
    """Write one table to <directory>/<name>.csv and return its manifest entry."""
    if name not in TABLE_COLUMNS:
        raise KeyError(f"Unknown table: {name}")

    columns = TABLE_COLUMNS[name]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.csv"

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            # Strict lookup: a missing key fails loudly instead of
            # silently becoming NULL.
            writer.writerow([_format(row[column]) for column in columns])

    return {
        "path": str(path),
        "rows": len(rows),
        "sha256": stable_checksum(path, ignore_columns or set()),
    }


def export_tables(
    datasets: dict[str, list[dict]],
    directory: Path,
    ignore_columns: set[str] | None = None,
) -> dict[str, dict]:
    """Write every dataset (in load order) and return manifest entries."""
    return {
        name: write_table(name, datasets[name], directory, ignore_columns)
        for name in LOAD_ORDER
        if name in datasets
    }


def dataset_checksum(files: dict[str, dict]) -> str:
    """One checksum covering every file, for the reproducibility proof."""
    combined = "\n".join(f"{name}:{files[name]['sha256']}" for name in sorted(files))
    return hashlib.sha256(combined.encode()).hexdigest()


def write_manifest(out_dir: Path, manifest: dict) -> Path:
    """Write manifest.json (seed, counts, per-file checksums, command)."""
    path = out_dir / "manifest.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True, default=str)
    return path