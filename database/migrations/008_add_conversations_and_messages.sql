-- ============================================================================
-- Migration 008: Add Conversations & Conversation Messages Tables
-- (Phase 1 Dashboard Live Transcript Engine)
--
-- Creates:
--   1. conversations          — high-level chat sessions per tenant/channel
--   2. conversation_messages — detailed message turn history & system events
--   3. Sample seed conversations matching TenantFlow UI screenshots
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. conversations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id     VARCHAR(50) PRIMARY KEY,
    tenant_id           VARCHAR(50) REFERENCES tenants(tenant_id),
    property_id         VARCHAR(50) REFERENCES properties(property_id),
    unit_id             VARCHAR(50) REFERENCES units(unit_id),
    contact_name        TEXT NOT NULL,
    channel             VARCHAR(30) NOT NULL DEFAULT 'WhatsApp', -- WhatsApp | Email | Voice | Web
    intent              VARCHAR(100) DEFAULT 'General Inquiry',
    urgency             VARCHAR(20) DEFAULT 'Normal',            -- Critical | High | Normal | Low
    status              VARCHAR(30) DEFAULT 'AI Resolved',      -- AI Resolved | Escalated | In Progress | Pending Review
    workflow_triggered  VARCHAR(100) DEFAULT 'Resident Support',
    human_intervention VARCHAR(50) DEFAULT 'None',              -- None | Property Manager | Human Required
    is_reviewed         BOOLEAN DEFAULT FALSE,
    last_message_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_property ON conversations(property_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_urgency ON conversations(urgency);

-- ---------------------------------------------------------------------------
-- 2. conversation_messages
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversation_messages (
    message_id          SERIAL PRIMARY KEY,
    conversation_id     VARCHAR(50) NOT NULL REFERENCES conversations(conversation_id),
    sender_type         VARCHAR(20) NOT NULL, -- tenant | ai | system
    sender_name         TEXT NOT NULL,
    content             TEXT NOT NULL,
    system_event        TEXT,                 -- e.g., 'SYSTEM: INTENT CLASSIFIED & PRIORITY UPDATED'
    timestamp           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON conversation_messages(conversation_id);

-- ---------------------------------------------------------------------------
-- 3. Baseline Seed Conversations Matching Dashboard UI Screenshots
-- ---------------------------------------------------------------------------
INSERT INTO conversations (
    conversation_id, tenant_id, property_id, unit_id, contact_name,
    channel, intent, urgency, status, workflow_triggered, human_intervention, is_reviewed, last_message_at
) VALUES
    ('TF-10482', 'T-100', 'P-100', 'U-4B', 'Sarah Johnson',
     'WhatsApp', 'Maintenance Request', 'High', 'AI Resolved', 'Maintenance Request', 'None', FALSE, '2026-08-17 10:43:00'),
    ('TF-10483', 'T-101', 'P-201', 'U-201', 'John Davis',
     'Email', 'Rent Follow-up', 'High', 'Escalated', 'Rent Follow-up', 'Property Manager', FALSE, '2026-08-17 10:31:00'),
    ('TF-10484', 'T-105', 'P-205', 'U-205', 'David Smith',
     'Website', 'Lease Question', 'Normal', 'AI Resolved', 'Resident Support', 'None', TRUE, '2026-08-17 10:18:00')
ON CONFLICT (conversation_id) DO NOTHING;

INSERT INTO conversation_messages (
    conversation_id, sender_type, sender_name, content, system_event, timestamp
) VALUES
    ('TF-10482', 'tenant', 'Sarah Johnson', 'The AC isn''t working again. It''s incredibly hot in here.', NULL, '2026-08-17 10:42:00'),
    ('TF-10482', 'ai', 'TenantFlow AI', 'I''m sorry to hear that, Sarah. Let''s get this sorted out. Is the unit completely off and unresponsive, or is it running but blowing warm air? I''ll collect these details to create a maintenance request for you.', NULL, '2026-08-17 10:42:30'),
    ('TF-10482', 'tenant', 'Sarah Johnson', 'It''s completely stopped. The thermostat screen is blank too.', NULL, '2026-08-17 10:43:00'),
    ('TF-10482', 'system', 'SYSTEM', 'Priority updated to High based on HVAC failure during high heat.', 'SYSTEM: INTENT CLASSIFIED & PRIORITY UPDATED', '2026-08-17 10:43:05'),
    ('TF-10482', 'ai', 'TenantFlow AI', 'Got it. A blank thermostat usually means a power issue to the unit. I have logged ticket #492 and dispatched our primary HVAC vendor.', NULL, '2026-08-17 10:43:10')
ON CONFLICT DO NOTHING;
