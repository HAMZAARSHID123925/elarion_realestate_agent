-- ============================================================================
-- Migration 003: Add Renewal Intent & Manager Notifications (Phase 3, Workflow #4)
--
-- Creates:
--   1. renewal_intents       — persistent record of tenant renewal intent interpretations
--   2. manager_notifications — manager review tasks for Human-in-the-Loop review
--
-- This migration is ADDITIVE — it does not modify or drop any existing tables.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. renewal_intents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS renewal_intents (
    intent_id        SERIAL PRIMARY KEY,
    lease_id         VARCHAR(50) NOT NULL REFERENCES leases(lease_id),
    tenant_id        VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id),
    tenant_response  TEXT NOT NULL,
    intent           VARCHAR(30) NOT NULL,
        -- YES | NO | UNCLEAR | NEGOTIATION
    confidence       REAL DEFAULT 1.0,
    reasoning        TEXT,
    renewal_status   VARCHAR(50) NOT NULL,
        -- PENDING_MANAGER_REVIEW | TENANT_DECLINED | CLARIFICATION_REQUIRED | ESCALATED
    requested_term   INTEGER,
    proposed_rent    NUMERIC(12, 2),
    metadata         JSONB DEFAULT '{}',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_renewal_intents_lease ON renewal_intents(lease_id);
CREATE INDEX IF NOT EXISTS idx_renewal_intents_intent ON renewal_intents(intent);

-- ---------------------------------------------------------------------------
-- 2. manager_notifications
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS manager_notifications (
    notification_id  SERIAL PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL,
        -- RENEWAL_INTENT_YES | RENEWAL_NEGOTIATION | RENEWAL_ESCALATION
    lease_id         VARCHAR(50) NOT NULL REFERENCES leases(lease_id),
    tenant_id        VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id),
    property_id      VARCHAR(50) REFERENCES properties(property_id),
    title            VARCHAR(255) NOT NULL,
    status           VARCHAR(30) NOT NULL DEFAULT 'PENDING',
        -- PENDING | REVIEWED | APPROVED | REJECTED | RESOLVED
    details          JSONB DEFAULT '{}',
    assigned_to      VARCHAR(50) DEFAULT 'Property Manager',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_manager_notifs_lease ON manager_notifications(lease_id);
CREATE INDEX IF NOT EXISTS idx_manager_notifs_status ON manager_notifications(status);
