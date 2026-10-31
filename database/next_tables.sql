CREATE TABLE policies (
    policy_id VARCHAR(30) PRIMARY KEY,
    claimant_id VARCHAR(30) NOT NULL
        REFERENCES claimants(claimant_id),
    policy_number VARCHAR(50) UNIQUE NOT NULL,
    policy_type VARCHAR(50) NOT NULL,
    coverage_amount DECIMAL(12,2) NOT NULL,
    premium_amount DECIMAL(12,2) NOT NULL,
    deductible_amount DECIMAL(12,2) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (coverage_amount >= 0),
    CHECK (premium_amount >= 0),
    CHECK (deductible_amount >= 0),
    CHECK (end_date >= start_date)
);
CREATE TABLE incidents (
    incident_id VARCHAR(30) PRIMARY KEY,
    incident_type VARCHAR(50) NOT NULL,
    incident_date TIMESTAMP NOT NULL,
    reported_at TIMESTAMP NOT NULL,
    description TEXT,
    location TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    estimated_loss DECIMAL(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (estimated_loss IS NULL OR estimated_loss >= 0)
);
CREATE TABLE claims (
    claim_id VARCHAR(30) PRIMARY KEY,
    claimant_id VARCHAR(30) NOT NULL
        REFERENCES claimants(claimant_id),
    policy_id VARCHAR(30) NOT NULL
        REFERENCES policies(policy_id),
    incident_id VARCHAR(30) NOT NULL
        REFERENCES incidents(incident_id),
    claim_number VARCHAR(50) UNIQUE NOT NULL,
    claim_amount DECIMAL(12,2) NOT NULL,
    approved_amount DECIMAL(12,2),
    claim_date TIMESTAMP NOT NULL,
    description TEXT,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (claim_amount >= 0),
    CHECK (approved_amount IS NULL OR approved_amount >= 0)
);
