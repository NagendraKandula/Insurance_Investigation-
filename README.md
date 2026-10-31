# Insurance Fraud Network Investigation

An end-to-end insurance fraud investigation prototype that analyses relationships between claimants, policies, incidents, providers, invoices and payments. It builds a graph of the available relationships, detects suspicious patterns, assigns explainable risk scores, evaluates results against a separate synthetic ground-truth dataset, and presents the findings in an analyst-facing web portal.

> **Important:** A risk score is an investigation priority, not proof that fraud occurred. Findings should be reviewed with the underlying evidence.

All records in this project are synthetic. No real policyholder or claim data is used.

---

## Contents

- [What the system does](#what-the-system-does)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Technology stack](#technology-stack)
- [Data model and generated dataset](#data-model-and-generated-dataset)
- [Detection and scoring](#detection-and-scoring)
- [Evaluation and current results](#evaluation-and-current-results)
- [API reference](#api-reference)
- [Frontend routes](#frontend-routes)
- [Setup and running locally](#setup-and-running-locally)
- [Important implementation decisions](#important-implementation-decisions)
- [Limitations and future improvements](#limitations-and-future-improvements)

---

## What the system does

The project is organised as a pipeline:

1. **Generate data:** Create a reproducible synthetic insurance dataset, including normal records and deliberately planted suspicious and benign patterns.
2. **Store data:** Export the generated tables and load them into PostgreSQL (Neon in the reference setup).
3. **Build a relationship graph:** Load the business records and relationship edges into a NetworkX graph.
4. **Detect suspicious indicators:** Run independent detectors for missing relationship edges, shared providers, duplicate invoice numbers and payment anomalies.
5. **Score entities:** Aggregate the detector findings into explainable entity-level risk scores.
6. **Evaluate:** Compare the scores with the isolated ground-truth answer key.
7. **Investigate:** Serve the JSON results through FastAPI and display the ranked queue, evidence and relationship graph in the Next.js frontend.

The detector pipeline does **not** use ground-truth labels as features. The answer key is separated from detection data and passed to the evaluator only after scoring.

---

## Screenshots

The screenshots below are expected in `docs/screenshots/`. Keep these filenames (or update the paths here if your filenames differ).

### 1. Executive dashboard

![Executive dashboard showing entity totals, risk distribution and evaluation summary](docs/screenshots/01-dashboard-summary.png)

### 2. Detection accuracy and signal volumes

![Detection metrics and detector signal counts](docs/screenshots/02-dashboard-accuracy-and-signals.png)

### 3. Analyst investigation queue

![Analyst queue with risk and signal filters](docs/screenshots/03-analyst-queue.png)

### 4. Entity investigation and network graph

![Entity investigation page showing a relationship graph](docs/screenshots/04-investigation-network-graph.png)

### 5. Evidence details

![Evidence cards for shared provider and duplicate invoice indicators](docs/screenshots/05-signal-evidence-shared-provider-duplicate-invoice.png)

![Evidence cards for financial anomaly indicators](docs/screenshots/06-signal-evidence-payment-anomalies.png)

---

## Architecture

```mermaid
flowchart TD
    A["Synthetic data generator<br/>generator/"] --> B["CSV exports, manifest and checksums"]
    B --> C[("PostgreSQL / Neon<br/>database/ schema")]
    C --> D["Data loader<br/>detection/db_loader.py"]
    D --> E["NetworkX graph builder<br/>detection/graph_builder.py"]
    E --> F["Four detection modules"]
    F --> G["Risk scorer<br/>fraud_scorer.py"]
    G --> H["Evaluation<br/>evaluator.py"]
    G --> I["output/risk_scores.json"]
    H --> J["output/evaluation_report.json"]
    F --> K["output/detector_counts.json"]
    I --> L["FastAPI REST API<br/>api/"]
    J --> L
    K --> L
    L --> M["Next.js investigation portal<br/>frontend/"]
    M --> N["Dashboard, analyst queue<br/>and entity network view"]
```

### Data and detection flow

- The generator creates parent records before dependent records so foreign-key relationships can refer to existing entities.
- It injects labelled suspicious patterns and benign lookalike patterns into the synthetic dataset.
- Relationship edges and status-history events are generated from the final records.
- The detection loader reads the business tables and relationship edges. Ground truth is removed from the detection dataset before graph construction.
- Detectors inspect the graph and source-record attributes, not the generator's labels.
- The scorer aggregates findings by entity. The evaluator receives the ground-truth data only after the scores have been produced.
- The detection pipeline writes JSON result files. FastAPI reads those files and the frontend consumes the API.

---

## Project structure

```text
insurance-investigation/
│
├── database/                 # PostgreSQL schema, supporting tables and indexes
│
├── generator/                # Synthetic data generation pipeline
│   ├── main.py               # Generation pipeline entry point
│   ├── pattern_injector.py   # Suspicious and benign pattern injection
│   ├── ground_truth_writer.py# Ground-truth preparation and leakage guard
│   ├── export.py             # CSV export, manifest and checksums
│   ├── load_neon.py          # Loading generated CSV data into Neon
│   └── validate.py           # Data integrity and business-rule validation
│
├── detection/                # Graph-based detection and evaluation
│   ├── main.py               # Detection pipeline entry point
│   ├── db_loader.py          # Loads source data from PostgreSQL
│   ├── graph_builder.py      # Builds the NetworkX MultiDiGraph
│   ├── edge_gap_detector.py
│   ├── shared_provider_detector.py
│   ├── duplicate_invoice_detector.py
│   ├── payment_anomaly_detector.py
│   ├── fraud_scorer.py        # Explainable entity risk scoring
│   └── evaluator.py           # Evaluation against ground truth
│
├── api/
│   ├── __init__.py
│   └── main.py               # FastAPI read-only REST service
│
├── frontend/                 # Next.js analyst portal
│   ├── app/                  # Dashboard, queue and entity routes
│   ├── components/           # Dashboard, queue, evidence and graph UI
│   └── lib/                  # API client, graph mapping and labels
│
├── docs/
│   └── screenshots/          # UI screenshots used in this README
│
├── output/                   # Generated JSON results and run artefacts
├── requirements.txt
└── README.md
```

Generated output files should be treated as runtime artefacts. Do not commit database credentials, `.env` files, or sensitive connection strings.

---

## Technology stack

| Area | Technology |
|---|---|
| Language and data generation | Python, Faker |
| Graph analysis | NetworkX |
| Database | PostgreSQL (Neon) |
| Database access | psycopg |
| Reproducibility | Fixed random seed, freezegun, SHA-256 checksums |
| Backend API | FastAPI, Uvicorn |
| Frontend | Next.js 16, React 19, TypeScript |
| Styling | Tailwind CSS 4 |
| Network visualisation | react-force-graph-2d |

---

## Data model and generated dataset

The synthetic dataset models the main entities involved in an insurance claim lifecycle.

| Entity / table | Purpose |
|---|---|
| `claimants` | People submitting claims |
| `policies` | Insurance policies held by claimants |
| `incidents` | Reported events associated with claims |
| `claims` | Claim records submitted against policies |
| `providers` | Service providers issuing invoices |
| `invoices` | Bills associated with claims and providers |
| `payments` | Payments, refunds and reversals |
| `relationship_edges` | Typed relationships between entities |
| `claim_status_events` | Claim lifecycle history |
| `payment_status_events` | Payment lifecycle history |
| `ground_truth` | Separate evaluation labels; never a detector feature |

The schema also includes supporting tables for users, data-generation runs, networks, investigations, events and data-quality workflows. Some of these are schema foundations and are not yet populated by the current detection pipeline.

### Full-scale reference dataset

| Data type | Records |
|---|---:|
| Claimants | 2,000 |
| Providers | 500 |
| Policies | 3,000 |
| Incidents | 4,000 |
| Claims | 5,000 |
| Invoices | 6,000 |
| Payments | 8,000 |
| Users | 20 |
| Relationship edges | 38,000 |

The reference dataset contains 320 ground-truth records: 276 suspicious and 44 benign. Planted patterns include shared-provider clusters, duplicate invoice numbers and benign shared-address communities.

### Reproducibility and validation

The generator uses a fixed seed and deterministic data-generation steps. CSV exports include a manifest and SHA-256 checksums. The validation module checks keys, relationships, allowed values, dates, arithmetic and lifecycle consistency.

```powershell
python -m generator.main --scale full --repro-check
python -m generator.validate
```

The `--repro-check` option checks whether repeated generation with the same seed produces matching outputs. Validation is separate from fraud detection and does not use ground-truth labels.

---

## Detection and scoring

The graph builder creates a NetworkX `MultiDiGraph` from the source entities and the explicit `relationship_edges` table.

### Detection modules

| Detector | What it identifies |
|---|---|
| `EdgeGapDetector` | Claimants sharing a normalised phone number when the corresponding `SHARES_PHONE` relationship edge is missing |
| `SharedProviderDetector` | Providers connected to invoices and claims from three or more distinct claimants |
| `DuplicateInvoiceDetector` | Invoice numbers reused across invoices belonging to different claimants |
| `PaymentAnomalyDetector` | Financial inconsistencies involving invoice totals, approved claim amounts, rejected invoices and net payments |

The payment detector calculates net payments by accounting for payments, refunds and reversals.

### Explainable risk scoring

`fraud_scorer.py` aggregates detector findings into a score from 0 to 100 for each affected entity. A signal type is counted once per entity, and corroborating independent signals can increase the score.

| Signal | Base points |
|---|---:|
| Duplicate invoice across claimants | 30 |
| Payment on rejected invoice | 25 |
| Payments exceed approved amount | 25 |
| Shared phone with missing relationship edge | 15 |
| Invoices exceed claim amount | 15 |
| Paid invoice underpayment | 10 |
| Shared-provider cluster | 10 |

Risk bands used by the scorer:

- **HIGH:** 70–100
- **MEDIUM:** 40–69
- **LOW:** 0–39

The score is a rule-based investigation-priority score, not a statistically calibrated probability of fraud.

---

## Evaluation and current results

The evaluator compares entity scores with the separate ground-truth labels at a configurable threshold. It reports a confusion matrix, precision, recall, F1 score, accuracy, per-pattern metrics and network-level detection information.

The following figures are from the recorded **full-scale reference run at threshold 40**. They describe this synthetic dataset and should not be interpreted as expected real-world performance.

| Measure | Reference result |
|---|---:|
| Entities scored | 11,167 |
| HIGH risk | 991 |
| MEDIUM risk | 2,783 |
| LOW risk | 7,393 |
| Precision on labelled entities | 100.0% |
| Recall | 37.7% |
| F1 score | 54.7% |
| Accuracy | 46.3% |
| Missing-phone-edge findings | 72 |
| Shared-provider findings | 500 |
| Duplicate invoice findings | 4 |
| Payment anomaly findings | 6,838 |

### Interpreting the metrics

The reported 100% precision applies only to the entities represented in the labelled ground-truth set. Many flagged entities are outside that labelled set and therefore are not counted as false positives by this evaluation. The evaluation dashboard includes a coverage caveat for this reason.

The shared-provider detector is intentionally broad: a provider connected to multiple claimants is a lead for review, not proof of collusion. Financial anomalies can also reflect inconsistencies in the synthetic baseline data. Analysts should inspect the evidence associated with each signal before drawing conclusions.

---

## REST API

The FastAPI service reads the JSON artefacts generated by `python -m detection.main`. It does not run the detection pipeline itself. Re-running detection updates the JSON files that the API serves.

Start the API from the project root:

```powershell
python -m uvicorn api.main:app --reload --port 8000
```

Interactive API documentation:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | API welcome/status response |
| `GET` | `/api/health` | Check API and result-file availability |
| `GET` | `/api/summary` | Dashboard totals and risk-level summary |
| `GET` | `/api/risk-scores` | List and filter scored entities |
| `GET` | `/api/risk-scores/{entity_type}/{entity_id}` | Retrieve one entity and its evidence |
| `GET` | `/api/evaluation` | Evaluation metrics and confusion matrix |
| `GET` | `/api/detector-counts` | Detector finding counts |

Check the live Swagger documentation for the exact query parameters and response schemas implemented in the running API.

---

## Frontend

The frontend is a Next.js App Router application built with React, TypeScript and Tailwind CSS. It consumes the FastAPI endpoints and provides three main analyst workflows.

| Route | Purpose |
|---|---|
| `/` | Executive dashboard with entity totals, risk distribution, evaluation metrics and detector/signal summaries |
| `/queue` | Paginated analyst queue with risk, entity-type and signal filters |
| `/entities/{type}/{id}` | Entity risk score, signal evidence and interactive relationship graph |

### Network graph

The frontend maps an entity's detector evidence into graph nodes and links. The graph can show relationships involving claimants, providers, claims and invoices. The selected entity is visually highlighted, and scored entities can be opened for further investigation.

---

## Setup and running locally

### Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer
- npm
- PostgreSQL database (the reference deployment uses Neon)

### 1. Clone the repository and install Python dependencies

```powershell
git clone <YOUR_REPOSITORY_URL>
cd insurance-investigation

python -m pip install -r requirements.txt
python -m pip install fastapi uvicorn
```

A virtual environment is recommended for a clean installation, but it is not mandatory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install fastapi uvicorn
```

### 2. Configure the database

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Apply the SQL files in the order required by the schema:

1. `database/schema.sql`
2. `database/next_tables.sql`
3. `database/financial_tables.sql`
4. `database/relationship_tables.sql`
5. `database/detection_tables.sql`
6. `database/investigation_tables.sql`
7. `database/supporting_tables.sql`
8. `database/indexes.sql`
9. `database/additional_indexes.sql`

Use the database setup instructions and SQL files included in the repository. The exact `psql` command depends on your local PostgreSQL client setup.

### 3. Generate and load the dataset

For a new, empty database, run the generator's full-scale load command:

```powershell
python -m generator.main --scale full --load-neon --truncate
```

> **Warning:** `--truncate` clears existing table data before loading. Do not run this against a database containing data you need to keep. The reference project database has already been generated and loaded, so this step is not needed when using that existing database.

Validate the loaded data:

```powershell
python -m generator.validate
```

### 4. Run detection, scoring and evaluation

From the project root:

```powershell
python -m detection.main
```

This reads the database and writes the result artefacts under `output/`, including:

- `risk_scores.json`
- `evaluation_report.json`
- `detector_counts.json`

The frontend and API depend on these files being present.

### 5. Start the FastAPI backend

Open a terminal at the project root:

```powershell
python -m uvicorn api.main:app --reload --port 8000
```

The API runs at `http://127.0.0.1:8000`.

### 6. Configure and start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Start the frontend:

```powershell
npm run dev
```

Open `http://localhost:3000`.

For a production frontend build:

```powershell
npm run build
npm start
```

---

## Important implementation decisions

- **Ground-truth isolation:** Labels are withheld from graph construction and detection. They are used only by the evaluator after risk scoring.
- **Graph-based detection:** Detectors inspect relationships and business records rather than relying on generator labels.
- **Separate pipeline and API:** Detection produces JSON artefacts; the API serves them independently. This keeps expensive graph analysis out of ordinary dashboard requests.
- **Evidence-backed scoring:** Each score is accompanied by signal types and evidence so an analyst can understand why an entity was prioritised.
- **Benign patterns included:** Shared-address communities are included to help ensure that a common address alone is not treated as proof of fraud.
- **Synthetic and reproducible data:** A fixed seed, manifest and checksums support repeatable test runs.

---

## Limitations and future improvements

This is a recruitment-challenge prototype, not a production claims platform. Current areas for improvement include:

1. Improve baseline financial-data consistency so ordinary records generate fewer unlabelled payment anomalies.
2. Expand ground-truth coverage and evaluation so flagged-but-unlabelled entities can be assessed more meaningfully.
3. Improve network-level ranking instead of relying primarily on entity-level scores.
4. Persist detection networks and indicators in the database and add investigation/case-management workflows.
5. Add more planted patterns, such as repeated incident narratives, unusual timing and additional benign decoys.
6. Add authentication, authorisation, audit logging and operational monitoring before any production use.
7. Review thresholds and detector rules against larger, independently labelled datasets.

---

## Data provenance and responsible use

All records are synthetic and generated by this project. The system is designed to surface explainable indicators for human investigation. It must not be used to automatically reject claims, accuse individuals or make consequential decisions without appropriate human review and independent validation.
