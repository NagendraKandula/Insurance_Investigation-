# AI Prompt History – Synthetic Insurance Dataset Generation

## Project: Insurance Fraud Investigation System

### 1. Purpose

This document records how AI assistance was used during the development of the synthetic insurance dataset generation pipeline.

The objective was to generate a reproducible, relational insurance dataset containing realistic entities, relationships, deliberately planted fraud patterns, and benign communities.

AI was used as a development assistant for code generation, debugging, validation, and implementation guidance. Generated code was reviewed and tested before integration.

---

## 2. Global project context

**Initial project prompt:**

I am building an Insurance Fraud Investigation System for a recruitment challenge.

I need to generate a realistic synthetic insurance dataset using Python, Faker, PostgreSQL, and NetworkX.

The dataset should contain:

- Claimants
- Insurance policies
- Incidents
- Claims
- Providers
- Invoices
- Payments
- Relationship edges
- Investigation users
- Claim and payment status events
- Ground-truth fraud labels

The system should support graph-based fraud investigation.

Requirements:

1. Generate reproducible data using a fixed random seed.
2. Maintain valid foreign-key relationships.
3. Generate realistic Indian names, phone numbers, addresses, and cities.
4. Plant suspicious fraud networks.
5. Generate benign communities to test false-positive handling.
6. Maintain a separate ground-truth table.
7. Never allow detection algorithms to access ground-truth labels.
8. Validate generated records before loading them into PostgreSQL.
9. Export the generated dataset for reproducibility and inspection.

Use modular Python files rather than implementing everything in one script.

---

## 3. File-by-file prompt history

### 3.1 config.py

**Prompt:**

Create a centralized configuration module for a synthetic insurance dataset generator.

Requirements:
- Load environment variables using python-dotenv.
- Read the PostgreSQL DATABASE_URL.
- Use a fixed random seed of 20261031.
- Configure Faker with the Indian locale.
- Define full-scale dataset volumes:
  - 2,000 claimants
  - 500 providers
  - 3,000 policies
  - 4,000 incidents
  - 5,000 claims
  - 6,000 invoices
  - 8,000 payments
- Configure suspicious network and benign community counts.
- Define a generator version.

**Review prompt:**

Review the configuration for reproducibility, missing environment variables, and consistency between configured dataset volumes and actual generated relationship counts.

### 3.2 id_generator.py

**Prompt:**

Implement a reusable ID generator for all insurance entities.

Use prefixes:
- CPT for claimants
- CLM for claims
- POL for policies
- INC for incidents
- PRV for providers
- INV for invoices
- PAY for payments
- NET for networks
- IVG for investigations
- IND for indicators
- EXC for exceptions

IDs must be unique within their entity type. Support both individual and batch generation.

**Review prompt:**

Check whether IDs can collide, whether counters are maintained correctly, and whether batch generation produces unique identifiers.

### 3.3 normalizers.py

**Prompt:**

Create reusable normalization functions for email addresses, phone numbers, and addresses.

Requirements:
- Normalize email to lowercase and remove unnecessary whitespace.
- Normalize Indian phone numbers by removing formatting characters.
- Handle the Indian country code consistently.
- Normalize addresses using Unicode normalization, lowercase conversion, punctuation removal, and whitespace cleanup.

**Review prompt:**

Test the normalization functions using different formatting variations of the same phone number, email, and address.

### 3.4 claimant_generator.py

**Prompt:**

Create a claimant generator using Faker with Indian locale data.

Each claimant should contain:
- Unique claimant ID
- First and last name
- Date of birth
- Gender
- Email and normalized email
- Phone and normalized phone
- Address and normalized address
- City, state, and postal code
- Created and updated timestamps

Generate realistic Indian claimant records and ensure required fields are populated.

**Review prompt:**

Check unique claimant IDs, phone number formatting, normalized fields, date validity, and consistency of generated records.

### 3.5 provider_generator.py

**Prompt:**

Create a synthetic insurance provider generator.

Support provider types such as:
- Hospitals
- Clinics
- Garages
- Auto repair centers
- Pharmacies
- Diagnostic centers
- Construction services
- Legal services

Each provider must have a unique provider ID and registration number, along with contact details, normalized fields, address, city, state, registration date, and status.

**Review prompt:**

Validate unique registration numbers, provider types, normalized contact information, and required fields.

### 3.6 user_generator.py

**Prompt:**

Create a generator for system users who participate in insurance investigations.

Generate users with roles:
- ANALYST
- REVIEWER
- ADMIN

Each user should have a unique ID, full name, email, role, status, and creation timestamp.

**Review prompt:**

Verify that generated user roles belong to the allowed role set and email addresses are unique.

### 3.7 policy_generator.py

**Prompt:**

Implement an insurance policy generator.

Requirements:
- Every policy must reference an existing claimant.
- Generate policy numbers, policy types, coverage amounts, premiums, and deductibles.
- Support HEALTH, MOTOR, HOME, LIFE, and TRAVEL policies.
- Generate valid start and end dates.
- Generate ACTIVE, CANCELLED, and EXPIRED statuses.
- Use Decimal for monetary values.

