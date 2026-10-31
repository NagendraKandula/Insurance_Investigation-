
-- 1. Claim Status Events
CREATE TABLE claim_status_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id VARCHAR(30) NOT NULL
        REFERENCES claims(claim_id),
    from_status VARCHAR(30),
    to_status VARCHAR(30) NOT NULL,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor_id VARCHAR(30)
        REFERENCES users(user_id),
    remarks TEXT
);


-- 2. Payment Status Events
CREATE TABLE payment_status_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_id VARCHAR(30) NOT NULL
        REFERENCES payments(payment_id),
    from_status VARCHAR(30),
    to_status VARCHAR(30) NOT NULL,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor_id VARCHAR(30)
        REFERENCES users(user_id),
    remarks TEXT
);


-- 3. Investigation Events
CREATE TABLE investigation_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    investigation_id VARCHAR(30) NOT NULL
        REFERENCES investigations(investigation_id),
    actor_id VARCHAR(30)
        REFERENCES users(user_id),
    event_type VARCHAR(50) NOT NULL,
    previous_value TEXT,
    new_value TEXT,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 4. Claim Staging
CREATE TABLE claim_staging (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_claim_id VARCHAR(30) NOT NULL,
    claimant_id VARCHAR(30),
    referenced_policy_id VARCHAR(30),
    incident_id VARCHAR(30),
    claim_amount DECIMAL(12,2),
    claim_date TIMESTAMP,
    raw_record JSONB NOT NULL,
    validation_status VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 5. Data Generation Runs
CREATE TABLE data_generation_runs (
    generation_run_id VARCHAR(30) PRIMARY KEY,
    random_seed BIGINT NOT NULL,
    configuration JSONB NOT NULL,
    generator_version VARCHAR(50) NOT NULL,
    total_claimants INTEGER NOT NULL,
    total_policies INTEGER NOT NULL,
    total_claims INTEGER NOT NULL,
    total_providers INTEGER NOT NULL,
    total_edges INTEGER NOT NULL,
    dataset_checksum VARCHAR(128),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(30) NOT NULL
);
