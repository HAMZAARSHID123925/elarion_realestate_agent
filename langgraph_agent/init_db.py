"""
Database Schema Initialization & Migration Helper.

Safeguards against accidental production data loss:
- By default (SAFE MODE), runs `CREATE TABLE IF NOT EXISTS` without dropping any existing tables or data.
- Full table drops/re-seeding require `DANGEROUS_ALLOW_DB_RESET=true` in environment.
"""
import os
import asyncio
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set in .env")


async def init_db():
    allow_reset = os.getenv("DANGEROUS_ALLOW_DB_RESET", "false").lower() in ("true", "1", "yes")

    print("Connecting to PostgreSQL database to verify schema...")
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            if allow_reset:
                print("[RESET MODE] DANGEROUS_ALLOW_DB_RESET is active. Dropping and rebuilding tables...")
                await cur.execute("""
                    DROP TABLE IF EXISTS assignment_attempts CASCADE;
                    DROP TABLE IF EXISTS audit_logs CASCADE;
                    DROP TABLE IF EXISTS ticket_status_log CASCADE;
                    DROP TABLE IF EXISTS maintenance_tickets CASCADE;
                    DROP TABLE IF EXISTS vendors CASCADE;
                    DROP TABLE IF EXISTS tenants CASCADE;
                    DROP TABLE IF EXISTS units CASCADE;
                    DROP TABLE IF EXISTS properties CASCADE;
                """)
            else:
                print("[SAFE MODE] Ensuring tables exist with CREATE TABLE IF NOT EXISTS...")

            print("Ensuring properties table...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    property_id VARCHAR(50) PRIMARY KEY,
                    title TEXT,
                    address TEXT NOT NULL,
                    city TEXT,
                    property_type TEXT,
                    price_lakhs NUMERIC(12, 2) DEFAULT 0,
                    status VARCHAR(50) DEFAULT 'Active',
                    units_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            print("Ensuring units table...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS units (
                    unit_id VARCHAR(50) PRIMARY KEY,
                    property_id VARCHAR(50) REFERENCES properties(property_id),
                    unit_number TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            print("Ensuring tenants table...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id VARCHAR(50) PRIMARY KEY,
                    phone_or_email VARCHAR(100) UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    unit_id VARCHAR(50) REFERENCES units(unit_id),
                    property_address TEXT,
                    rent_due_date DATE,
                    last_payment_date DATE,
                    rent_amount NUMERIC(12, 2) DEFAULT 0.00,
                    payment_status VARCHAR(50) DEFAULT 'overdue',
                    reminder_30_sent_at TIMESTAMP,
                    reminder_5_sent_at TIMESTAMP,
                    response_received BOOLEAN DEFAULT FALSE,
                    human_escalated BOOLEAN DEFAULT FALSE,
                    escalation_reason TEXT,
                    manual_hold BOOLEAN DEFAULT FALSE,
                    last_reminder_status VARCHAR(50) DEFAULT 'none',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            print("Ensuring vendors table...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS vendors (
                    vendor_id VARCHAR(50) PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    category TEXT NOT NULL,
                    service_area TEXT NOT NULL,
                    is_contracted BOOLEAN DEFAULT FALSE,
                    contracted_property_id VARCHAR(50) REFERENCES properties(property_id),
                    accepts_emergency BOOLEAN DEFAULT FALSE,
                    capacity INTEGER DEFAULT 3,
                    active_jobs INTEGER DEFAULT 0,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            print("Ensuring maintenance_tickets table...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_tickets (
                    ticket_id VARCHAR(50) PRIMARY KEY,
                    tenant_id VARCHAR(50) REFERENCES tenants(tenant_id),
                    property_id VARCHAR(50) REFERENCES properties(property_id),
                    unit_id VARCHAR(50) REFERENCES units(unit_id),
                    category TEXT NOT NULL,
                    description TEXT,
                    urgency TEXT,
                    permission_to_enter TEXT,
                    pets_present TEXT,
                    status TEXT DEFAULT 'OPEN',
                    source_channel TEXT,
                    created_by TEXT,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    vendor_id VARCHAR(50) REFERENCES vendors(vendor_id),
                    assignment_status TEXT DEFAULT 'UNASSIGNED',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            print("Ensuring ticket_status_log table...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS ticket_status_log (
                    log_id SERIAL PRIMARY KEY,
                    ticket_id VARCHAR(50) REFERENCES maintenance_tickets(ticket_id),
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            print("Ensuring audit_logs table...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id SERIAL PRIMARY KEY,
                    action TEXT NOT NULL,
                    details TEXT,
                    actor TEXT,
                    before_state JSONB,
                    after_state JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            print("Ensuring assignment_attempts table...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS assignment_attempts (
                    attempt_id SERIAL PRIMARY KEY,
                    ticket_id VARCHAR(50) REFERENCES maintenance_tickets(ticket_id),
                    vendor_id VARCHAR(50) REFERENCES vendors(vendor_id),
                    strategy_used TEXT NOT NULL,
                    result TEXT NOT NULL,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            if allow_reset:
                print("Seeding initial reference records...")
                await cur.execute("INSERT INTO properties (property_id, address) VALUES ('P-100', '123 Main St Building') ON CONFLICT DO NOTHING;")
                await cur.execute("INSERT INTO units (unit_id, property_id, unit_number) VALUES ('U-4B', 'P-100', 'Apt 4B') ON CONFLICT DO NOTHING;")
                await cur.execute("INSERT INTO units (unit_id, property_id, unit_number) VALUES ('U-12', 'P-100', 'House 12') ON CONFLICT DO NOTHING;")
                await cur.execute("INSERT INTO tenants (tenant_id, phone_or_email, name, unit_id) VALUES ('T-100', '+923001234567', 'Hamza Arshid', 'U-4B') ON CONFLICT DO NOTHING;")
                await cur.execute("INSERT INTO tenants (tenant_id, phone_or_email, name, unit_id) VALUES ('T-101', 'tenant@example.com', 'John Doe', 'U-12') ON CONFLICT DO NOTHING;")
                await cur.execute("""
                    INSERT INTO vendors (vendor_id, name, phone, category, service_area, is_contracted, contracted_property_id, accepts_emergency, capacity, active_jobs, active)
                    VALUES
                        ('V-100', 'Ali Plumbing Co.',       '+923001112221', 'plumbing',   'P-100', TRUE,  'P-100', TRUE,  5, 1, TRUE),
                        ('V-101', 'Rapid Fix Plumbers',      '+923001112222', 'plumbing',   'P-100', FALSE, NULL,    TRUE,  3, 0, TRUE),
                        ('V-102', 'Bright Spark Electrical', '+923001112223', 'electrical', 'P-100', FALSE, NULL,    TRUE,  4, 0, TRUE),
                        ('V-103', 'CoolAir HVAC Services',   '+923001112224', 'hvac',       'P-100', FALSE, NULL,    FALSE, 2, 2, TRUE),
                        ('V-104', 'Handy Malik Services',    '+923001112225', 'general',    'P-100', FALSE, NULL,    FALSE, 2, 1, TRUE),
                        ('V-105', 'CityWide On-Call Pool',   '+923001112226', 'general',    'FALLBACK_POOL', FALSE, NULL, TRUE, 10, 0, TRUE)
                    ON CONFLICT DO NOTHING;
                """)

            await conn.commit()
    print("Database schema verification and setup completed successfully.")


if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_db())
