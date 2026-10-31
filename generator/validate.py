"""
Validate the loaded database (Step 8 of the challenge).

Run from the project root:

    python -m generator.validate
    python -m generator.validate --strict          # also fail on findings
    python -m generator.validate --as-of 2026-10-31

This script is deliberately independent of the generator. It reads only the
source tables, never ground_truth, so what it reports is what a real
validator would discover on its own.

Three kinds of check:
  integrity  must be zero. Broken keys, enums, dates, lifecycle, arithmetic.
             Any failure makes the script exit with code 1.
  finding    business-rule violations. These are the anomalies the system is
             meant to surface (planted ones are expected to show up here).
             They are reported but do not fail the run unless --strict.
  info       signals and counts for context (shared contacts and so on).

Read-only: nothing is written to the database.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv

SAMPLE_SIZE = 5


@dataclass
class Check:
    check_id: str
    section: str
    kind: str          # integrity | finding | info
    description: str
    sql: str           # returns one column: the offending id or key


# ----------------------------------------------------------------------
# Reusable pieces
# ----------------------------------------------------------------------

NET_PAID = (
    "SUM(CASE WHEN transaction_type = 'PAYMENT' "
    "THEN payment_amount ELSE -payment_amount END)"
)

ENTITIES_CTE = """
WITH ent(t, id) AS (
    SELECT 'CLAIMANT', claimant_id FROM claimants UNION ALL
    SELECT 'PROVIDER', provider_id FROM providers UNION ALL
    SELECT 'POLICY', policy_id FROM policies UNION ALL
    SELECT 'INCIDENT', incident_id FROM incidents UNION ALL
    SELECT 'CLAIM', claim_id FROM claims UNION ALL
    SELECT 'INVOICE', invoice_id FROM invoices UNION ALL
    SELECT 'PAYMENT', payment_id FROM payments
)
"""

# Allowed values, matching the data dictionary and the generators.
ENUMS = {
    ("users", "role", "user_id"): ["ANALYST", "REVIEWER", "ADMIN"],
    ("users", "status", "user_id"): ["ACTIVE", "INACTIVE"],
    ("claimants", "gender", "claimant_id"): ["Male", "Female", "Other"],
    ("policies", "policy_type", "policy_id"):
        ["HEALTH", "MOTOR", "HOME", "LIFE", "TRAVEL"],
    ("policies", "status", "policy_id"): ["ACTIVE", "EXPIRED", "CANCELLED"],
    ("incidents", "incident_type", "incident_id"):
        ["VEHICLE_ACCIDENT", "FIRE", "THEFT", "MEDICAL",
         "PROPERTY_DAMAGE", "NATURAL_DISASTER"],
    ("providers", "provider_type", "provider_id"):
        ["HOSPITAL", "CLINIC", "GARAGE", "AUTO_REPAIR", "PHARMACY",
         "DIAGNOSTIC_CENTER", "CONSTRUCTION", "LEGAL_SERVICE"],
    ("providers", "status", "provider_id"): ["ACTIVE", "INACTIVE"],
    ("claims", "status", "claim_id"):
        ["PENDING", "UNDER_REVIEW", "APPROVED", "REJECTED"],
    ("invoices", "status", "invoice_id"):
        ["SUBMITTED", "PENDING", "PAID", "REJECTED"],
    ("payments", "payment_method", "payment_id"):
        ["BANK_TRANSFER", "UPI", "CREDIT_CARD", "DEBIT_CARD", "CHEQUE"],
    ("payments", "transaction_type", "payment_id"):
        ["PAYMENT", "REFUND", "REVERSAL"],
    ("payments", "status", "payment_id"):
        ["PENDING", "COMPLETED", "FAILED", "REVERSED"],
    ("relationship_edges", "relationship_type", "edge_id"):
        ["OWNS_POLICY", "FILED_CLAIM", "COVERS_CLAIM", "REPORTED_IN_CLAIM",
         "ISSUED_INVOICE", "HAS_INVOICE", "HAS_PAYMENT",
         "SHARES_PHONE", "SHARES_EMAIL", "SHARES_ADDRESS"],
    ("relationship_edges", "source_type", "edge_id"):
        ["CLAIMANT", "PROVIDER", "POLICY", "INCIDENT", "CLAIM",
         "INVOICE", "PAYMENT"],
    ("relationship_edges", "target_type", "edge_id"):
        ["CLAIMANT", "PROVIDER", "POLICY", "INCIDENT", "CLAIM",
         "INVOICE", "PAYMENT"],
}

# Allowed lifecycle transitions: (from_status, to_status).
CLAIM_TRANSITIONS = [
    (None, "PENDING"),
    ("PENDING", "UNDER_REVIEW"),
    ("PENDING", "REJECTED"),
    ("UNDER_REVIEW", "APPROVED"),
    ("UNDER_REVIEW", "REJECTED"),
]
PAYMENT_TRANSITIONS = [
    (None, "PENDING"),
    (None, "COMPLETED"),
    ("PENDING", "COMPLETED"),
    ("PENDING", "FAILED"),
    ("COMPLETED", "REVERSED"),
]

ROW_COUNT_TABLES = [
    "users", "claimants", "providers", "policies", "incidents", "claims",
    "invoices", "payments", "relationship_edges",
    "claim_status_events", "payment_status_events",
]


def _values(pairs):
    rows = []
    for frm, to in pairs:
        left = "NULL::text" if frm is None else f"'{frm}'::text"
        rows.append(f"({left}, '{to}'::text)")
    return ", ".join(rows)


def pk_unique(table, column):
    return Check(
        f"KEY-{table}-{column}", "Keys", "integrity",
        f"{table}.{column} is unique",
        f"SELECT {column} FROM {table} GROUP BY {column} HAVING count(*) > 1",
    )


def fk_orphans(child, child_pk, column, parent, parent_pk, nullable=False):
    extra = f" AND c.{column} IS NOT NULL" if nullable else ""
    return Check(
        f"FK-{child}-{column}", "Foreign keys", "integrity",
        f"{child}.{column} points to an existing {parent}",
        f"SELECT c.{child_pk} FROM {child} c "
        f"LEFT JOIN {parent} p ON p.{parent_pk} = c.{column} "
        f"WHERE p.{parent_pk} IS NULL{extra}",
    )


def enum_check(table, column, pk, allowed):
    quoted = ", ".join(f"'{v}'" for v in allowed)
    return Check(
        f"ENUM-{table}-{column}", "Allowed values", "integrity",
        f"{table}.{column} is one of the allowed values",
        f"SELECT {pk} FROM {table} "
        f"WHERE {column} IS NULL OR {column} NOT IN ({quoted})",
    )


def lifecycle_checks(events, key, parent, parent_pk, transitions, label):
    values = _values(transitions)
    return [
        Check(
            f"LIFE-{events}-transition", "Lifecycle", "integrity",
            f"{label} events use only allowed transitions",
            f"SELECT e.event_id FROM {events} e WHERE NOT EXISTS ("
            f"SELECT 1 FROM (VALUES {values}) a(f, t) "
            f"WHERE a.f IS NOT DISTINCT FROM e.from_status "
            f"AND a.t = e.to_status)",
        ),
        Check(
            f"LIFE-{events}-chain", "Lifecycle", "integrity",
            f"{label} events form an unbroken chain "
            f"(each from_status equals the previous to_status)",
            f"SELECT event_id FROM ("
            f"SELECT event_id, from_status, "
            f"lag(to_status) OVER (PARTITION BY {key} ORDER BY event_id) AS prev "
            f"FROM {events}) t WHERE from_status IS DISTINCT FROM prev",
        ),
        Check(
            f"LIFE-{events}-final", "Lifecycle", "integrity",
            f"Latest {label} event matches the current status "
            f"(and every record has history)",
            f"SELECT p.{parent_pk} FROM {parent} p LEFT JOIN ("
            f"SELECT DISTINCT ON ({key}) {key}, to_status FROM {events} "
            f"ORDER BY {key}, event_id DESC) l ON l.{key} = p.{parent_pk} "
            f"WHERE l.to_status IS DISTINCT FROM p.status",
        ),
        Check(
            f"LIFE-{events}-time", "Lifecycle", "integrity",
            f"{label} event times never go backwards",
            f"SELECT event_id FROM ("
            f"SELECT event_id, event_time, "
            f"lag(event_time) OVER (PARTITION BY {key} ORDER BY event_id) AS prev "
            f"FROM {events}) t WHERE event_time < prev",
        ),
    ]


# ----------------------------------------------------------------------
# The checks
# ----------------------------------------------------------------------

def build_checks() -> list[Check]:
    checks: list[Check] = []

    # --- Keys -----------------------------------------------------------
    for table, column in [
        ("users", "user_id"), ("users", "email"),
        ("claimants", "claimant_id"), ("providers", "provider_id"),
        ("providers", "registration_number"), ("policies", "policy_id"),
        ("policies", "policy_number"), ("incidents", "incident_id"),
        ("claims", "claim_id"), ("claims", "claim_number"),
        ("invoices", "invoice_id"), ("payments", "payment_id"),
        ("payments", "transaction_reference"),
    ]:
        checks.append(pk_unique(table, column))

    # --- Foreign keys ---------------------------------------------------
    for args in [
        ("policies", "policy_id", "claimant_id", "claimants", "claimant_id"),
        ("claims", "claim_id", "claimant_id", "claimants", "claimant_id"),
        ("claims", "claim_id", "policy_id", "policies", "policy_id"),
        ("claims", "claim_id", "incident_id", "incidents", "incident_id"),
        ("invoices", "invoice_id", "provider_id", "providers", "provider_id"),
        ("invoices", "invoice_id", "claim_id", "claims", "claim_id"),
        ("payments", "payment_id", "invoice_id", "invoices", "invoice_id"),
        ("claim_status_events", "event_id", "claim_id", "claims", "claim_id"),
        ("payment_status_events", "event_id", "payment_id", "payments", "payment_id"),
    ]:
        checks.append(fk_orphans(*args))

    for events in ("claim_status_events", "payment_status_events"):
        checks.append(
            fk_orphans(events, "event_id", "actor_id", "users", "user_id", nullable=True)
        )

    checks.append(Check(
        "FK-claims-owner", "Foreign keys", "integrity",
        "Claim's claimant is the owner of the claim's policy",
        "SELECT c.claim_id FROM claims c JOIN policies p USING (policy_id) "
        "WHERE c.claimant_id <> p.claimant_id",
    ))

    # --- Graph edges ----------------------------------------------------
    checks += [
        Check(
            "GRAPH-source-exists", "Graph edges", "integrity",
            "Every edge source exists in its own entity table",
            ENTITIES_CTE + "SELECT e.edge_id FROM relationship_edges e "
            "LEFT JOIN ent s ON s.t = e.source_type AND s.id = e.source_id "
            "WHERE s.id IS NULL",
        ),
        Check(
            "GRAPH-target-exists", "Graph edges", "integrity",
            "Every edge target exists in its own entity table",
            ENTITIES_CTE + "SELECT e.edge_id FROM relationship_edges e "
            "LEFT JOIN ent s ON s.t = e.target_type AND s.id = e.target_id "
            "WHERE s.id IS NULL",
        ),
        Check(
            "GRAPH-duplicates", "Graph edges", "integrity",
            "No duplicate edges (same source, target and relationship type)",
            "SELECT source_id || '>' || target_id FROM relationship_edges "
            "GROUP BY source_type, source_id, target_type, target_id, "
            "relationship_type HAVING count(*) > 1",
        ),
        Check(
            "GRAPH-self-loops", "Graph edges", "integrity",
            "No edge points from an entity to itself",
            "SELECT edge_id FROM relationship_edges "
            "WHERE source_type = target_type AND source_id = target_id",
        ),
        Check(
            "GRAPH-claim-edge", "Graph edges", "finding",
            "Every claim has a FILED_CLAIM edge from its claimant",
            "SELECT c.claim_id FROM claims c WHERE NOT EXISTS ("
            "SELECT 1 FROM relationship_edges e "
            "WHERE e.relationship_type = 'FILED_CLAIM' "
            "AND e.source_id = c.claimant_id AND e.target_id = c.claim_id)",
        ),
        Check(
            "GRAPH-invoice-edge", "Graph edges", "finding",
            "Every invoice has an ISSUED_INVOICE edge from its provider",
            "SELECT i.invoice_id FROM invoices i WHERE NOT EXISTS ("
            "SELECT 1 FROM relationship_edges e "
            "WHERE e.relationship_type = 'ISSUED_INVOICE' "
            "AND e.source_id = i.provider_id AND e.target_id = i.invoice_id)",
        ),
    ]

    # --- Allowed values -------------------------------------------------
    for (table, column, pk), allowed in ENUMS.items():
        checks.append(enum_check(table, column, pk, allowed))

    # --- Dates ----------------------------------------------------------
    checks += [
        Check("DATE-incident-reported", "Dates", "integrity",
              "Incident is reported on or after the day it happened",
              "SELECT incident_id FROM incidents WHERE reported_at < incident_date"),
        Check("DATE-claim-after-report", "Dates", "integrity",
              "Claim is filed on or after the incident was reported",
              "SELECT c.claim_id FROM claims c JOIN incidents i USING (incident_id) "
              "WHERE c.claim_date::date < i.reported_at::date"),
        Check("DATE-claim-in-policy", "Dates", "integrity",
              "Incident falls within the policy's coverage period",
              "SELECT c.claim_id FROM claims c JOIN policies p USING (policy_id) "
              "JOIN incidents i USING (incident_id) "
              "WHERE i.incident_date::date < p.start_date "
              "OR i.incident_date::date > p.end_date"),
        Check("DATE-policy-range", "Dates", "integrity",
              "Policy ends on or after it starts",
              "SELECT policy_id FROM policies WHERE end_date < start_date"),
        Check("DATE-invoice-after-claim", "Dates", "integrity",
              "Invoice is dated on or after its claim",
              "SELECT i.invoice_id FROM invoices i JOIN claims c USING (claim_id) "
              "WHERE i.invoice_date::date < c.claim_date::date"),
        Check("DATE-invoice-due", "Dates", "integrity",
              "Invoice due date is on or after the invoice date",
              "SELECT invoice_id FROM invoices "
              "WHERE due_date IS NOT NULL AND due_date < invoice_date::date"),
        Check("DATE-payment-after-invoice", "Dates", "integrity",
              "Payment is dated on or after its invoice",
              "SELECT p.payment_id FROM payments p JOIN invoices i USING (invoice_id) "
              "WHERE p.payment_date::date < i.invoice_date::date"),
        Check("DATE-refund-after-payment", "Dates", "integrity",
              "Refund or reversal comes after a payment on the same invoice",
              "SELECT r.payment_id FROM payments r "
              "WHERE r.transaction_type IN ('REFUND', 'REVERSAL') AND NOT EXISTS ("
              "SELECT 1 FROM payments p WHERE p.invoice_id = r.invoice_id "
              "AND p.transaction_type = 'PAYMENT' AND p.payment_date <= r.payment_date)"),
        Check("DATE-not-future", "Dates", "integrity",
              "No business date is after the as-of date",
              "SELECT x FROM ("
              "SELECT claim_id AS x FROM claims WHERE claim_date::date > %(as_of)s::date "
              "UNION ALL SELECT invoice_id FROM invoices "
              "WHERE invoice_date::date > %(as_of)s::date "
              "UNION ALL SELECT payment_id FROM payments "
              "WHERE payment_date::date > %(as_of)s::date "
              "UNION ALL SELECT policy_id FROM policies "
              "WHERE start_date > %(as_of)s::date) t"),
        Check("DATE-adult", "Dates", "integrity",
              "Claimants are at least 18 at the as-of date",
              "SELECT claimant_id FROM claimants "
              "WHERE date_of_birth > (%(as_of)s::date - INTERVAL '18 years')"),
    ]

    # --- Arithmetic -----------------------------------------------------
    checks += [
        Check("MATH-approved-le-claimed", "Arithmetic", "integrity",
              "Approved amount never exceeds the claimed amount",
              "SELECT claim_id FROM claims WHERE approved_amount > claim_amount"),
        Check("MATH-claim-le-coverage", "Arithmetic", "integrity",
              "Claimed amount never exceeds the policy coverage",
              "SELECT c.claim_id FROM claims c JOIN policies p USING (policy_id) "
              "WHERE c.claim_amount > p.coverage_amount"),
        Check("MATH-approved-consistent", "Arithmetic", "integrity",
              "Approved amount is positive exactly when the claim is APPROVED",
              "SELECT claim_id FROM claims WHERE "
              "(status = 'APPROVED' AND COALESCE(approved_amount, 0) <= 0) OR "
              "(status <> 'APPROVED' AND COALESCE(approved_amount, 0) > 0)"),
        Check("MATH-premium", "Arithmetic", "integrity",
              "Premium equals 2% of coverage (derived value)",
              "SELECT policy_id FROM policies "
              "WHERE abs(premium_amount - round(coverage_amount * 0.02, 2)) > 0.01"),
        Check("MATH-payment-le-invoice", "Arithmetic", "integrity",
              "No single transaction exceeds its invoice amount",
              "SELECT p.payment_id FROM payments p JOIN invoices i USING (invoice_id) "
              "WHERE p.payment_amount > i.invoice_amount"),
        Check("MATH-net-paid-range", "Arithmetic", "integrity",
              "Net paid per invoice (payments minus refunds and reversals) "
              "stays between 0 and the invoice amount",
              "SELECT i.invoice_id FROM invoices i JOIN ("
              f"SELECT invoice_id, {NET_PAID} AS net FROM payments GROUP BY invoice_id"
              ") p USING (invoice_id) WHERE p.net < 0 OR p.net > i.invoice_amount"),
    ]

    # --- Lifecycle ------------------------------------------------------
    checks += lifecycle_checks(
        "claim_status_events", "claim_id", "claims", "claim_id",
        CLAIM_TRANSITIONS, "Claim")
    checks += lifecycle_checks(
        "payment_status_events", "payment_id", "payments", "payment_id",
        PAYMENT_TRANSITIONS, "Payment")

    # --- Business rules (findings) --------------------------------------
    checks += [
        Check("BIZ-payment-exceeds-approved", "Business rules", "finding",
              "Net payments on a claim exceed its approved amount",
              "SELECT c.claim_id FROM claims c "
              "JOIN invoices i ON i.claim_id = c.claim_id "
              "JOIN payments p ON p.invoice_id = i.invoice_id "
              f"GROUP BY c.claim_id, c.approved_amount "
              f"HAVING {NET_PAID} > COALESCE(c.approved_amount, 0)"),
        Check("BIZ-invoices-exceed-claim", "Business rules", "finding",
              "Invoices on a claim add up to more than the claimed amount",
              "SELECT c.claim_id FROM claims c JOIN invoices i USING (claim_id) "
              "GROUP BY c.claim_id, c.claim_amount "
              "HAVING SUM(i.invoice_amount) > c.claim_amount"),
        Check("BIZ-invoice-unapproved-claim", "Business rules", "finding",
              "Invoice raised against a claim that is not APPROVED",
              "SELECT i.invoice_id FROM invoices i JOIN claims c USING (claim_id) "
              "WHERE c.status <> 'APPROVED'"),
        Check("BIZ-paid-not-settled", "Business rules", "finding",
              "Invoice marked PAID but net payments are below the invoice amount",
              "SELECT i.invoice_id FROM invoices i LEFT JOIN ("
              f"SELECT invoice_id, {NET_PAID} AS net FROM payments GROUP BY invoice_id"
              ") p USING (invoice_id) "
              "WHERE i.status = 'PAID' AND COALESCE(p.net, 0) < i.invoice_amount"),
        Check("BIZ-rejected-but-paid", "Business rules", "finding",
              "Invoice marked REJECTED but money was paid out",
              "SELECT i.invoice_id FROM invoices i JOIN ("
              f"SELECT invoice_id, {NET_PAID} AS net FROM payments GROUP BY invoice_id"
              ") p USING (invoice_id) WHERE i.status = 'REJECTED' AND p.net > 0"),
        Check("BIZ-invoice-number-repeats", "Business rules", "finding",
              "Same provider repeats an invoice number",
              "SELECT provider_id || '/' || invoice_number FROM invoices "
              "GROUP BY provider_id, invoice_number HAVING count(*) > 1"),
        Check("BIZ-duplicate-invoice-cross-claimant", "Business rules", "finding",
              "Same invoice number appears on claims of different claimants",
              "SELECT i.invoice_number FROM invoices i JOIN claims c USING (claim_id) "
              "GROUP BY i.invoice_number HAVING count(DISTINCT c.claimant_id) > 1"),
        Check("BIZ-duplicate-claimant", "Business rules", "finding",
              "Possible duplicate claimant (same name and date of birth)",
              "SELECT lower(first_name || ' ' || last_name) || ' ' || date_of_birth "
              "FROM claimants GROUP BY lower(first_name || ' ' || last_name), "
              "date_of_birth HAVING count(*) > 1"),
        Check("BIZ-missing-contact-edge", "Business rules", "finding",
              "Claimants share a phone number but no SHARES_PHONE edge records it",
              "SELECT a.claimant_id || '~' || b.claimant_id FROM claimants a "
              "JOIN claimants b ON a.normalized_phone = b.normalized_phone "
              "AND a.claimant_id < b.claimant_id "
              "WHERE a.normalized_phone IS NOT NULL AND NOT EXISTS ("
              "SELECT 1 FROM relationship_edges e "
              "WHERE e.relationship_type = 'SHARES_PHONE' AND ("
              "(e.source_id = a.claimant_id AND e.target_id = b.claimant_id) OR "
              "(e.source_id = b.claimant_id AND e.target_id = a.claimant_id)))"),
        Check("BIZ-staged-missing-policy", "Business rules", "finding",
              "Staged claim references a policy that does not exist",
              "SELECT s.external_claim_id FROM claim_staging s "
              "LEFT JOIN policies p ON p.policy_id = s.referenced_policy_id "
              "WHERE p.policy_id IS NULL"),
    ]

    # --- Signals (info) -------------------------------------------------
    checks += [
        Check("SIG-shared-phone", "Signals", "info",
              "Phone numbers shared by 2 or more claimants",
              "SELECT normalized_phone FROM claimants WHERE normalized_phone IS NOT NULL "
              "GROUP BY normalized_phone HAVING count(*) > 1"),
        Check("SIG-shared-email", "Signals", "info",
              "Emails shared by 2 or more claimants",
              "SELECT normalized_email FROM claimants WHERE normalized_email IS NOT NULL "
              "GROUP BY normalized_email HAVING count(*) > 1"),
        Check("SIG-shared-address", "Signals", "info",
              "Addresses shared by 2 or more claimants",
              "SELECT normalized_address FROM claimants WHERE normalized_address IS NOT NULL "
              "GROUP BY normalized_address HAVING count(*) > 1"),
        Check("SIG-address-only-share", "Signals", "info",
              "Shared addresses where every claimant has a different phone "
              "(household-style, not proof of fraud)",
              "SELECT normalized_address FROM claimants WHERE normalized_address IS NOT NULL "
              "GROUP BY normalized_address "
              "HAVING count(*) > 1 AND count(DISTINCT normalized_phone) = count(*)"),
        Check("SIG-provider-shared-claimants", "Signals", "info",
              "Providers billing 3 or more claimants who share one phone number",
              "SELECT i.provider_id FROM invoices i JOIN claims c USING (claim_id) "
              "JOIN claimants k ON k.claimant_id = c.claimant_id "
              "WHERE k.normalized_phone IS NOT NULL "
              "GROUP BY i.provider_id, k.normalized_phone "
              "HAVING count(DISTINCT k.claimant_id) >= 3"),
        Check("SIG-shared-incident", "Signals", "info",
              "Incidents referenced by more than one claim",
              "SELECT incident_id FROM claims GROUP BY incident_id HAVING count(*) > 1"),
    ]

    return checks


# The five edge cases the challenge requires, mapped to the checks above.
EDGE_CASES = [
    ("Claim links to a nonexistent policy", "BIZ-staged-missing-policy"),
    ("Payment exceeds approved amount", "BIZ-payment-exceeds-approved"),
    ("Duplicate invoice across claimants", "BIZ-duplicate-invoice-cross-claimant"),
    ("Real relationship missing from edges", "BIZ-missing-contact-edge"),
    ("Benign shared address (must not be proof)", "SIG-address-only-share"),
]


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------

def run_check(cur, check: Check, params: dict) -> dict:
    cur.execute(f"SELECT count(*) FROM ({check.sql}) t", params)
    count = cur.fetchone()[0]

    samples = []
    if count:
        cur.execute(f"SELECT * FROM ({check.sql}) t LIMIT {SAMPLE_SIZE}", params)
        samples = [str(row[0]) for row in cur.fetchall()]

    return {
        "id": check.check_id,
        "section": check.section,
        "kind": check.kind,
        "description": check.description,
        "violations": count,
        "samples": samples,
    }


def status_of(result: dict) -> str:
    if result["kind"] == "info":
        return "INFO"
    if result["violations"] == 0:
        return "PASS"
    return "FAIL" if result["kind"] == "integrity" else "FIND"


def validate(database_url: str, as_of: str, output_dir: Path) -> dict:
    params = {"as_of": as_of}
    results = []

    with psycopg.connect(database_url) as conn:
        conn.read_only = True
        with conn.cursor() as cur:

            row_counts = {}
            for table in ROW_COUNT_TABLES:
                cur.execute(f"SELECT count(*) FROM {table}")
                row_counts[table] = cur.fetchone()[0]

            for check in build_checks():
                results.append(run_check(cur, check, params))

    empty = [t for t, n in row_counts.items() if n == 0]
    for table in empty:
        results.insert(0, {
            "id": f"ROWS-{table}", "section": "Row counts", "kind": "integrity",
            "description": f"{table} is not empty", "violations": 1, "samples": [],
        })

    coverage = {}
    by_id = {r["id"]: r for r in results}
    for label, check_id in EDGE_CASES:
        coverage[label] = by_id[check_id]["violations"]

    summary = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of,
        "row_counts": row_counts,
        "totals": {
            "integrity_checks": sum(r["kind"] == "integrity" for r in results),
            "integrity_failures": sum(status_of(r) == "FAIL" for r in results),
            "findings": sum(status_of(r) == "FIND" for r in results),
            "info_signals": sum(r["kind"] == "info" for r in results),
        },
        "edge_case_coverage": coverage,
        "checks": results,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "validation_summary.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    return summary


def print_report(summary: dict) -> None:
    print("\n========== ROW COUNTS ==========")
    for table, count in summary["row_counts"].items():
        print(f"  {table:<24}{count:>8}")

    section = None
    for result in summary["checks"]:
        if result["section"] != section:
            section = result["section"]
            print(f"\n========== {section.upper()} ==========")

        status = status_of(result)
        detail = f"  ({result['violations']})" if result["violations"] else ""
        print(f"[{status}] {result['description']}{detail}")
        if result["violations"] and result["kind"] != "info":
            print(f"        e.g. {', '.join(result['samples'])}")

    print("\n========== REQUIRED EDGE CASES ==========")
    for label, count in summary["edge_case_coverage"].items():
        state = f"found {count}" if count else "NOT FOUND in data"
        print(f"  {label:<46}{state}")

    totals = summary["totals"]
    print("\n========== SUMMARY ==========")
    print(f"  Integrity checks : {totals['integrity_checks']}  "
          f"(failed: {totals['integrity_failures']})")
    print(f"  Business findings: {totals['findings']} rules with violations")
    print(f"  Signals reported : {totals['info_signals']}")
    print("\nIntegrity:", "PASS" if totals["integrity_failures"] == 0 else "FAIL")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the loaded dataset")
    parser.add_argument("--as-of", default="2026-10-31",
                        help="Reference date for 'not in the future' checks")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--strict", action="store_true",
                        help="Also exit with code 1 when business findings exist")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set. Add it to your .env file.")

    summary = validate(database_url, args.as_of, args.output_dir)
    print_report(summary)
    print(f"\nSummary written to: {(args.output_dir / 'validation_summary.json').resolve()}")

    failed = summary["totals"]["integrity_failures"] > 0
    if args.strict:
        failed = failed or summary["totals"]["findings"] > 0
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()