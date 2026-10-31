
CREATE TABLE invoices (
    invoice_id VARCHAR(30) PRIMARY KEY,
    provider_id VARCHAR(30) NOT NULL
        REFERENCES providers(provider_id),
    claim_id VARCHAR(30) NOT NULL
        REFERENCES claims(claim_id),
    invoice_number VARCHAR(100) NOT NULL,
    invoice_amount DECIMAL(12,2) NOT NULL,
    invoice_date TIMESTAMP NOT NULL,
    due_date DATE,
    description TEXT,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (invoice_amount >= 0)
);

CREATE TABLE payments (
    payment_id VARCHAR(30) PRIMARY KEY,
    invoice_id VARCHAR(30) NOT NULL
        REFERENCES invoices(invoice_id),
    transaction_reference VARCHAR(100) UNIQUE,
    payment_amount DECIMAL(12,2) NOT NULL,
    payment_date TIMESTAMP NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    transaction_type VARCHAR(30) NOT NULL
        CHECK (transaction_type IN ('PAYMENT', 'REFUND', 'REVERSAL')),
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (payment_amount >= 0)
);
