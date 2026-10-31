# Insurance Fraud Investigation System

## LLM Development History and Decision Log --- Detection Folder

> **Purpose:** This document records the decisions, architecture,
> implementation steps, validation results, and reasoning behind
> creating the `detection/` folder.
>
> **Scope and accuracy note:** This is a consolidated, chronological
> reconstruction from the conversation history and project context
> available in this chat. It is not a verbatim export of every message
> or terminal session. Where exact source code or a decision was not
> preserved in the available history, this document describes only what
> is known and marks assumptions explicitly.

------------------------------------------------------------------------

## 1. Project objective

Build an insurance fraud investigation system that identifies suspicious
relationships and financial patterns across insurance claims, claimants,
providers, invoices, and payments.

The system uses: - Neon PostgreSQL as the data source. - Python for the
detection pipeline. - NetworkX to represent relationships as a graph. -
Deterministic, explainable detection rules. - A risk scorer to
prioritize entities for investigation. - An evaluator to compare
detections with a separately stored synthetic answer key.

The system produces **investigation leads**, not proof or a final
accusation of fraud. A human investigator must review the supporting
evidence.

### Main design principle

The project does not need to force an LLM, machine-learning model, or
graph neural network into the detection engine. Explainable graph rules
and evidence-based scoring are appropriate for the current challenge
scope.

------------------------------------------------------------------------

## 2. Dataset and database decisions

The synthetic dataset was generated and loaded into Neon PostgreSQL
before the detection implementation was completed.

### Important instruction

The generator had already been run successfully with truncation and
loading. **Do not rerun the generator with `--truncate`**, because that
would replace the current dataset.

### Dataset counts recorded during validation

  Table/entity              Records
  ----------------------- ---------
  users                          20
  claimants                   2,000
  providers                     500
  policies                    3,000
  incidents                   4,000
  claims                      5,000
  invoices                    6,000
  payments                    8,000
  relationship_edges         38,000
  claim_status_events        10,861
  payment_status_events       8,000
  ground_truth                  320

The graph uses seven main entity types: claimant, policy, incident,
claim, provider, invoice, and payment.

### Ground-truth distribution

  Pattern                    Label            Count
  -------------------------- ------------ ---------
  BENIGN_SHARED_ADDRESS      BENIGN              44
  DUPLICATE_INVOICE_NUMBER   SUSPICIOUS          36
  SHARED_PROVIDER_CLUSTER    SUSPICIOUS         240
  **Total**                                 **320**

The suspicious planted data contains 28 networks, and the benign planted
data contains 11 networks.

Ground-truth records include fields such as: - `planted_network_id` -
`entity_type` - `entity_id` - `pattern_type` - `role_in_network` -
`expected_label` - `description`

### Ground-truth isolation decision

This is one of the most important project decisions:

1.  Load `ground_truth` for evaluation.
2.  Separate it immediately from ordinary detection data.
3.  Never pass it to graph construction, detectors, or fraud scoring.
4.  Pass it only to the evaluator after risk scores have been produced.

This prevents answer-key leakage into the detection logic.

The implementation pattern used by test scripts was:

``` python
data = loader.load_all_data()

ground_truth = data["ground_truth"]

detection_data = {
    key: value
    for key, value in data.items()
    if key != "ground_truth"
}
```

The final `main.py` later used `data.pop("ground_truth")` to remove it
from the dictionary before building the graph.

------------------------------------------------------------------------

## 3. Detection folder architecture

The detection package was created to keep each responsibility isolated.

Final known file responsibilities:

  -----------------------------------------------------------------------
  File                                Responsibility
  ----------------------------------- -----------------------------------
  `__init__.py`                       Expose/import detection classes

  `db_loader.py`                      Read required records from Neon

  `graph_builder.py`                  Build the NetworkX relationship
                                      graph

  `edge_gap_detector.py`              Find missing phone relationships

  `shared_provider_detector.py`       Find claimant-provider clusters

  `duplicate_invoice_detector.py`     Find duplicate invoice numbers
                                      across claimants

  `payment_anomaly_detector.py`       Detect payment and invoice
                                      anomalies

  `fraud_scorer.py`                   Combine findings into entity risk
                                      scores

  `evaluator.py`                      Evaluate predictions against ground
                                      truth

  `main.py`                           Run the complete pipeline end to
                                      end
  -----------------------------------------------------------------------

