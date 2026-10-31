
-- 1. Investigations
CREATE TABLE investigations (
    investigation_id VARCHAR(30) PRIMARY KEY,

    network_id VARCHAR(30)
        REFERENCES networks(network_id),

    title VARCHAR(200) NOT NULL,
    description TEXT,

    priority VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL,

    assigned_to VARCHAR(30)
        REFERENCES users(user_id),

    findings TEXT,
    decision VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);


-- 2. Ground Truth
CREATE TABLE ground_truth (
    ground_truth_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    planted_network_id VARCHAR(30),

    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,

    pattern_type VARCHAR(100) NOT NULL,
    role_in_network VARCHAR(50),

    issue_type VARCHAR(100),
    expected_label VARCHAR(30) NOT NULL,

    description TEXT,
    generation_run_id VARCHAR(30),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 3. Data Exceptions
CREATE TABLE data_exceptions (
    exception_id VARCHAR(30) PRIMARY KEY,

    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50),

    issue_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,

    referenced_entity_type VARCHAR(50),
    referenced_entity_id VARCHAR(50),

    severity VARCHAR(30) NOT NULL,
    resolution_status VARCHAR(30) NOT NULL,

    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);
