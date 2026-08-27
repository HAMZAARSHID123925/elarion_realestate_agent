-- Migration 009: Add Automations Table and Initial Seed Data
-- Enables dynamic PostgreSQL persistence for workflow automations,
-- escalation conditions, active channels, status, scope, and parameters.

CREATE TABLE IF NOT EXISTS automations (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Active', -- 'Active' | 'Inactive'
    description TEXT,
    tagline TEXT,
    handles JSONB NOT NULL DEFAULT '[]'::jsonb,
    channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    escalation_conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
    scope VARCHAR(255) DEFAULT 'All Properties (42)',
    properties_count INT DEFAULT 42,
    icon_type VARCHAR(100) DEFAULT 'maintenance',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_automations_status ON automations(status);

-- Seed initial 5 core automations if not present
INSERT INTO automations (id, name, status, description, tagline, handles, channels, escalation_conditions, scope, properties_count, icon_type)
VALUES
(
    'maintenance_request',
    'Maintenance Request',
    'Active',
    'Handles: Collect details, classify urgency, ticket creation, vendor assignment.',
    'End-to-end ticket triage, vendor dispatch, and tenant notification.',
    '["Collect details", "classify urgency", "ticket creation", "vendor assignment"]'::jsonb,
    '["WhatsApp", "Email", "Voice", "Web"]'::jsonb,
    '["Emergency detected (e.g., flood)", "AI confidence < 85%", "Estimate > $500 requires sign-off", "Primary vendor unavailable"]'::jsonb,
    'All Properties (42)',
    42,
    'maintenance'
),
(
    'rent_reminder',
    'Rent Reminder',
    'Active',
    'Handles: Automated follow-ups, payment link generation, late fee calculation.',
    'Automated payment follow-ups, late fee calculation, and tenant disputes.',
    '["Automated follow-ups", "payment link generation", "late fee calculation"]'::jsonb,
    '["WhatsApp", "Email", "SMS"]'::jsonb,
    '["> 15 days past due", "Tenant dispute initiated", "Payment plan request detected"]'::jsonb,
    '3 Properties',
    3,
    'rent'
),
(
    'resident_support',
    'Resident Support',
    'Active',
    'Handles: General FAQ, community rules, amenity booking assistance.',
    'General FAQ, community rules, and amenity booking assistance.',
    '["General FAQ", "community rules", "amenity booking assistance"]'::jsonb,
    '["WhatsApp", "Web", "Email"]'::jsonb,
    '["Complex policy questions", "Frustration sentiment detected", "Multiple clarification loops"]'::jsonb,
    'All Properties (42)',
    42,
    'support'
),
(
    'lease_renewal',
    'Lease Renewal',
    'Active',
    'Handles: Document collection, signature chasing, pre-renewal intent checks.',
    'Document collection, signature chasing, and pre-renewal intent checks.',
    '["Document collection", "signature chasing", "pre-renewal intent checks"]'::jsonb,
    '["Email", "WhatsApp", "Web"]'::jsonb,
    '["Tenant declines renewal", "Documents missing after deadline", "Negotiation requested"]'::jsonb,
    'All Properties (42)',
    42,
    'lease'
),
(
    'owner_reporting',
    'Owner Reporting',
    'Active',
    'Handles: Automated monthly portfolio generation, variance explanations.',
    'Automated monthly portfolio reports with variance analysis and delivery.',
    '["Automated monthly portfolio generation", "variance explanations"]'::jsonb,
    '["Email", "Web Portal"]'::jsonb,
    '["Occupancy variance > 10%", "Maintenance cost spike detected", "Owner requests custom period"]'::jsonb,
    'All Properties (42)',
    42,
    'reporting'
)
ON CONFLICT (id) DO NOTHING;
