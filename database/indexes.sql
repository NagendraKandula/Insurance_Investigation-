
-- Claimant searches
CREATE INDEX IF NOT EXISTS idx_claimants_phone
ON claimants(normalized_phone);

CREATE INDEX IF NOT EXISTS idx_claimants_email
ON claimants(normalized_email);

CREATE INDEX IF NOT EXISTS idx_claimants_address
ON claimants(normalized_address);


-- Policy and claim relationships
CREATE INDEX IF NOT EXISTS idx_policies_claimant
ON policies(claimant_id);

CREATE INDEX IF NOT EXISTS idx_claims_claimant
ON claims(claimant_id);

CREATE INDEX IF NOT EXISTS idx_claims_policy
ON claims(policy_id);

CREATE INDEX IF NOT EXISTS idx_claims_incident
ON claims(incident_id);

CREATE INDEX IF NOT EXISTS idx_claims_status
ON claims(status);


-- Provider and financial records
CREATE INDEX IF NOT EXISTS idx_invoices_provider
ON invoices(provider_id);

CREATE INDEX IF NOT EXISTS idx_invoices_claim
ON invoices(claim_id);

CREATE INDEX IF NOT EXISTS idx_invoices_number
ON invoices(invoice_number);

CREATE INDEX IF NOT EXISTS idx_payments_invoice
ON payments(invoice_id);

CREATE INDEX IF NOT EXISTS idx_payments_date
ON payments(payment_date);


-- Graph relationships
CREATE INDEX IF NOT EXISTS idx_edges_source
ON relationship_edges(source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_edges_target
ON relationship_edges(target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_edges_relationship
ON relationship_edges(relationship_type);


-- Detection and investigation
CREATE INDEX IF NOT EXISTS idx_network_members_entity
ON network_members(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_indicators_entity
ON fraud_indicators(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_investigations_status
ON investigations(status);


-- Audit and validation
CREATE INDEX IF NOT EXISTS idx_claim_events_claim
ON claim_status_events(claim_id);

CREATE INDEX IF NOT EXISTS idx_payment_events_payment
ON payment_status_events(payment_id);

CREATE INDEX IF NOT EXISTS idx_exceptions_status
ON data_exceptions(resolution_status);