**Naming correction:** The actual scorer filename is `fraud_scorer.py`,
not `fraud_scoring.py`. The evaluator filename used in the final main
file is `evaluator.py`.

------------------------------------------------------------------------

## 4. Implementation history, module by module

### 4.1 `db_loader.py`

**Decision:** Centralize database reads in one loader rather than
letting every detector independently query Neon.

Known behavior: - Loads the required tables in one repeatable-read,
read-only transaction. - Exposes `load_all_data()`. - Loads the
ground-truth table as part of the returned data, but the caller must
isolate it before detection.

Validation: - `test_db_loader.py` passed. - The final pipeline loaded
the records successfully. - The recorded load duration in the final run
was approximately 200.4 seconds.

### 4.2 `graph_builder.py`

**Decision:** Represent the insurance relationships using a NetworkX
`MultiDiGraph`.

Known behavior: - Creates nodes for seven entity types. - Stores
`entity_type` and raw row data in node attributes. - Builds edges only
from `relationship_edges`. - Does not add extra edges merely because a
foreign key exists. - Validates that source and target nodes exist and
have expected types. - Uses `edge_id` as the multigraph edge key.

Correct usage:

``` python
graph = GraphBuilder().build(detection_data)
```

Do not use `GraphBuilder(data).build()`; the constructor takes no data
argument.

Recorded graph size: - 28,500 nodes. - 38,000 edges.

### 4.3 `edge_gap_detector.py`

**Purpose:** Find claimant pairs that share a normalized phone number
but do not have the corresponding `SHARES_PHONE` relationship edge.

Method:

``` python
EdgeGapDetector(graph).detect_missing_phone_edges(claimants)
```

Known behavior: - Groups claimants by normalized phone number. - Finds
claimant pairs missing the expected relationship edge. - Returns
findings with `entity_type`, `entity_id`, `related_entity_id`,
`indicator_type`, and evidence. - Evidence includes the shared phone and
claimant count.

Important scoring decision: - Both `entity_id` and `related_entity_id`
must receive the missing-phone signal.

Validation: - Detected 72 missing phone relationships. - This matched
the earlier business validation count of 72 claimant pairs.

### 4.4 `shared_provider_detector.py`

**Purpose:** Find providers connected to multiple claimants through
invoice and claim relationships.

Constructor and method:

``` python
SharedProviderDetector(graph, minimum_claimants=3).detect()
```

Known traversal:

``` text
Provider
  -> ISSUED_INVOICE
Invoice
  <- HAS_INVOICE
Claim
  <- FILED_CLAIM
Claimant
```

A provider finding is emitted when at least three distinct claimants are
connected through this path.

Evidence includes: - `distinct_claimant_count` - `claimant_ids` -
`claim_ids` - `invoice_ids`

Recorded result: - 500 provider findings.

Important observation: - This detector flags all 500 providers in the
synthetic dataset. - This is broad and may be noisy. - The decision was
to preserve the working detector rather than make an unvalidated change
under the deadline. - Do not interpret every shared provider as fraud.
Shared providers can be legitimate.

### 4.5 `duplicate_invoice_detector.py`

**Purpose:** Identify invoice numbers reused across different claimants.

Known behavior: - Groups invoice records by invoice number. - Checks
whether the invoice number appears across distinct claimants. - Produces
evidence containing invoice number, invoice count, distinct claimant
count, claimant IDs, and invoice-level details.

