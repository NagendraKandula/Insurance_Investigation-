# LLM Usage and Prompt History
## Project: Insurance Fraud Investigation System

### 1. Objective

I used an LLM as a development assistant during the database design and implementation phase of the Insurance Fraud Investigation System.

The objective was to translate the given business problem into a structured relational database design that supports insurance entities, financial transactions, relationship analysis, fraud indicators, investigations and evaluation.

The prompts below are reconstructed summaries of the prompts and interactions used during development, not a verbatim export of the conversation.

---

### 2. Prompt History

#### Prompt 1 – Understanding the problem statement

**Prompt:**

"Analyze the insurance fraud detection problem statement. Explain the business workflow, important entities, actors, relationships and expected system outputs. Identify what needs to be stored in the database."

**AI assistance:**
- Explained the insurance investigation workflow.
- Identified claimants, policies, claims, incidents, providers, invoices and payments.
- Identified the need for relationship analysis, fraud indicators, investigations and evaluation.

**My contribution:**
Reviewed the proposed entities against the original challenge requirements and selected the entities necessary for the implementation.

#### Prompt 2 – Database table identification

**Prompt:**

"Based on the insurance fraud investigation problem statement, design a relational database schema. Divide the system into appropriate tables. Include primary keys, foreign keys, column names, data types, constraints and relationships."

**AI assistance:**
- Proposed the core relational tables.
- Suggested primary-key and foreign-key relationships.
- Identified supporting tables for event history, investigations, data validation and synthetic data generation.

**My contribution:**
Reviewed the proposed schema and finalized 20 tables based on the project's requirements.

#### Prompt 3 – Handling suspicious relationships

**Prompt:**

"How should I store relationships between different entities such as claimants, claims, providers, invoices and payments so that I can later perform graph-based fraud detection using Python NetworkX?"

**AI assistance:**
- Suggested a relationship_edges table.
- Explained typed relationships between different entity types.
- Recommended storing relationship type, source, target and confidence.
- Explained why polymorphic references require additional validation.

**My contribution:**
Selected PostgreSQL as the source of truth and planned to load relationship records into NetworkX for graph analysis.

#### Prompt 4 – Handling ground truth and data exceptions

**Prompt:**

"How should I design database tables for planted fraud patterns, ground-truth labels and data-quality exceptions? The detection algorithm should not access ground-truth labels."

**AI assistance:**
- Suggested separate ground_truth and data_exceptions tables.
- Explained why invalid foreign-key references should be kept in a staging table rather than inserted into valid relational records.
- Recommended separating fraud indicators from data-integrity exceptions.

**My contribution:**
Kept ground truth separate from detection inputs and included claim_staging for invalid or incomplete claim references.

#### Prompt 5 – Database schema implementation

**Prompt:**

"Help me implement the finalized PostgreSQL schema incrementally. Explain how to create the tables in dependency order and execute SQL files against my Neon PostgreSQL database using Python."

**AI assistance:**
- Provided PostgreSQL CREATE TABLE statements.
- Explained primary keys, foreign keys, data types and constraints.
- Suggested Python scripts using psycopg and python-dotenv to execute SQL files.

**My contribution:**
Created the project structure, configured the Neon connection, executed the SQL scripts and verified that all 20 tables were created.

#### Prompt 6 – Database indexing

**Prompt:**

"Review the indexes required for an insurance fraud investigation database. Identify missing indexes on foreign-key columns and fields frequently used for entity matching, relationship lookup and investigation queries."

**AI assistance:**
- Recommended indexes for normalized claimant and provider contact details.
- Suggested indexes for claims, invoices, payments, relationship edges and investigation records.
- Explained that PostgreSQL does not automatically index referencing foreign-key columns.

**My contribution:**
Reviewed the suggested indexes and executed the selected indexes in Neon. Verified their creation using pg_indexes.

#### Prompt 7 – Database validation

**Prompt:**

"How can I verify that my database relationships work correctly? Provide sample INSERT statements for a claimant, policy, incident and claim, followed by a SQL JOIN query."

**AI assistance:**
- Provided sample records.
- Explained insertion order based on foreign-key dependencies.
- Generated a JOIN query to validate the relationships.

**My contribution:**
Executed the INSERT statements and JOIN query in Neon SQL Editor and verified that the connected records were returned successfully.

---

### 3. Where AI Accelerated My Work

AI helped accelerate:
- Translating the business problem into a relational database structure.
- Identifying the required entities and relationships.
- Designing supporting tables for investigations, ground truth and data exceptions.
- Drafting SQL table definitions and indexes.
- Creating Python scripts for PostgreSQL connectivity and SQL execution.
- Preparing database validation queries.

### 4. Where I Relied Heavily on AI

I relied heavily on AI for initial schema suggestions, SQL syntax, table dependency ordering and database implementation guidance.

AI-generated suggestions were treated as proposals rather than automatically accepted decisions.

### 5. What I Personally Reviewed, Changed and Validated

I personally:
- Reviewed the proposed 20-table schema against the challenge requirements.
- Selected PostgreSQL with Neon as the database.
- Chose NetworkX for the planned graph analysis.
- Reviewed foreign-key relationships and constraints.
- Kept invoice_number non-unique to support duplicate-invoice detection.
- Separated ground-truth labels from detection inputs.
- Used claim_staging for invalid policy references.
- Reviewed and added relevant indexes.
- Connected Python to Neon PostgreSQL.
- Executed all 20 table definitions and verified their existence.
- Inserted sample records and validated relationships using SQL JOINs.
- Verified index creation through PostgreSQL system catalogs.

### 6. Current Implementation Status

| Activity | Status |
|---|---|
| Business problem analysis | Completed |
| Database design | Completed |
| 20 PostgreSQL tables | Created |
| Database indexes | Created |
| Neon connection | Verified |
| Sample data insertion | Verified |
| SQL JOIN validation | Successful |
| Synthetic data generation | Not started |
| NetworkX fraud detection | Not started |
| Evaluation and metrics | Not started |

### 7. Transparency Statement

The LLM was used as a development assistant for analysis, schema suggestions, SQL drafting and implementation guidance. I reviewed and adapted its suggestions, executed the database operations myself and validated the results against my Neon PostgreSQL database.

The database implementation and validation results are based on actual execution, not merely AI-generated code or claims of completion.