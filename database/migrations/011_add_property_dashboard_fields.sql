-- ============================================================================
-- Migration 011: Add Property Dashboard Fields
-- (Properties Page — Chunk 5)
--
-- Adds:
--   1. status       — Active / Inactive toggle for dashboard property cards
--   2. units_count  — Number of units in each property
--
-- This migration is ADDITIVE — it does not modify or drop any existing columns.
-- ============================================================================

-- 1. Add status column (Active / Inactive)
ALTER TABLE properties ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Active';

-- 2. Add units_count column
ALTER TABLE properties ADD COLUMN IF NOT EXISTS units_count INTEGER DEFAULT 0;

-- 3. Backfill units_count from the units table
UPDATE properties p
SET units_count = COALESCE(
    (SELECT COUNT(*) FROM units u WHERE u.property_id = p.property_id),
    0
);

-- 4. Ensure all existing properties are Active
UPDATE properties SET status = 'Active' WHERE status IS NULL;
