-- ============================================================================
-- Migration 001: Add Lease Expiry Tracking (Phase 1, Workflow #4)
--
-- Creates:
--   1. leases              — core lease records (NEW — no lease table existed)
--   2. lease_expiry_events — idempotent expiry window events for Phase 2
--   3. lease_expiry_scan_runs — observability / audit for scheduler runs
--
-- This migration is ADDITIVE — it does not modify or drop any existing tables.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. leases
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS leases (
    lease_id        VARCHAR(50) PRIMARY KEY,
    tenant_id       VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id),
    property_id     VARCHAR(50) NOT NULL REFERENCES properties(property_id),
    unit_id         VARCHAR(50) REFERENCES units(unit_id),
    lease_start_date DATE NOT NULL,
    lease_end_date   DATE NOT NULL,
    monthly_rent     NUMERIC(12, 2) DEFAULT 0.00,
    status           VARCHAR(30) NOT NULL DEFAULT 'active',
        -- active | terminated | cancelled | renewed | expired | draft
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for the Phase 1 scan: active leases with expiry window
CREATE INDEX IF NOT EXISTS idx_leases_status ON leases(status);
CREATE INDEX IF NOT EXISTS idx_leases_end_date ON leases(lease_end_date);
CREATE INDEX IF NOT EXISTS idx_leases_status_end_date ON leases(status, lease_end_date);

-- ---------------------------------------------------------------------------
-- 2. lease_expiry_events
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lease_expiry_events (
    id              SERIAL PRIMARY KEY,
    event_name      VARCHAR(100) NOT NULL,
        -- e.g. LEASE_EXPIRY_90_DAYS, LEASE_EXPIRY_60_DAYS, LEASE_EXPIRED
    lease_id        VARCHAR(50) NOT NULL REFERENCES leases(lease_id),
    tenant_id       VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id),
    property_id     VARCHAR(50) NOT NULL REFERENCES properties(property_id),
    expiry_date     DATE NOT NULL,
    days_remaining  INTEGER NOT NULL,
    window_days     INTEGER NOT NULL,
        -- the configured window value crossed (90, 60, 30, 7, or 0 for expired)
    event_date      DATE NOT NULL,
        -- the business date the scan ran on
    event_status    VARCHAR(30) NOT NULL DEFAULT 'PENDING',
        -- PENDING -> CONSUMED / FAILED (Phase 2 owns transitions beyond PENDING)
    run_id          VARCHAR(50) NOT NULL,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Idempotency constraint: exactly one event per (lease, window) pair
CREATE UNIQUE INDEX IF NOT EXISTS uq_lease_expiry_event
    ON lease_expiry_events(lease_id, window_days);

-- Index for Phase 2 consumption: find PENDING events
CREATE INDEX IF NOT EXISTS idx_expiry_events_status
    ON lease_expiry_events(event_status);

-- ---------------------------------------------------------------------------
-- 3. lease_expiry_scan_runs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lease_expiry_scan_runs (
    run_id          VARCHAR(50) PRIMARY KEY,
    started_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at     TIMESTAMP,
    trigger_type    VARCHAR(30) NOT NULL DEFAULT 'manual',
        -- manual | scheduled
    leases_scanned  INTEGER DEFAULT 0,
    events_created  INTEGER DEFAULT 0,
    duplicates_skipped INTEGER DEFAULT 0,
    errors_count    INTEGER DEFAULT 0,
    status          VARCHAR(30) NOT NULL DEFAULT 'RUNNING',
        -- RUNNING | COMPLETED | FAILED
    error_details   JSONB DEFAULT '[]',
    window_config   JSONB DEFAULT '[]',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 4. Seed sample leases for development/testing
-- ---------------------------------------------------------------------------
INSERT INTO leases (lease_id, tenant_id, property_id, unit_id, lease_start_date, lease_end_date, monthly_rent, status)
VALUES
    -- Lease expiring in ~90 days -> should trigger 90-day window
    ('L-001', 'T-100', 'P-100', 'U-4B',
     CURRENT_DATE - INTERVAL '275 days',
     CURRENT_DATE + INTERVAL '90 days',
     75000.00, 'active'),

    -- Lease expiring in ~60 days -> should trigger 90-day and 60-day windows
    ('L-002', 'T-101', 'P-100', 'U-12',
     CURRENT_DATE - INTERVAL '305 days',
     CURRENT_DATE + INTERVAL '60 days',
     120000.00, 'active'),

    -- Lease expiring in ~30 days -> should trigger 90, 60, 30-day windows
    ('L-003', 'T-100', 'P-100', 'U-4B',
     CURRENT_DATE - INTERVAL '335 days',
     CURRENT_DATE + INTERVAL '30 days',
     95000.00, 'active'),

    -- Lease expiring in ~7 days -> should trigger all windows
    ('L-004', 'T-101', 'P-100', 'U-12',
     CURRENT_DATE - INTERVAL '358 days',
     CURRENT_DATE + INTERVAL '7 days',
     110000.00, 'active'),

    -- Already expired lease still marked active (data quality edge case)
    ('L-005', 'T-100', 'P-100', 'U-4B',
     CURRENT_DATE - INTERVAL '400 days',
     CURRENT_DATE - INTERVAL '5 days',
     50000.00, 'active'),

    -- Terminated lease -> should be excluded from scan
    ('L-006', 'T-101', 'P-100', 'U-12',
     CURRENT_DATE - INTERVAL '200 days',
     CURRENT_DATE + INTERVAL '30 days',
     85000.00, 'terminated'),

    -- Lease far in the future (2 years out) -> no window match
    ('L-007', 'T-100', 'P-100', 'U-4B',
     CURRENT_DATE - INTERVAL '30 days',
     CURRENT_DATE + INTERVAL '730 days',
     65000.00, 'active')
ON CONFLICT (lease_id) DO NOTHING;
