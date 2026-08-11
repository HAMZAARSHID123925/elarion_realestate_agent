-- ============================================================================
-- Migration 002: Add Renewal Reminders Tracking (Phase 2, Workflow #4)
--
-- Creates:
--   1. renewal_reminders — persistent history of renewal reminder dispatches
--
-- This migration is ADDITIVE — it does not modify or drop any existing tables.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. renewal_reminders
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS renewal_reminders (
    reminder_id     SERIAL PRIMARY KEY,
    event_id        INTEGER REFERENCES lease_expiry_events(id),
    lease_id        VARCHAR(50) NOT NULL REFERENCES leases(lease_id),
    tenant_id       VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id),
    property_id     VARCHAR(50) REFERENCES properties(property_id),
    channel         VARCHAR(30) NOT NULL DEFAULT 'email',
        -- email | whatsapp | sms | system
    recipient       VARCHAR(100) NOT NULL,
    reminder_type   VARCHAR(50) NOT NULL,
        -- LEASE_EXPIRY_90_DAYS | LEASE_EXPIRY_60_DAYS | LEASE_EXPIRY_30_DAYS | LEASE_EXPIRY_7_DAYS | LEASE_EXPIRED
    message_body    TEXT NOT NULL,
    status          VARCHAR(30) NOT NULL DEFAULT 'SENT',
        -- SENT | DELIVERED | FAILED | MOCKED
    sent_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message   TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for querying reminder history and preventing duplicate sends
CREATE INDEX IF NOT EXISTS idx_renewal_reminders_lease_id ON renewal_reminders(lease_id);
CREATE INDEX IF NOT EXISTS idx_renewal_reminders_event_id ON renewal_reminders(event_id);
CREATE INDEX IF NOT EXISTS idx_renewal_reminders_lease_type ON renewal_reminders(lease_id, reminder_type);
CREATE INDEX IF NOT EXISTS idx_renewal_reminders_sent_at ON renewal_reminders(sent_at);
