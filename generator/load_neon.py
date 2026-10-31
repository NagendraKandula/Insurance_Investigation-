"""
Load the exported CSV files into Neon (PostgreSQL).

Reads DATABASE_URL from .env, e.g.
    DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

Everything loads in ONE transaction: if any table fails, nothing is kept.
"""

import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

from generator.export import LOAD_ORDER, TABLE_COLUMNS

CHUNK_SIZE = 1024 * 1024  # 1 MB


def _csv_path(out_dir: Path, table: str) -> Path:
    # Ground truth is kept apart from the input data.
    folder = "ground_truth" if table == "ground_truth" else "data"
    return out_dir / folder / f"{table}.csv"


def _copy_table(cur: psycopg.Cursor, table: str, path: Path) -> None:
    columns = ", ".join(TABLE_COLUMNS[table])
    statement = (
        f"COPY {table} ({columns}) FROM STDIN "
        "WITH (FORMAT csv, HEADER true)"
    )
    with open(path, "rb") as handle, cur.copy(statement) as copy:
        while chunk := handle.read(CHUNK_SIZE):
            copy.write(chunk)


def _insert_run_record(cur: psycopg.Cursor, manifest: dict) -> None:
    counts = manifest["row_counts"]
    cur.execute(
        """
        INSERT INTO data_generation_runs (
            generation_run_id, random_seed, configuration, generator_version,
            total_claimants, total_policies, total_claims, total_providers,
            total_edges, dataset_checksum, started_at, completed_at, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            manifest["generation_run_id"],
            manifest["seed"],
            Jsonb(manifest["configuration"]),
            manifest["generator_version"],
            counts["claimants"],
            counts["policies"],
            counts["claims"],
            counts["providers"],
            counts["relationship_edges"],
            manifest["dataset_checksum"],
            manifest["run_started_at"],
            manifest["run_completed_at"],
            "COMPLETED",
        ),
    )


def load_into_neon(out_dir: Path, truncate: bool = False) -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set. Add it to your .env file.")

    out_dir = Path(out_dir)
    with open(out_dir / "manifest.json", encoding="utf-8") as handle:
        manifest = json.load(handle)

    tables = [t for t in LOAD_ORDER if _csv_path(out_dir, t).exists()]

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:

            if truncate:
                names = ", ".join(tables + ["data_generation_runs"])
                print("Truncating (CASCADE also clears tables that reference these).")
                cur.execute(f"TRUNCATE {names} RESTART IDENTITY CASCADE")
            else:
                for table in tables:
                    cur.execute(f"SELECT count(*) FROM {table}")
                    if cur.fetchone()[0] > 0:
                        raise SystemExit(
                            f"Table {table} already has data. "
                            "Re-run with --truncate to replace it."
                        )

            for table in tables:
                _copy_table(cur, table, _csv_path(out_dir, table))
                print(f"Loaded {table}")

            _insert_run_record(cur, manifest)

            # Compare the database against the manifest before committing.
            mismatches = []
            for table in tables:
                cur.execute(f"SELECT count(*) FROM {table}")
                in_db = cur.fetchone()[0]
                expected = manifest["row_counts"][table]
                if in_db != expected:
                    mismatches.append(f"{table}: file={expected} db={in_db}")

            if mismatches:
                raise SystemExit(
                    "Row count mismatch, rolling back:\n  " + "\n  ".join(mismatches)
                )

        conn.commit()

    print("\nLoad complete. Row counts match the manifest.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load generated CSVs into Neon")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--truncate", action="store_true")
    args = parser.parse_args()

    load_into_neon(args.output_dir, truncate=args.truncate)