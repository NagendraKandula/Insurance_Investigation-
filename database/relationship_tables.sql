
CREATE TABLE relationship_edges (
    edge_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(50) NOT NULL,

    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(50) NOT NULL,

    relationship_type VARCHAR(50) NOT NULL,

    confidence DECIMAL(5,4),

    source VARCHAR(100) NOT NULL,

    valid_from TIMESTAMP,
    valid_to TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (confidence IS NULL OR
           (confidence >= 0 AND confidence <= 1)),

    CHECK (valid_to IS NULL OR
           valid_from IS NULL OR valid_to >= valid_from)
);
