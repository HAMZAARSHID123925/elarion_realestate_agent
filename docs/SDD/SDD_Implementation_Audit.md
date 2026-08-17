# SDD Scope & Implementation Audit — Elarion Real Estate Agent Platform

> **Document Path:** `docs/SDD/SDD_Implementation_Audit.md`
> **Status:** Active Architectural Audit
> **Scope:** Project-Wide Platform Review

---

## 1. Executive Summary

This audit documents the transition of the project documentation from a legacy single-domain focus (*"Rent Reminder Workflow"*) to the complete, authoritative **4-Domain Multi-Workflow Architecture** matching the active codebase.

The Elarion backend consists of 4 major business workflow domains coordinated by a 3-layer architecture:
1. **Maintenance Workflow** (`langgraph_agent/app/core_workflows/maintenance/`)
2. **Rent Reminder Workflow** (`langgraph_agent/app/core_workflows/rent_reminder/`)
3. **FAQ & Property Search Workflow** (`langgraph_agent/app/core_workflows/faq/`)
4. **Lease Expiry & Rent Renewal Workflow** (`langgraph_agent/app/core_workflows/rent_renewal/`)

---

## 2. Multi-Workflow Scope Matrix

| Domain / Layer | Current Code Implementation | Database Entities | SDD Representation | Phase 4 API Scope | Phase 5 Scheduling Scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Maintenance** | LangGraph slot-filling, emergency detection, vendor matching, `human_approval_node` with `interrupt()`, MCP tools. | `vendors`, `maintenance_tickets`, `ticket_status_log`, `assignment_attempts` (000 DDL) | Documented in `Maintenance_Workflow_Architecture.md` | `/api/v1/maintenance/tickets` (create, list, get) | Stale unassigned ticket monitoring |
| **Rent Reminder** | LangGraph decision rules (Day 30/35), live tenant hydration, `reminder_send_node`, escalation. | `tenants` (overdue columns, reminder timestamps, manual hold) | Documented in `00_SDD_Master.md`, `03_Database_Wiring.md` | `/api/v1/workflows/rent-reminder/run`, `/evaluate`, `/api/v1/tenants` | Daily batch scan (08:00 AM) |
| **FAQ & Search** | LangGraph RAG query engine, ChromaDB knowledge base, property search tools, `mcp_client.py`. | `properties` (city, type, price indexes) | Documented in `FAQ_Property_Search_Architecture.md` | `/api/v1/properties` (search, detail) | Request-driven (no periodic scan) |
| **Rent Renewal** | 5 sub-domains: `lease_expiry`, `renewal_reminder`, `renewal_intent`, `document_tracking`, `human_escalation`. 13 graph nodes. | Migrations 001–005: `leases`, `lease_expiry_events`, `renewal_reminders`, `renewal_intents`, `renewal_documents`, `human_escalations` | Documented in `Lease_Expiry_Renewal_Architecture.md` | `/api/v1/workflows/lease-expiry/scan`, `/renewal-reminder/scan` | Daily lease expiry scan (07:00 AM) & renewal reminder scan (08:30 AM) |
| **Shared Platform** | Channels (WhatsApp 8000, Vapi 8001, Email 8002), Layer 2 Orchestrator, Master Pipeline Supervisor (`pipeline.py`), Checkpointer. | PostgreSQL connection pool (`psycopg_pool`) / `AsyncPostgresSaver` | Documented in `00_SDD_Master.md` to `12_Backend_Testing_Strategy.md` | `/health`, `/ready`, `/api/v1/pipeline/message` | Centralized scheduler daemon / alert notifications |

---

## 3. Implementation Status Across Phases

* **Phase 1 — Stabilization**: `[COMPLETED & VERIFIED]` Docker Compose merge conflict resolved, `.env` discovery hardened, 104 baseline tests passed.
* **Phase 2 — Database Unification**: `[COMPLETED & VERIFIED]` Migration `000_init_base_tables.sql` created, canonical PostgreSQL `TenantRepository` created, `rent_models.py` unified, 105 tests passed.
* **Phase 3 — Live Data Wiring**: `[COMPLETED & VERIFIED]` Live state hydration and missing-tenant handling implemented in `payment_check_node`, dynamic response generation wired in `run_rent_reminder`, 109 tests passed.
* **Phase 4 — API Layer**: `[TARGET]` Implement unified FastAPI server (`app/server.py`) exposing modular routers for Health, Tenants, Properties, Maintenance, Workflows, and Pipeline Ingestion.
* **Phase 5 — Scheduling & Alerting**: `[PLANNED]` Centralize recurring scan jobs (Rent Reminder, Lease Expiry, Renewal Reminder) and emergency/escalation alerts.
* **Phase 6 — Hardening**: `[PLANNED]` Connection pool tuning, security sanitization, rate limiting, and production Docker containerization.

---

## 4. Contract for Future Phases

All subsequent implementation phases (Phase 4, Phase 5, Phase 6) must maintain full multi-workflow compatibility across all four domains. No phase may restrict its scope or implementation to a single workflow.
