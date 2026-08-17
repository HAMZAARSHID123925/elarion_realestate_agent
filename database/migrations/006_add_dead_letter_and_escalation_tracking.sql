-- ===========================================================================
-- Migration 006: Add Dead-Letter Jobs Table and Maintenance Escalation Columns
-- Phase 5 Production Hardening
-- ===========================================================================

-- 1. Create dead_letter_jobs table for persistent failure records
CREATE TABLE IF NOT EXISTS dead_letter_jobs (
    dead_letter_id  VARCHAR(50) PRIMARY KEY,
    job_name        VARCHAR(100) NOT NULL,
    status          VARCHAR(50) DEFAULT 'DEAD_LETTER',
    attempts        INTEGER NOT NULL DEFAULT 1,
    error_type      TEXT,
    error_message   TEXT,
    payload_summary TEXT,
    duration_ms     NUMERIC(10, 2) DEFAULT 0.00,
    started_at      TIMESTAMP,
    failed_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dead_letter_job_name ON dead_letter_jobs(job_name);
CREATE INDEX IF NOT EXISTS idx_dead_letter_failed_at ON dead_letter_jobs(failed_at);

-- 2. Add durable escalation tracking columns to maintenance_tickets table
ALTER TABLE maintenance_tickets ADD COLUMN IF NOT EXISTS last_escalated_at TIMESTAMP;
ALTER TABLE maintenance_tickets ADD COLUMN IF NOT EXISTS escalation_level VARCHAR(50);
