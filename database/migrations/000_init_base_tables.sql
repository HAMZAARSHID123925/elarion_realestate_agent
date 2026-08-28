-- ============================================================================
-- Migration 000: Initialize Canonical Base Tables (Phase 2 Database Unification)
--
-- Creates canonical PostgreSQL tables:
--   1. properties            — managed properties
--   2. units                 — rental units per property
--   3. tenants               — tenant records, rent due dates, payment/reminder status
--   4. vendors               — maintenance service vendors
--   5. maintenance_tickets   — maintenance complaint records
--   6. ticket_status_log     — ticket state history
--   7. audit_logs            — general operation audit logs
--   8. assignment_attempts   — vendor dispatch attempt records
--
-- This migration establishes the base schema required by migrations 001–005.
-- It is idempotent (IF NOT EXISTS).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. properties
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS properties (
    property_id     VARCHAR(50) PRIMARY KEY,
    title           TEXT,
    address         TEXT NOT NULL,
    city            VARCHAR(100),
    property_type   VARCHAR(50) DEFAULT 'apartment',
    price_lakhs     NUMERIC(12, 2) DEFAULT 0.00,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_properties_city ON properties(city);

-- ---------------------------------------------------------------------------
-- 2. units
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS units (
    unit_id         VARCHAR(50) PRIMARY KEY,
    property_id     VARCHAR(50) NOT NULL REFERENCES properties(property_id),
    unit_number     VARCHAR(50) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_units_property_id ON units(property_id);

-- ---------------------------------------------------------------------------
-- 3. tenants
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id           VARCHAR(50) PRIMARY KEY,
    property_id         VARCHAR(50) REFERENCES properties(property_id),
    unit_id             VARCHAR(50) REFERENCES units(unit_id),
    tenant_name         TEXT NOT NULL,
    name                TEXT,
    tenant_phone        VARCHAR(50),
    phone_or_email      VARCHAR(100),
    property_address    TEXT,
    rent_due_date       DATE,
    last_payment_date   DATE,
    rent_amount         NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    payment_status      VARCHAR(50) DEFAULT 'overdue',
    reminder_30_sent_at TIMESTAMP,
    reminder_5_sent_at  TIMESTAMP,
    response_received   BOOLEAN DEFAULT FALSE,
    human_escalated     BOOLEAN DEFAULT FALSE,
    escalation_reason   TEXT,
    manual_hold         BOOLEAN DEFAULT FALSE,
    last_reminder_status VARCHAR(50) DEFAULT 'none',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tenants_property_id ON tenants(property_id);
CREATE INDEX IF NOT EXISTS idx_tenants_payment_status ON tenants(payment_status);
CREATE INDEX IF NOT EXISTS idx_tenants_due_date ON tenants(rent_due_date);

-- ---------------------------------------------------------------------------
-- 4. vendors
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id               VARCHAR(50) PRIMARY KEY,
    name                    TEXT NOT NULL,
    phone                   VARCHAR(50) NOT NULL,
    category                TEXT NOT NULL,
    service_area            TEXT NOT NULL,
    is_contracted           BOOLEAN DEFAULT FALSE,
    contracted_property_id  VARCHAR(50) REFERENCES properties(property_id),
    accepts_emergency       BOOLEAN DEFAULT FALSE,
    capacity                INTEGER DEFAULT 3,
    active_jobs             INTEGER DEFAULT 0,
    active                  BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 5. maintenance_tickets
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS maintenance_tickets (
    ticket_id           VARCHAR(50) PRIMARY KEY,
    tenant_id           VARCHAR(50) REFERENCES tenants(tenant_id),
    property_id         VARCHAR(50) REFERENCES properties(property_id),
    unit_id             VARCHAR(50) REFERENCES units(unit_id),
    category            TEXT NOT NULL,
    description         TEXT,
    urgency             TEXT,
    permission_to_enter TEXT,
    pets_present        TEXT,
    status              TEXT DEFAULT 'OPEN',
    source_channel      TEXT,
    created_by          TEXT,
    idempotency_key     TEXT UNIQUE NOT NULL,
    vendor_id           VARCHAR(50) REFERENCES vendors(vendor_id),
    assignment_status   TEXT DEFAULT 'UNASSIGNED',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 6. ticket_status_log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ticket_status_log (
    log_id      SERIAL PRIMARY KEY,
    ticket_id   VARCHAR(50) REFERENCES maintenance_tickets(ticket_id),
    old_status  TEXT,
    new_status  TEXT NOT NULL,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 7. audit_logs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id          SERIAL PRIMARY KEY,
    action          TEXT NOT NULL,
    details         TEXT,
    actor           TEXT,
    before_state    JSONB,
    after_state     JSONB,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 8. assignment_attempts
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assignment_attempts (
    attempt_id      SERIAL PRIMARY KEY,
    ticket_id       VARCHAR(50) REFERENCES maintenance_tickets(ticket_id),
    vendor_id       VARCHAR(50) REFERENCES vendors(vendor_id),
    strategy_used   TEXT NOT NULL,
    result          TEXT NOT NULL,
    reason          TEXT,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 9. Baseline Sample Seed Data (Idempotent)
-- ---------------------------------------------------------------------------
INSERT INTO properties (property_id, title, address, city, property_type, price_lakhs)
VALUES
    ('P-100', 'Gulberg Heights Building', '123 Main St Building, Gulberg, Lahore', 'Lahore', 'apartment', 180.00),
    ('P-201', 'Gulberg Heights Flat 4B', 'Flat 4B, Gulberg Heights, Lahore', 'Lahore', 'apartment', 75.00),
    ('P-202', 'DHA Phase 5 Villa 12', 'Villa 12, DHA Phase 5, Lahore', 'Lahore', 'house', 420.00),
    ('P-203', 'F-10 Apartment 302', 'Apartment 302, F-10, Islamabad', 'Islamabad', 'apartment', 95.00),
    ('P-204', 'Bahria Town House 88', 'House 88, Bahria Town, Karachi', 'Karachi', 'house', 280.00),
    ('P-205', 'Clifton Studio 15', 'Studio 15, Clifton, Karachi', 'Karachi', 'apartment', 38.00)
ON CONFLICT (property_id) DO NOTHING;

INSERT INTO units (unit_id, property_id, unit_number)
VALUES
    ('U-4B', 'P-100', 'Apt 4B'),
    ('U-12', 'P-100', 'House 12'),
    ('U-201', 'P-201', 'Unit 4B'),
    ('U-202', 'P-202', 'Unit 12'),
    ('U-203', 'P-203', 'Unit 302'),
    ('U-204', 'P-204', 'Unit 88'),
    ('U-205', 'P-205', 'Unit 15')
ON CONFLICT (unit_id) DO NOTHING;

INSERT INTO tenants (
    tenant_id, property_id, unit_id, tenant_name, name, tenant_phone, phone_or_email,
    property_address, rent_due_date, last_payment_date, rent_amount, payment_status,
    reminder_30_sent_at, reminder_5_sent_at, response_received, human_escalated,
    escalation_reason, manual_hold, last_reminder_status
) VALUES
    ('T-100', 'P-100', 'U-4B', 'Hamza Arshid', 'Hamza Arshid', '+923001234567', '+923001234567',
     '123 Main St Building, Apt 4B, Lahore', '2026-07-01', NULL, 75000.00, 'overdue',
     NULL, NULL, FALSE, FALSE, NULL, FALSE, 'none'),
    ('T-101', 'P-201', 'U-201', 'Ali Ahmed', 'Ali Ahmed', '0300-1112223', '0300-1112223',
     'Flat 4B, Gulberg Heights, Lahore', '2026-07-06', NULL, 75000.00, 'overdue',
     NULL, NULL, FALSE, FALSE, NULL, FALSE, 'none'),
    ('T-102', 'P-202', 'U-202', 'Zainab Bibi', 'Zainab Bibi', '0321-4445556', '0321-4445556',
     'Villa 12, DHA Phase 5, Lahore', '2026-06-25', NULL, 120000.00, 'reminder_sent',
     '2026-07-31 08:00:00', NULL, FALSE, FALSE, NULL, FALSE, 'reminder_sent'),
    ('T-103', 'P-203', 'U-203', 'Hamza Malik', 'Hamza Malik', '0333-7778889', '0333-7778889',
     'Apartment 302, F-10, Islamabad', '2026-06-20', NULL, 95000.00, 'followup_sent',
     '2026-07-25 08:00:00', '2026-08-03 08:00:00', FALSE, FALSE, NULL, FALSE, 'followup_sent'),
    ('T-104', 'P-204', 'U-204', 'Usman Tariq', 'Usman Tariq', '0345-9990001', '0345-9990001',
     'House 88, Bahria Town, Karachi', '2026-06-15', NULL, 110000.00, 'overdue',
     NULL, NULL, FALSE, FALSE, NULL, TRUE, 'none'),
    ('T-105', 'P-205', 'U-205', 'Sana Farooq', 'Sana Farooq', '0311-2223334', '0311-2223334',
     'Studio 15, Clifton, Karachi', '2026-07-01', '2026-07-02', 50000.00, 'paid',
     NULL, NULL, FALSE, FALSE, NULL, FALSE, 'none')
ON CONFLICT (tenant_id) DO NOTHING;
