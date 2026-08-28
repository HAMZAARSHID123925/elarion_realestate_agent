-- Migration 012: Allow NULL on property_id for FK tables (tenants, leases, lease_expiry_events)
-- This allows disassociating property records upon property deletion without violating foreign key constraints.

ALTER TABLE tenants ALTER COLUMN property_id DROP NOT NULL;
ALTER TABLE leases ALTER COLUMN property_id DROP NOT NULL;
ALTER TABLE lease_expiry_events ALTER COLUMN property_id DROP NOT NULL;
