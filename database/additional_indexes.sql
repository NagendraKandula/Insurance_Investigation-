
-- Provider matching indexes
CREATE INDEX IF NOT EXISTS idx_providers_phone
ON providers(normalized_phone);

CREATE INDEX IF NOT EXISTS idx_providers_email
ON providers(normalized_email);

CREATE INDEX IF NOT EXISTS idx_providers_address
ON providers(normalized_address);


-- Claim status history
CREATE INDEX IF NOT EXISTS idx_claim_events_claim_time
ON claim_status_events(claim_id, event_time);


-- Investigation lookup by network
CREATE INDEX IF NOT EXISTS idx_investigations_network
ON investigations(network_id);


-- Staging validation lookup
CREATE INDEX IF NOT EXISTS idx_staging_policy
ON claim_staging(referenced_policy_id);


-- Optional: combined provider and invoice lookup
CREATE INDEX IF NOT EXISTS idx_invoices_provider_number
ON invoices(provider_id, invoice_number);