Recorded result: - 4 duplicate invoice-number findings. - Reused invoice
numbers were `INV-REUSED-001` through `INV-REUSED-004`. - Each reused
number appeared in three invoice records associated with three distinct
claimants. - Total affected invoice records: 12.

Validation: - `test_duplicate_invoice_detector.py` passed, with the
exact four expected reused invoice numbers.

### 4.6 `payment_anomaly_detector.py`

**Purpose:** Find inconsistencies between invoices, claim amounts,
approved amounts, and net payments.

Known behavior: - Uses invoice-to-payment relationships in the graph. -
Considers completed payments. - `PAYMENT` adds to the net amount. -
`REFUND` and `REVERSAL` subtract from the net amount.

Four recorded indicators:

  Indicator                              Findings
  ----------------------------------- -----------
  `PAID_INVOICE_UNDERPAYMENT`               1,979
  `PAYMENT_ON_REJECTED_INVOICE`             1,005
  `INVOICES_EXCEED_CLAIM_AMOUNT`            1,121
  `PAYMENTS_EXCEED_APPROVED_AMOUNT`         2,733
  **Total**                             **6,838**

Important interpretation decisions: - A payment anomaly is not
automatically fraud. - Underpayment may be an operational or
reconciliation issue. - Invoice totals exceeding claim amounts and
payments exceeding approved amounts are warning signals requiring
context. - These findings should be described as anomalies or
indicators, not proof of fraud.

Validation: - `test_payment_anomaly.py` passed. - The total of 6,838
matched the recorded business-validation counts.

### 4.7 `fraud_scorer.py`

**Purpose:** Aggregate detector findings into a risk score for each
entity.

Known scoring weights in the latest recorded scorer:

  Indicator                                Weight
  -------------------------------------- --------
  `DUPLICATE_INVOICE_ACROSS_CLAIMANTS`         30
  `MISSING_PHONE_RELATIONSHIP`                 15
  `PAYMENT_ON_REJECTED_INVOICE`                25
  `PAYMENTS_EXCEED_APPROVED_AMOUNT`            25
  `INVOICES_EXCEED_CLAIM_AMOUNT`               15
  `PAID_INVOICE_UNDERPAYMENT`                  10
  `SHARED_PROVIDER_CLUSTER`                    10

Additional recorded rules: - Duplicate signals of the same indicator
type for one entity are deduplicated. - A corroboration bonus of 10
points is added for each additional distinct signal, capped at 20. - A
shared-provider-only score is kept at 10. - Final score is capped at
100. - Risk levels are HIGH at 70 or above, MEDIUM at 40 or above, and
LOW below 40.

The scorer propagates findings to related entities: - Shared-provider
findings score the provider, claimants, claims, and invoices. -
Duplicate-invoice findings score the affected invoice, claimant, claim,
and provider. - Missing-phone findings score both claimant endpoints. -
Payment findings score the relevant entity.

The score is a **heuristic investigation-priority score**, not a
calibrated probability that fraud occurred.

### 4.8 `evaluator.py`

**Purpose:** Compare the scored entities with the separate ground-truth
answer key.

Known behavior: - Uses entity type and entity ID to match scored records
with ground-truth records. - Applies a configurable threshold. -
Calculates confusion matrix and overall precision, recall, F1, and
accuracy. - Calculates pattern-level metrics. - Reports detection rates
for planted networks.

Evaluation is performed only after detection and scoring have completed.

Important limitation: - The evaluation contains 320 labelled records. -
There are only 44 benign labels, all from `BENIGN_SHARED_ADDRESS`. -
Therefore, a 100% measured precision on this dataset does not establish
100% real-world precision. - Unlabelled entities are not automatically
known negatives.

------------------------------------------------------------------------

## 5. Testing and validation history

The following checks were recorded as passing: - Database loader test. -
Graph construction and relationship validation. - Missing phone
relationship detector: 72 findings. - Duplicate invoice detector: 4
findings. - Payment anomaly detector: 6,838 findings. - Full dataset
validation: 69 checks passed, 0 failed.

