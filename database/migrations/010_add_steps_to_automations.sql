-- Migration 010: Add steps JSONB column to automations table
-- Allows property managers to customize execution flow timeline steps in PostgreSQL

ALTER TABLE automations ADD COLUMN IF NOT EXISTS steps JSONB DEFAULT '[]'::jsonb;
