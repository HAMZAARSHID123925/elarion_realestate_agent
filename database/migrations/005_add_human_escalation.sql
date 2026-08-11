-- ============================================================================
-- Migration 005: Add Human Escalation & Manager Intervention (Phase 5, Workflow #4)
--
-- Creates:
--   1. human_escalations      — persistent tracking of cases escalated for human intervention
--   2. escalation_audit_logs  — audit history for escalation lifecycle events
--
-- This migration is ADDITIVE — it does not modify or drop any existing tables.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. human_escalations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS human_escalations (
    escalation_id        SERIAL PRIMARY KEY,
    lease_id             VARCHAR(50) NOT NULL REFERENCES leases(lease_id),
    tenant_id            VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id),
    property_id          VARCHAR(50) REFERENCES properties(property_id),
    escalation_reason    VARCHAR(50) NOT NULL,
        -- RENEWAL_APPROVAL_REQUIRED | NEGOTIATION_REQUIRED | TENANT_REQUESTED_HUMAN
        -- EXCEPTION_REQUEST | DOCUMENT_ISSUE | WORKFLOW_ERROR | OTHER
    escalation_priority  VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
        -- LOW | MEDIUM | HIGH | URGENT
    status               VARCHAR(30) NOT NULL DEFAULT 'OPEN',
        -- OPEN | PENDING_MANAGER_ACTION | RESOLVED | CLOSED | REJECTED
    description          TEXT,
    assigned_to          VARCHAR(50) DEFAULT 'Property Manager',
    notified_at          TIMESTAMP,
    manager_action       VARCHAR(50),
        -- APPROVE_CONTINUATION | REJECT_CONTINUATION | REQUEST_MORE_INFORMATION | NEGOTIATE | CLOSE_CASE
    manager_notes        TEXT,
    resolved_at          TIMESTAMP,
    metadata             JSONB DEFAULT '{}',
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_human_escalations_lease ON human_escalations(lease_id);
CREATE INDEX IF NOT EXISTS idx_human_escalations_status ON human_escalations(status);
CREATE INDEX IF NOT EXISTS idx_human_escalations_assigned ON human_escalations(assigned_to, status);

-- ---------------------------------------------------------------------------
-- 2. escalation_audit_logs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS escalation_audit_logs (
    audit_id             SERIAL PRIMARY KEY,
    escalation_id        INTEGER REFERENCES human_escalations(escalation_id),
    lease_id             VARCHAR(50),
    tenant_id            VARCHAR(50),
    event_type           VARCHAR(50) NOT NULL,
        -- ESCALATION_CREATED | MANAGER_NOTIFIED | MANAGER_ACTION_RECEIVED | WORKFLOW_RESUMED | ESCALATION_RESOLVED
    actor                VARCHAR(50) NOT NULL DEFAULT 'system',
    details              JSONB DEFAULT '{}',
    timestamp            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_escalation_audit_escalation ON escalation_audit_logs(escalation_id);
CREATE INDEX IF NOT EXISTS idx_escalation_audit_lease ON escalation_audit_logs(lease_id);