The graph builder produced: - 28,500 nodes. - 38,000 edges.

The complete pipeline later scored: - 11,167 entities.

------------------------------------------------------------------------

## 6. Threshold sweep and threshold decision

A threshold sweep was run against the 320 labelled ground-truth records.

Recorded results:

    Threshold    TP   FP   TN    FN   Precision   Recall       F1
  ----------- ----- ---- ---- ----- ----------- -------- --------
           10   276   22   22     0      0.9262   1.0000   0.9617
           20   207    0   44    69      1.0000   0.7500   0.8571
           25   207    0   44    69      1.0000   0.7500   0.8571
           30   207    0   44    69      1.0000   0.7500   0.8571
           35   177    0   44    99      1.0000   0.6413   0.7815
           40   104    0   44   172      1.0000   0.3768   0.5474
           45   104    0   44   172      1.0000   0.3768   0.5474
           50    60    0   44   216      1.0000   0.2174   0.3571

### Interpretation

-   Threshold 10 produced the highest F1 score in this sweep, but it
    incorrectly flagged 22 of the 44 benign labelled records.
-   Threshold 20 retained all 44 benign records as negative and detected
    207 of 276 suspicious records.
-   Thresholds 20, 25, and 30 produced identical results.
-   Higher thresholds reduced recall substantially.

### Practical decision

Threshold 20 was recommended as the working investigation threshold
because it offers a practical balance for prioritizing leads without
flagging the known benign shared-address records.

However, the final executed `main.py` output shown in the conversation
still used threshold 40. Its output explicitly reported:

``` text
Threshold : 40
```

The final `main.py` code also had `threshold: int = 40` and an argparse
default of 40. To use threshold 20, both defaults must be changed to 20,
or the command must explicitly pass `--threshold 20`.

Do not claim the final run used threshold 20 unless its output confirms
that.

------------------------------------------------------------------------

## 7. Final `main.py` execution

The final pipeline entry point was run from the project root:

``` powershell
python -m detection.main
```

The `main.py` implementation: 1. Creates the output directory. 2. Loads
all database data. 3. Removes `ground_truth` from the detection data
using `data.pop("ground_truth")`. 4. Builds the graph. 5. Runs all four
detectors. 6. Scores entities. 7. Evaluates risk scores against ground
truth. 8. Writes JSON output files. 9. Prints top-risk entities and a
run summary.

### Final observed execution counts

  Component                       Output
  ----------------------------- --------
  Graph nodes                     28,500
  Graph edges                     38,000
  Missing phone relationships         72
  Shared provider findings           500
  Duplicate invoice findings           4
  Payment anomaly findings         6,838
  Entities scored                 11,167

Risk levels in the observed run:

  Risk level     Entities
  ------------ ----------
  HIGH                991
  MEDIUM            2,783
  LOW               7,393

The observed run used threshold 40 and produced:

  Metric              Result
  ----------------- --------
  True positives         104
  False positives          0
  True negatives          44
  False negatives        172
  Precision           1.0000
  Recall              0.3768
  F1                  0.5474
  Accuracy            0.4625

### Pattern-wise evaluation in that run

-   `DUPLICATE_INVOICE_NUMBER`: 36 TP, 0 FN.
-   `SHARED_PROVIDER_CLUSTER`: 68 TP, 172 FN.
-   `BENIGN_SHARED_ADDRESS`: 44 TN, 0 FP.

The 28 planted networks had mixed detection rates: - Networks
`NET-000025` through `NET-000028`: 9/9 detected (100%). - Other networks
ranged approximately from 20% to 40% in the displayed summary.

### Output files

The run wrote these files to the `output/` folder:

  -----------------------------------------------------------------------
  File                                Purpose
  ----------------------------------- -----------------------------------
  `output/risk_scores.json`           Entity risk scores, risk levels,
                                      and supporting signals

  `output/evaluation_report.json`     Evaluation metrics and
                                      network/pattern results

  `output/detector_counts.json`       Finding counts from each detector
  -----------------------------------------------------------------------

