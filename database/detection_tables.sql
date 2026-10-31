
-- 1. Networks
CREATE TABLE networks (
    network_id VARCHAR(30) PRIMARY KEY,
    network_name VARCHAR(150),
    network_type VARCHAR(30) NOT NULL DEFAULT 'UNCLASSIFIED',
    network_score DECIMAL(6,4),
    detection_method VARCHAR(100) NOT NULL,
    algorithm_version VARCHAR(50),
    member_count INTEGER NOT NULL DEFAULT 0,
    edge_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (network_score IS NULL OR
           (network_score >= 0 AND network_score <= 1)),
    CHECK (member_count >= 0),
    CHECK (edge_count >= 0)
);


-- 2. Network Members
CREATE TABLE network_members (
    network_id VARCHAR(30) NOT NULL
        REFERENCES networks(network_id),

    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,

    role_in_network VARCHAR(50),
    membership_score DECIMAL(6,4),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (network_id, entity_type, entity_id),

    CHECK (membership_score IS NULL OR
           (membership_score >= 0 AND membership_score <= 1))
);


-- 3. Fraud Indicators
CREATE TABLE fraud_indicators (
    indicator_id VARCHAR(30) PRIMARY KEY,

    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,

    indicator_type VARCHAR(100) NOT NULL,
    anomaly_score DECIMAL(6,4),
    severity VARCHAR(30) NOT NULL,

    evidence JSONB,

    detection_method VARCHAR(100) NOT NULL,
    algorithm_version VARCHAR(50),

    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (anomaly_score IS NULL OR
           (anomaly_score >= 0 AND anomaly_score <= 1))
);
