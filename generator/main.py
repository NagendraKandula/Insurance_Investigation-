"""
Orchestrate the full synthetic-data pipeline.

Examples (run from the project root):

    python -m generator.main --scale starter
    python -m generator.main --scale full --load-neon
    python -m generator.main --scale full --repro-check
"""

import argparse
import sys
from contextlib import nullcontext
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from generator.claim_generator import ClaimGenerator
from generator.claimant_generator import ClaimantGenerator
from generator.config import fake
from generator.export import (
    VOLATILE_COLUMNS,
    dataset_checksum,
    export_tables,
    write_manifest,
)
from generator.ground_truth_writer import (
    assert_no_leakage,
    finalize_ground_truth,
    summarize,
    validate_ground_truth,
    write_ground_truth,
)
from generator.id_generator import IDGenerator
from generator.incident_generator import IncidentGenerator
from generator.invoice_generator import InvoiceGenerator
from generator.pattern_injector import PatternInjector
from generator.payment_generator import PaymentGenerator
from generator.policy_generator import PolicyGenerator
from generator.provider_generator import ProviderGenerator
from generator.relationship_generator import RelationshipEdgeGenerator

try:
    from freezegun import freeze_time
except ImportError:  # optional, see README note on reproducibility
    freeze_time = None

SEED = 20261031
REFERENCE_DATE = "2026-10-31"
REFERENCE_DT = datetime(2026, 10, 31, 23, 59, tzinfo=timezone.utc)
GENERATOR_VERSION = "0.1.0"

SCALES = {
    # Same generator, different volume.
    "starter": {
        "users": 12, "claimants": 600, "providers": 250, "policies": 900,
        "incidents": 1200, "claims": 900, "invoices": 250,
        "payments": 400, "edges": 8000,
    },
    "full": {
        "users": 20, "claimants": 2000, "providers": 500, "policies": 3000,
        "incidents": 4000, "claims": 5000, "invoices": 6000,
        "payments": 8000, "edges": 8000,
    },
}


# --------------------------------------------------
# Users (analysts, reviewers, admins)
# --------------------------------------------------