The console confirmed:

``` text
Results written to: ...\insurance-investigation\output
```

------------------------------------------------------------------------

## 8. Issues encountered and fixes

### Import error: scorer module

Initial error:

``` text
ModuleNotFoundError: No module named 'detection.fraud_scoring'
Did you mean: 'detection.fraud_scorer'?
```

Fix:

``` python
from detection.fraud_scorer import FraudScorer
```

The actual file is `fraud_scorer.py`; no file rename was needed.

The evaluator import used in the working main file is:

``` python
from detection.evaluator import Evaluator
```

### Threshold mismatch

A threshold of 20 was recommended after the sweep, but the first
complete `main.py` implementation still defaulted to 40. The output
showed threshold 40. This was a configuration mismatch, not a detector
failure.

------------------------------------------------------------------------

## 9. Current status

### Completed

-   [x] Synthetic dataset generated and loaded into Neon.
-   [x] Database loader.
-   [x] NetworkX graph builder.
-   [x] Missing phone relationship detector.
-   [x] Shared provider detector.
-   [x] Duplicate invoice detector.
-   [x] Payment anomaly detector.
-   [x] Fraud scorer.
-   [x] Evaluator.
-   [x] Threshold sweep.
-   [x] End-to-end `detection/main.py`.
-   [x] JSON outputs written to `output/`.

### Next planned phase --- not yet implemented in the recorded history

The next proposed work is investigation and reporting:

  ------------------------------------------------------------------------------
  Planned file                               Planned responsibility
  ------------------------------------------ -----------------------------------
  `investigation/investigation_builder.py`   Group related high-risk entities
                                             into investigation cases

  `investigation/evidence_builder.py`        Assemble traceable evidence for
                                             each case

  `reporting/report_generator.py`            Export investigator-friendly JSON
                                             and CSV reports
  ------------------------------------------------------------------------------

These are plans, not completed modules. The conversation ended before
their implementation.

A case should contain: - Case ID. - Primary entity and related
entities. - Risk score and risk level. - Detection indicators. -
Supporting evidence. - Investigation status, such as OPEN. - Recommended
next step, such as MANUAL_REVIEW.

Do not label a case as confirmed fraud merely because its risk score is
high.

------------------------------------------------------------------------

## 10. Key decisions to preserve

1.  **Never use `ground_truth` in detection or scoring.** Only the
    evaluator receives it.
2.  Keep detection rules explainable and evidence-based.
3.  Use `relationship_edges` as the graph's relationship source; do not
    silently invent graph edges from foreign keys.
4.  Treat shared providers, shared contact details, and payment
    anomalies as leads requiring context.
5.  Do not rerun the generator with `--truncate`.
6.  Keep the scorer's risk score described as a heuristic, not a fraud
    probability.
7.  Keep evaluation limitations visible: only 320 labelled examples and
    44 benign labels are available.
8.  The observed end-to-end run used threshold 40; threshold 20 was the
    recommended setting from the sweep but must be explicitly
    configured.
9.  The next planned stage is investigation case creation, evidence
    assembly, and report generation.

------------------------------------------------------------------------

## 11. Commands used

Run the full detection pipeline from the project root:

``` powershell
python -m detection.main
```

Run with an explicit threshold and top-entity count:

``` powershell
python -m detection.main --threshold 20 --top 20
```

The threshold can be changed without changing the detection algorithms.

------------------------------------------------------------------------

## 12. Handoff summary

The detection folder is implemented and the end-to-end pipeline has run
successfully. It loads Neon data, constructs a 28,500-node / 38,000-edge
graph, runs four detectors, scores 11,167 entities, evaluates the scores
against a separately held-out answer key, and writes three JSON files.

The next development task is not another detector. It is to turn the
scored entities and their supporting signals into coherent investigation
cases, then generate evidence-backed reports that a human insurance
investigator can review.
