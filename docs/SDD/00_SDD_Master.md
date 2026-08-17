# Software Design Document — Elarion Real Estate Agent Platform

> **Document Path:** `docs/SDD/00_SDD_Master.md`
> **Version:** 2.0 (Project-Wide Multi-Workflow Architecture)
> **Status:** Active
> **Audience:** Developers, AI Coding Agents, Reviewers, Future Maintainers

---

## 1. Document Purpose

This document is the **Master Software Design Document (SDD)** for the **Elarion Real Estate Agent Platform** backend. It serves as the single entry point and authoritative reference for all backend architectural decisions, component relationships, implementation phases, and engineering principles across all workflow domains.

The Elarion platform coordinates four core business workflows through an intelligent 3-layer architecture:
1. **Maintenance Workflow** — Slot-filling intake, emergency detection, vendor matching, and human-in-the-loop dispatch.
2. **Rent Reminder Workflow** — Automated overdue rent monitoring, timed reminders (Day 30/35), intent handling, and escalation.
3. **FAQ & Property Search Workflow** — Knowledge base RAG querying, tenant policy assistance, and MCP-powered property search.
4. **Lease Expiry & Rent Renewal Workflow** — 5-stage lifecycle tracking (lease expiry, renewal reminders, tenant intent, document verification, and manager escalation).

---

## 2. System Overview

The Elarion Real Estate Agent backend is an autonomous, multi-channel property management system that ingests tenant and client requests across WhatsApp, Voice (Vapi), and Email, normalizes them, routes them to specialized LangGraph domain subgraphs, and synchronizes state with a unified PostgreSQL database.

**The Four Core Workflow Domains:**

1. **Maintenance Domain (`app/core_workflows/maintenance/`)**:
   - Ingests maintenance complaints across all channels.
   - Extracts slots: category, description, urgency, permission to enter, pets present.
   - Triggers human manager approval via LangGraph `interrupt()` for non-contracted/high-cost vendors.
   - Persists tickets to `maintenance_tickets`, `ticket_status_log`, and `assignment_attempts`.