**Review prompt:**

Check claimant references, date validity, monetary constraints, policy-number uniqueness, and policy status consistency.

### 3.8 incident_generator.py

**Prompt:**

Create a synthetic insurance incident generator.

Support:
- Vehicle accidents
- Fire
- Theft
- Medical incidents
- Property damage
- Natural disasters

Each incident should include its ID, type, date, reported date, description, location, city, state, and estimated loss.

Ensure reported dates do not occur before incident dates.

**Review prompt:**

Validate incident dates, reported dates, estimated losses, and required fields.

### 3.9 claim_generator.py

**Prompt:**

Implement a claim generator that connects claimants, policies, and incidents.

Requirements:
- Every claim references an existing claimant, policy, and incident.
- The policy must belong to the same claimant.
- The incident must fall within the policy coverage period.
- Claim amounts must respect coverage and estimated loss constraints.
- Support PENDING, UNDER_REVIEW, APPROVED, and REJECTED statuses.
- Approved amounts must be consistent with claim status.

**Review prompt:**

Check all foreign-key references, claimant-policy ownership, policy coverage dates, monetary constraints, and approved amount consistency.

### 3.10 invoice_generator.py

**Prompt:**

Create an invoice generator connected to existing claims and providers.

Each invoice must contain:
- Invoice ID
- Provider ID
- Claim ID
- Invoice number
- Invoice amount
- Invoice date
- Due date
- Description
- Status

Ensure invoice amounts do not exceed the associated claim amount.

Keep invoice numbers non-unique at the database level because duplicate invoice numbers will be deliberately planted later as a fraud pattern.

**Review prompt:**

Validate provider and claim references, invoice amounts, invoice dates, and invoice-number behavior.

### 3.11 payment_generator.py

**Prompt:**

Create a payment transaction generator for existing invoices.

Support:
- PAYMENT
- REFUND
- REVERSAL

Requirements:
- Every payment transaction must reference an existing invoice.
- Generate unique transaction references.
- Payment amounts must be positive.
- Refunds and reversals must reference valid invoices.
- Transaction dates must follow the original payment date where applicable.
- Generate realistic payment methods and statuses.

**Review prompt:**

Check transaction references, invoice references, transaction types, monetary constraints, and payment/refund/reversal consistency.

### 3.12 pattern_injector.py

**Prompt:**

Implement a synthetic fraud-pattern injector for an insurance investigation dataset.

Plant the following patterns:

1. Shared provider cluster:
   - Multiple claimants use a common provider.
   - Claimants share a deliberately repeated phone number.
   - Create ground-truth records for participating entities.

2. Duplicate invoice number:
   - Reuse invoice numbers across different invoices.
   - Use different providers and claims.
   - Record the planted relationships in ground truth.

3. Benign shared-address communities:
   - Multiple legitimate claimants share an address.
   - Keep their phone numbers separate.
   - Label these communities BENIGN.

Requirements:
- Use a fixed random seed.
- Avoid accidental reuse of entities across incompatible patterns.
- Store pattern type, network ID, entity type, entity ID, role, expected label, and description in ground truth.
- Do not implement detection logic inside the injector.

**Review prompt:**

Check that planted networks contain the expected number of members, that benign communities are not marked suspicious, that duplicate invoice numbers are actually reused, and that ground-truth records match the injected data.

### 3.13 relationship_generator.py

**Prompt:**

Implement a relationship-edge generator for the insurance dataset.

Generate these relationships:

- CLAIMANT → POLICY: OWNS_POLICY
- CLAIMANT → CLAIM: FILED_CLAIM
- POLICY → CLAIM: COVERS_CLAIM
- INCIDENT → CLAIM: REPORTED_IN_CLAIM
- PROVIDER → INVOICE: ISSUED_INVOICE
- CLAIM → INVOICE: HAS_INVOICE
- INVOICE → PAYMENT: HAS_PAYMENT

Requirements:
- Validate entity references.
- Maintain consistent relationship directions.
- Detect duplicate or invalid edges.
- Generate confidence and relationship metadata.
- Do not generate SHARES_PHONE edges intentionally. This missing relationship will be investigated independently by the detection pipeline.

**Review prompt:**

Verify all seven relationship types, validate source and target references, check edge counts against the entity relationships, and confirm that the intentionally missing phone relationship has not been generated.

### 3.14 event_generator.py

**Prompt:**

Create generators for claim status events and payment status events.

Requirements:
- Generate realistic status transitions.
- Reference valid claims and payments.
- Generate event timestamps.
- Include previous status, new status, actor, and remarks where applicable.
- Maintain valid relationships with investigation users.

**Review prompt:**

Check event references, valid status transitions, timestamp ordering, and user references.

### 3.15 ground_truth_writer.py

**Prompt:**

Implement a ground-truth writer for the synthetic insurance fraud dataset.

