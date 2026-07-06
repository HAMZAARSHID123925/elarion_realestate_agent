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
    print(f"Connecting to database to initialize schema...")
    # Use sync connection for simple schema initialization
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            
            print("Dropping existing tables for clean stage 3 test...")
            await cur.execute("""
                DROP TABLE IF EXISTS audit_logs CASCADE;
                DROP TABLE IF EXISTS ticket_status_log CASCADE;
                DROP TABLE IF EXISTS maintenance_tickets CASCADE;
                DROP TABLE IF EXISTS tenants CASCADE;
                DROP TABLE IF EXISTS units CASCADE;
                DROP TABLE IF EXISTS properties CASCADE;
            """)
            
            print("Creating properties table...")
            await cur.execute("""
                CREATE TABLE properties (
                    property_id VARCHAR(50) PRIMARY KEY,
                    address TEXT NOT NULL
                );
            """)

            print("Creating units table...")
            await cur.execute("""
                CREATE TABLE units (
                    unit_id VARCHAR(50) PRIMARY KEY,
                    property_id VARCHAR(50) REFERENCES properties(property_id),
                    unit_number TEXT NOT NULL
                );
            """)

            print("Creating tenants table...")
            await cur.execute("""
                CREATE TABLE tenants (
                    tenant_id VARCHAR(50) PRIMARY KEY,
                    phone_or_email VARCHAR(100) UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    unit_id VARCHAR(50) REFERENCES units(unit_id)
                );
            """)

            print("Creating maintenance_tickets table...")
            await cur.execute("""
                CREATE TABLE maintenance_tickets (
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            print("Creating ticket_status_log table...")
            await cur.execute("""
                CREATE TABLE ticket_status_log (
                    log_id SERIAL PRIMARY KEY,
                    ticket_id VARCHAR(50) REFERENCES maintenance_tickets(ticket_id),
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            print("Creating audit_logs table...")
            await cur.execute("""
                CREATE TABLE audit_logs (
                    log_id SERIAL PRIMARY KEY,
                    action TEXT NOT NULL,
                    details TEXT,
                    actor TEXT,
                    before_state JSONB,
                    after_state JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            print("Seeding initial data for testing...")
            
            # Insert Property
            await cur.execute("INSERT INTO properties (property_id, address) VALUES ('P-100', '123 Main St Building')")
            
            # Insert Units
            await cur.execute("INSERT INTO units (unit_id, property_id, unit_number) VALUES ('U-4B', 'P-100', 'Apt 4B')")
            await cur.execute("INSERT INTO units (unit_id, property_id, unit_number) VALUES ('U-12', 'P-100', 'House 12')")
            
            # Insert Tenants
            await cur.execute("INSERT INTO tenants (tenant_id, phone_or_email, name, unit_id) VALUES ('T-100', '+923001234567', 'Hamza Arshid', 'U-4B')")
            await cur.execute("INSERT INTO tenants (tenant_id, phone_or_email, name, unit_id) VALUES ('T-101', 'tenant@example.com', 'John Doe', 'U-12')")

        await conn.commit()
    print("Database initialization and seeding completed successfully.")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_db())
