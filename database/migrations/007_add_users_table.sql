-- ============================================================================
-- Migration 007: Initialize Users Table (Phase 8 Security & Authentication)
--
-- Creates canonical PostgreSQL table:
--   1. users            — dashboard users for authentication
--
-- This migration establishes the base schema required for dashboard authentication.
-- It is idempotent (IF NOT EXISTS).
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id         VARCHAR(50) PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            VARCHAR(50) DEFAULT 'read_only',
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ---------------------------------------------------------------------------
-- Baseline Seed Data
-- ---------------------------------------------------------------------------
-- Note: 'password' hashed with bcrypt:
-- $2b$12$Kix3hO8S.F41S.Kz7eK7VOPs4.9.4A.3G/pD0sY2O5O/9t2m9A1J6
-- Users should change this immediately in production.
INSERT INTO users (user_id, email, password_hash, role, active)
VALUES
    ('USR-ADMIN1', 'admin@elarion.com', '$2b$12$Kix3hO8S.F41S.Kz7eK7VOPs4.9.4A.3G/pD0sY2O5O/9t2m9A1J6', 'admin', TRUE),
    ('USR-MGR1', 'manager@elarion.com', '$2b$12$Kix3hO8S.F41S.Kz7eK7VOPs4.9.4A.3G/pD0sY2O5O/9t2m9A1J6', 'read_only', TRUE)
ON CONFLICT (email) DO NOTHING;