Requirements:
- Store planted network labels separately from the main detection data.
- Preserve suspicious and benign labels.
- Include entity IDs, pattern types, roles, issue types, and generation-run references.
- Support database insertion and export.
- Do not allow the fraud detection algorithms to use ground-truth records.

**Review prompt:**

Check for missing labels, duplicate records, incorrect network membership, and consistency with injected patterns.

### 3.16 export.py

**Prompt:**

Create an export module that writes generated datasets into an output directory.

Requirements:
- Export generated entities and relationships.
- Support CSV or JSON output.
- Preserve entity IDs and relationship references.
- Export ground truth separately.
- Produce a dataset manifest.
- Calculate a dataset checksum for reproducibility and integrity verification.

**Review prompt:**

Check that exported files contain the expected rows, preserve relationships, and match the generated dataset manifest.

### 3.17 validate.py

**Prompt:**

Create a validation module for the synthetic insurance dataset.

Validate:
- Required fields
- Unique identifiers
- Foreign-key relationships
- Claimant-policy ownership
- Policy coverage dates
- Invoice amounts
- Payment references
- Relationship-edge references
- Ground-truth record integrity

Report validation failures clearly without silently modifying generated data.

**Review prompt:**

Run validation against the full-scale generated dataset and verify that errors are reported with entity IDs and useful descriptions.

### 3.18 load_neon.py

**Prompt:**

Create a PostgreSQL loader using psycopg and environment-based database configuration.

Requirements:
- Load generated datasets into the existing Neon PostgreSQL schema.
- Insert records in foreign-key dependency order.
- Use transactions.
- Handle JSONB values correctly.
- Validate inserted row counts against the dataset manifest.
- Provide clear progress messages and error handling.
- Support an explicitly requested truncate option, with clear warnings because TRUNCATE CASCADE can remove referencing records.

**Review prompt:**

Check table names, column mappings, insertion order, transaction handling, row-count verification, and behavior when loading fails.

### 3.19 main.py

**Prompt:**

Create the main orchestration module for the complete synthetic insurance data-generation pipeline.

Requirements:
- Support command-line arguments for dataset scale.
- Support full and test generation modes.
- Run generators in dependency order.
- Generate users, claimants, providers, policies, incidents, claims, invoices, and payments.
- Inject suspicious and benign patterns.
- Generate relationship edges and status events.
- Write ground truth separately.
- Validate the generated dataset.
- Export files and create a manifest.
- Optionally load the generated dataset into Neon.
- Support an explicit --truncate option.
- Print a complete generation summary and checksum.

**Review prompt:**

Review the orchestration order, module imports, command-line arguments, generator dependencies, output files, database-loading behavior, and final row-count verification.

---

## 4. Full-scale execution evidence

Command executed:

```powershell
python -m generator.main --scale full --load-neon --truncate
```

Generation results:

| Dataset | Rows |
|---|---:|
| Users | 20 |
| Claimants | 2,000 |
| Providers | 500 |
| Policies | 3,000 |
| Incidents | 4,000 |
| Claims | 5,000 |
| Invoices | 6,000 |
| Payments | 8,000 |
| Relationship edges | 38,000 |
| Claim status events | 10,861 |
| Payment status events | 8,000 |
| Ground truth | 320 |

### Ground-truth distribution

| Pattern | Records |
|---|---:|
| SHARED_PROVIDER_CLUSTER | 240 |
| DUPLICATE_INVOICE_NUMBER | 36 |
| BENIGN_SHARED_ADDRESS | 44 |
| **Total** | **320** |

Planted network distribution:
- Suspicious networks: 28
- Benign communities: 11

### Dataset integrity

Dataset checksum:

```text
7ddfe15724a966f979a94516d39934873c11ab13b0dc30c219d2d75eb0b12fd8
```

### Neon loading result

The generation and loading process reported:

```text
Loaded users
Loaded claimants
Loaded providers
Loaded policies
Loaded incidents
Loaded claims
Loaded invoices
Loaded payments
Loaded relationship_edges
Loaded claim_status_events
Loaded payment_status_events
Loaded ground_truth

Load complete. Row counts match the manifest.
```

---

## 5. AI usage and verification approach

AI assistance was used for:
- Designing modular data generators.
- Implementing realistic synthetic data generation.
- Creating planted fraud patterns.
- Debugging Python module imports and generation issues.
- Reviewing relationship integrity.
- Implementing PostgreSQL loading and validation logic.

Code was tested through module-level checks and a full-scale generation and database-loading run.

**Important separation:** Ground-truth labels represent known planted patterns and are reserved for evaluation. They must not be used as input to the independent fraud detection algorithms.

---

## 6. Current project status

Completed:
- Synthetic entity generation.
- Relationship generation.
- Fraud-pattern injection.
- Ground-truth generation.
- Full-scale dataset export.
- Neon PostgreSQL loading.
- Initial row-count verification.

Next:
- Independent graph-based fraud detection.
- Missing relationship discovery.
- Fraud indicator generation.
- Investigation lead ranking.
- Precision, recall, F1, and false-positive evaluation.
