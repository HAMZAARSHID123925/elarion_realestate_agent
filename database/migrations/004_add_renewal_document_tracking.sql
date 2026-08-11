-- ============================================================================
-- Migration 004: Add Renewal Document Tracking (Phase 4, Workflow #4)
--
-- Creates:
--   1. renewal_documents — stores submitted renewal documents, URLs, and verification state
--
-- This migration is ADDITIVE — it does not modify or drop any existing tables.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. renewal_documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS renewal_documents (
    document_id       SERIAL PRIMARY KEY,
    lease_id          VARCHAR(50) NOT NULL REFERENCES leases(lease_id),
    tenant_id         VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id),
    doc_type          VARCHAR(50) NOT NULL,
        -- signed_lease_agreement | cnic_copy | proof_of_income | deposit_receipt | other
    file_name         VARCHAR(255) NOT NULL,
    file_url          TEXT,
    status            VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED',
        -- PENDING | SUBMITTED | VERIFIED | REJECTED
    uploaded_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_at       TIMESTAMP,
    verified_by       VARCHAR(50),
    rejection_reason  TEXT,
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_renewal_docs_lease ON renewal_documents(lease_id);
CREATE INDEX IF NOT EXISTS idx_renewal_docs_tenant ON renewal_documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_renewal_docs_type ON renewal_documents(lease_id, doc_type);
CREATE INDEX IF NOT EXISTS idx_renewal_docs_status ON renewal_documents(status);