def build_users(count: int) -> list[dict]:
    """Mostly analysts, some reviewers, a couple of admins."""
    if count < 3:
        raise ValueError("Need at least 3 users (one per role).")

    admins = max(1, count // 10)
    reviewers = max(1, count // 4)

    users = []
    for number in range(1, count + 1):
        if number <= admins:
            role = "ADMIN"
        elif number <= admins + reviewers:
            role = "REVIEWER"
        else:
            role = "ANALYST"

        first, last = fake.first_name(), fake.last_name()
        users.append({
            "user_id": f"USR-{number:06d}",
            "full_name": f"{first} {last}",
            # The number keeps the unique email constraint safe.
            "email": f"{first.lower()}.{last.lower()}{number}@insurer.example",
            "role": role,
            # Every 10th user is inactive, so the status column has variety.
            "status": "INACTIVE" if number % 10 == 0 else "ACTIVE",
            "created_at": datetime.now(timezone.utc),
        })

    return users


# --------------------------------------------------
# Status history (derived from final status, never random)
# --------------------------------------------------

CLAIM_PATH = ["PENDING", "UNDER_REVIEW"]


def _to_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time(9, 0), tzinfo=timezone.utc)
    raise TypeError(f"Cannot convert {value!r} to datetime")


def _event(key: str, entity_id: str, from_status, to_status, when, remarks,
           actor_id=None):
    return {
        key: entity_id,
        "from_status": from_status,
        "to_status": to_status,
        "event_time": min(when, REFERENCE_DT),
        "actor_id": actor_id,
        "remarks": remarks,
    }


def build_claim_events(claims: list[dict], users: list[dict]) -> list[dict]:
    """
    PENDING -> UNDER_REVIEW -> APPROVED/REJECTED, ending at the claim's status.

    Submission has no actor (the customer or system). Review is done by an
    active analyst and the final decision by an active reviewer, picked by
    position so the result is deterministic.
    """
    analysts = [u["user_id"] for u in users
                if u["role"] == "ANALYST" and u["status"] == "ACTIVE"]
    reviewers = [u["user_id"] for u in users
                 if u["role"] == "REVIEWER" and u["status"] == "ACTIVE"]
    if not analysts or not reviewers:
        raise ValueError("Need an active analyst and an active reviewer.")

    events = []

    for index, claim in enumerate(claims):
        submitted = _to_datetime(claim["claim_date"])
        final = claim["status"]

        chain = [None, "PENDING"]
        if final in ("UNDER_REVIEW", "APPROVED", "REJECTED"):
            chain.append("UNDER_REVIEW")
        if final in ("APPROVED", "REJECTED"):
            chain.append(final)

        for step in range(1, len(chain)):
            if chain[step] == "PENDING":
                actor = None
            elif chain[step] == "UNDER_REVIEW":
                actor = analysts[index % len(analysts)]
            else:
                actor = reviewers[index % len(reviewers)]

            events.append(
                _event(
                    "claim_id", claim["claim_id"], chain[step - 1], chain[step],
                    submitted + timedelta(days=2 * (step - 1)),
                    "Generated from final claim status",
                    actor,
                )
            )

    return events


def build_payment_events(payments: list[dict]) -> list[dict]:
    return [
        _event(
            "payment_id", payment["payment_id"], None, payment["status"],
            _to_datetime(payment["payment_date"]),
            "Generated from final payment status",
        )
        for payment in payments
    ]


# --------------------------------------------------
# Generation
# --------------------------------------------------

def build_dataset(seed: int, counts: dict) -> tuple[dict, list[dict]]:
    """Generate every table in dependency order. Returns (datasets, ground_truth)."""
    # Re-seed everything so repeated runs are identical.
    fake.seed_instance(seed)
    fake.unique.clear()

    ids = IDGenerator()

    claimants = ClaimantGenerator(ids).generate_claimants(counts["claimants"])
    providers = ProviderGenerator(ids).generate_providers(counts["providers"])
    policies = PolicyGenerator(ids).generate_policies(claimants, counts["policies"])
    incidents = IncidentGenerator(ids).generate_incidents(counts["incidents"])
    claims = ClaimGenerator(ids).generate_claims(
        claimants, policies, incidents, counts["claims"]
    )
    invoices = InvoiceGenerator(ids).generate_invoices(
        claims, providers, counts["invoices"]
    )
    payments = PaymentGenerator(ids).generate_payments(invoices, counts["payments"])

    # Inject BEFORE building edges: the injector edits records in place
    # and the edges must reflect the final data.
    injector = PatternInjector(ids, seed=seed)
    ground_truth = injector.inject_all_patterns(
        claimants=claimants, claims=claims, providers=providers, invoices=invoices
    )

    edges = RelationshipEdgeGenerator().generate_edges(
        claimants, policies, incidents, claims, providers, invoices, payments
    )

    # Created last so adding users does not change any other table's values.
    users = build_users(counts["users"])

    datasets = {
        "users": users,
        "claimants": claimants,
        "providers": providers,
        "policies": policies,
        "incidents": incidents,
        "claims": claims,
        "invoices": invoices,
        "payments": payments,
        "relationship_edges": edges,
        "claim_status_events": build_claim_events(claims, users),
        "payment_status_events": build_payment_events(payments),
    }

    return datasets, ground_truth


def sanity_check(datasets: dict) -> list[str]:
    """Quick PK and FK integrity check. Full checks belong in validate.py."""
    problems = []

    pk = {
        "users": "user_id", "claimants": "claimant_id", "providers": "provider_id",
        "policies": "policy_id", "incidents": "incident_id",
        "claims": "claim_id", "invoices": "invoice_id",
        "payments": "payment_id",
    }
    ids = {}
    for table, field in pk.items():
        values = [row[field] for row in datasets[table]]
        ids[table] = set(values)
        if len(values) != len(ids[table]):
            problems.append(f"{table}: duplicate primary keys")

    fks = [
        ("policies", "claimant_id", "claimants"),
        ("claims", "claimant_id", "claimants"),
        ("claims", "policy_id", "policies"),
        ("claims", "incident_id", "incidents"),
        ("invoices", "provider_id", "providers"),
        ("invoices", "claim_id", "claims"),
        ("payments", "invoice_id", "invoices"),
        ("claim_status_events", "claim_id", "claims"),
        ("payment_status_events", "payment_id", "payments"),
    ]
    for table, column, parent in fks:
        bad = sum(1 for row in datasets[table] if row[column] not in ids[parent])
        if bad:
            problems.append(f"{table}.{column}: {bad} orphan rows")

    # actor_id is optional, but when present it must be a real user.
    for table in ("claim_status_events", "payment_status_events"):
        bad = sum(1 for row in datasets[table]
                  if row["actor_id"] is not None and row["actor_id"] not in ids["users"])
        if bad:
            problems.append(f"{table}.actor_id: {bad} unknown users")

    endpoint_ids = {
        "CLAIMANT": ids["claimants"], "POLICY": ids["policies"],
        "INCIDENT": ids["incidents"], "CLAIM": ids["claims"],
        "PROVIDER": ids["providers"], "INVOICE": ids["invoices"],
        "PAYMENT": ids["payments"],
    }
    bad_edges = sum(
        1
        for edge in datasets["relationship_edges"]
        if edge["source_id"] not in endpoint_ids.get(edge["source_type"], set())
        or edge["target_id"] not in endpoint_ids.get(edge["target_type"], set())
    )
    if bad_edges:
        problems.append(f"relationship_edges: {bad_edges} edges with missing endpoints")

    return problems


# --------------------------------------------------
# One full run: generate, validate, export
# --------------------------------------------------

def run_pipeline(seed: int, scale: str, out_dir: Path) -> dict:
    counts = SCALES[scale]
    started_at = datetime.now(timezone.utc)

    # Freeze the clock so created_at and "today" are identical across runs.
    frozen = freeze_time is not None
    clock = freeze_time(REFERENCE_DATE) if frozen else nullcontext()

    with clock:
        datasets, raw_ground_truth = build_dataset(seed, counts)

    run_id = f"RUN-{seed}"
    ground_truth = finalize_ground_truth(raw_ground_truth, run_id)

    problems = sanity_check(datasets)
    problems += validate_ground_truth(ground_truth, datasets)
    assert_no_leakage(datasets)

    if problems:
        print("\nValidation FAILED:")
        for problem in problems[:20]:
            print(f"  - {problem}")
        raise SystemExit(1)

    ignore = set() if frozen else VOLATILE_COLUMNS

    files = export_tables(datasets, out_dir / "data", ignore)
    # Ground truth lives in its own directory, away from the input data.
    files["ground_truth"] = write_ground_truth(
        ground_truth, out_dir / "ground_truth", ignore
    )

    manifest = {
        "generation_run_id": run_id,
        "generator_version": GENERATOR_VERSION,
        "generator_command": f"python -m generator.main --scale {scale} --seed {seed}",
        "seed": seed,
        "scale": scale,
        "configuration": counts,
        "time_frozen": frozen,
        "run_started_at": started_at.isoformat(),
        "run_completed_at": datetime.now(timezone.utc).isoformat(),
        "row_counts": {name: info["rows"] for name, info in files.items()},
        "files": files,
        "dataset_checksum": dataset_checksum(files),
        "ground_truth_summary": summarize(ground_truth),
    }
    write_manifest(out_dir, manifest)
    return manifest


def print_summary(manifest: dict) -> None:
    print("\n========== GENERATION SUMMARY ==========")
    print(f"Seed: {manifest['seed']}   Scale: {manifest['scale']}   "
          f"Time frozen: {manifest['time_frozen']}")
    for name, rows in manifest["row_counts"].items():
        print(f"  {name:<24}{rows:>8}")

    target = manifest["configuration"]["edges"]
    actual = manifest["row_counts"]["relationship_edges"]
    if actual != target:
        print(f"\nNOTE: {actual} edges generated vs. target {target}. "
              "The foreign-key edges alone exceed the target; "
              "decide which edge types count toward it.")

    print("\nGround truth:", manifest["ground_truth_summary"])
    print(f"Dataset checksum: {manifest['dataset_checksum']}")


def repro_check(seed: int, scale: str, out_dir: Path) -> bool:
    """Generate twice with the same seed and compare row counts and checksums."""
    first = run_pipeline(seed, scale, out_dir / "repro_run_1")
    second = run_pipeline(seed, scale, out_dir / "repro_run_2")

    print("\n========== REPRODUCIBILITY CHECK ==========")
    all_match = True
    for name in first["files"]:
        same_rows = first["files"][name]["rows"] == second["files"][name]["rows"]
        same_hash = first["files"][name]["sha256"] == second["files"][name]["sha256"]
        all_match &= same_rows and same_hash
        print(f"  {name:<24}rows {'OK' if same_rows else 'DIFF'}   "
              f"checksum {'OK' if same_hash else 'DIFF'}")

    print(f"\nRun 1: {first['dataset_checksum']}")
    print(f"Run 2: {second['dataset_checksum']}")
    print("RESULT:", "REPRODUCIBLE" if all_match else "NOT REPRODUCIBLE")
    return all_match


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthetic fraud-data generator")
    parser.add_argument("--scale", choices=SCALES, default="starter")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--repro-check", action="store_true",
                        help="Generate twice and compare checksums")
    parser.add_argument("--load-neon", action="store_true",
                        help="Load the exported CSVs into Neon after generating")
    parser.add_argument("--truncate", action="store_true",
                        help="With --load-neon: empty the tables first")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.repro_check:
        ok = repro_check(args.seed, args.scale, args.output_dir)
        sys.exit(0 if ok else 1)

    manifest = run_pipeline(args.seed, args.scale, args.output_dir)
    print_summary(manifest)
    print(f"\nFiles written to: {args.output_dir.resolve()}")

    if args.load_neon:
        from generator.load_neon import load_into_neon
        load_into_neon(args.output_dir, truncate=args.truncate)


if __name__ == "__main__":
    main()