2. **Rent Reminder Domain (`app/core_workflows/rent_reminder/`)**:
   - Evaluates overdue tenants and tracks payment status.
   - Dispatches timed reminders (Reminder #1 on Day 30 overdue, Follow-up #2 on Day 35).
   - Escalates chronic non-payment to property managers while respecting `manual_hold` overrides.
   - Persists state changes to `tenants` table.

3. **FAQ & Property Search Domain (`app/core_workflows/faq/`)**:
   - Answers tenant questions regarding building rules, payment policies, office hours, and move-in procedures.
   - Connects to ChromaDB vector knowledge base for RAG retrieval.
   - Queries property listings database via MCP tool client (`mcp_server.py`).

4. **Lease Expiry & Rent Renewal Domain (`app/core_workflows/rent_renewal/`)**:
   - Evaluates approaching lease expirations (90, 60, 30, 7-day windows) via `lease_expiry`.
   - Dispatches structured renewal reminders via `renewal_reminder`.
   - Classifies tenant renewal intentions (accept, negotiate, terminate) via `renewal_intent`.
   - Tracks document upload requests and verification via `document_tracking`.
   - Handles manager review and manual interventions via `human_escalation`.

**Shared Platform Infrastructure:**
- **Layer 1 (Channel Ingestion)**: Inbound webhooks for WhatsApp (Meta Cloud API), Voice (Vapi API), and Email (Resend Webhook API).
- **Layer 2 (Supervisor / Orchestrator)**: Intent classification (`orchestrator_graph`), urgency detection, and entity extraction.
- **Layer 3 (Domain Execution)**: Isolated LangGraph subgraphs invoked via wrapper nodes in `app/department_nodes.py`.
- **Master Pipeline Supervisor (`app/pipeline.py`)**: Persistent session management with `AsyncPostgresSaver` / `MemorySaver`, conversation resumption, and unified response normalization.
- **Unified Database (`database/`)**: Authoritative PostgreSQL database configured via `DATABASE_URL` with versioned migrations `000` through `005`.

---

## 3. System Goals

1. **Multi-Domain Autonomy** — Autonomously process maintenance, rent reminders, support FAQs, and lease renewals without manual routing.
2. **Unified Source of Truth** — Centralize all persistent business state (properties, units, tenants, vendors, tickets, leases, renewal stages) in PostgreSQL.
3. **Deterministic & Agentic Execution** — Combine rule-based decision nodes with LLM-powered slot extraction and intent classification.
4. **Stateful Conversation Continuity** — Ensure multi-turn conversations and paused approval workflows survive process restarts via durable checkpointing.
5. **Channel-Agnostic Processing** — Normalize all channel inputs into `UnifiedRequest` and format responses into `UnifiedResponse`.
6. **Strict Domain Isolation** — Keep domain workflow states and business logic encapsulated within their respective sub-packages.
7. **Comprehensive Observability & Safety** — Log structured audit trails without leaking PII, passwords, or payment credentials.

---

## 4. Platform Architecture & Layering

```text
                                  [ INBOUND CHANNELS ]
                       WhatsApp (8000)  │  Vapi Voice (8001)  │  Email (8002)
                                        │
                                        ▼
                                [ UNIFIED REQUEST ]
                       NormalizedRequest / UnifiedRequest
                                        │
                                        ▼
                   ┌──────────────────────────────────────────┐
                   │        LAYER 2: ORCHESTRATOR GRAPH       │
                   │  - Intent Node (LLM Extraction)          │
                   │  - Rules Engine Node (Urgency / Route)   │
                   └────────────────────┬─────────────────────┘
                                        │
                                        ▼
                   ┌──────────────────────────────────────────┐
                   │    LAYER 3: MASTER PIPELINE SUPERVISOR   │
                   │           (app/pipeline.py)              │
                   │  - department_router (Command Dispatch)  │
                   │  - Persistent Checkpointer (Postgres)    │
                   └───────┬────────────┬───────────┬─────────┘
                           │            │           │         │
             ┌─────────────┘            │           │         └──────────────┐
             ▼                          ▼           ▼                        ▼
  ┌────────────────────┐      ┌────────────┐  ┌───────────┐      ┌─────────────────────────┐
  │    MAINTENANCE     │      │    RENT    │  │   FAQ &   │      │      RENT RENEWAL       │
  │     WORKFLOW       │      │  REMINDER  │  │  SEARCH   │      │     (5 SUB-DOMAINS)     │
  │ - Slot Extraction  │      │ - Day 30   │  │ - RAG KB  │      │ - Lease Expiry Scan     │
  │ - Vendor Match     │      │ - Day 35   │  │ - MCP Tool│      │ - Renewal Reminders     │
  │ - Human Approval   │      │ - Escalate │  │ - Listings│      │ - Intent Classification │
  └─────────┬──────────┘      └─────┬──────┘  └─────┬─────┘      │ - Document Tracking     │
            │                       │               │            │ - Human Escalation      │
            │                       │               │            └────────────┬────────────┘
            ▼                       ▼               ▼                         ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │                       UNIFIED POSTGRESQL DATABASE & REPOSITORIES                       │
  │   - Base: properties, units, tenants, vendors, maintenance_tickets (Migration 000)     │
  │   - Renewal: leases, expiry_events, reminders, intents, docs, escalations (001–005)   │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Major Architectural Components

| Component | Responsibility | Relevant Files / Sub-packages | Detailed SDD |
| :--- | :--- | :--- | :--- |
| **Unified Database & Migrations** | Authoritative persistence for all 4 domains | `database/migrations/000_*.sql` to `005_*.sql`, `tenant_repository.py` | [03_Database_Wiring.md](./03_Database_Wiring.md) |
| **API & Service Layer** | REST endpoints for health, tenants, properties, tickets, and workflow triggers | `app/server.py`, `app/api/routers/` | [04_API_And_Service_Layer.md](./04_API_And_Service_Layer.md) |
| **Event & Ingestion Pipeline** | Multi-channel request normalization and routing | `input_channels/`, `app/orchestrator/`, `app/pipeline.py` | [05_Event_And_Pipeline_Architecture.md](./05_Event_And_Pipeline_Architecture.md) |
| **Workflow Runner & Master Engine** | Subgraph supervisor, session resumption, and checkpointer | `app/department_nodes.py`, `app/checkpointer.py` | [06_WorkflowRunner_Architecture.md](./06_WorkflowRunner_Architecture.md) |
| **LangGraph Multi-Agent Workflows** | Domain-specific graph nodes and state machines | `core_workflows/{maintenance, rent_reminder, faq, rent_renewal}/` | [07_LangGraph_Integration.md](./07_LangGraph_Integration.md) |
| **Integration & Providers** | LLM providers, MCP tool servers, communication adapters | `mcp_server.py`, `input_channels/` | [08_Integration_And_Provider_Layer.md](./08_Integration_And_Provider_Layer.md) |
| **Scheduling & Background Jobs** | Daily batch scans for rent reminders and lease expiries | `rent_reminder/scheduler.py`, `rent_renewal/*/scheduler_entry.py` | [09_Background_Jobs_And_Scheduling.md](./09_Background_Jobs_And_Scheduling.md) |
| **Security & Error Handling** | Validation, error envelopes, and credential safety | `app/pipeline.py`, `app/checkpointer.py` | [10_Security_And_Error_Handling.md](./10_Security_And_Error_Handling.md) |
| **Observability & Logging** | Step logging, execution timing, and audit tables | `state["logs"]`, `audit_logs`, `ticket_status_log` | [11_Observability_And_Logging.md](./11_Observability_And_Logging.md) |
| **Testing Strategy** | 109+ automated unit and integration tests | `langgraph_agent/tests/` | [12_Backend_Testing_Strategy.md](./12_Backend_Testing_Strategy.md) |

---

## 6. Implementation Roadmap (Phases 1–6)

All phases represent the **Project-Wide Multi-Workflow Platform**:

* **Phase 1 — Stabilization**: `[COMPLETED]` Resolved Git merge conflicts, hardened `.env` discovery, and validated baseline regression suite.
* **Phase 2 — Database Unification**: `[COMPLETED]` Created `000_init_base_tables.sql`, unified PostgreSQL models, and built `TenantRepository`.
* **Phase 3 — Live Data Wiring**: `[COMPLETED]` Connected `payment_check_node()` to live database state, handled missing records, and wired dynamic responses.
* **Phase 4 — API Layer**: `[CURRENT]` Build unified FastAPI application exposing modular `/api/v1/` routers for Health, Tenants, Properties, Maintenance, Rent Reminders, and Lease Expiry.
* **Phase 5 — Scheduling & Alerting**: `[UPCOMING]` Establish centralized background scheduling for all 3 daily recurring scans and emergency/escalation alerting.
* **Phase 6 — Hardening**: `[UPCOMING]` Connection pool optimization, rate limiting, and production Docker containerization.