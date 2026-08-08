# 🏛️ Elarion AI Property Management Operations Layer
## Project Master Documentation & System Architecture Guide

**System Version**: 2.0  
**Architecture System**: 5-Tier AI Operations Layer (Elarion Standard)  
**Main Engine**: Python 3.13 | FastAPI | LangGraph | SQLite/PostgreSQL  

---

## 📌 Executive Summary

The **Elarion AI Property Management Agent** is an enterprise-grade AI operations platform built to automate property management workflows across multiple channels (WhatsApp Cloud API, VAPI Voice AI, Webhooks). 

The platform enforces **strict separation of concerns** across a 5-layer architecture. It handles user intent identification, emergency maintenance ticketing, vector-RAG property FAQs, lease renewal inquiries, and time-triggered automated rent overdue pings with human manager escalations.

---

## 🏛️ The 5-Layer Operations Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. INPUT CHANNELS LAYER (input_channels/)                                   │
│    Meta WhatsApp Cloud API (Port 8003) | VAPI Voice API (Port 8002)         │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. ELARION AI ORCHESTRATION LAYER (app/orchestrator/)                        │
│    Tenant Identification | Intent Classification | Urgency | Rules Engine   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. CORE AUTOMATED WORKFLOWS LAYER (app/core_workflows/)                     │
│    ├── maintenance/    (11-step ticket creation & vendor matching)       │
│    ├── faq/            (Vector RAG + Property Search tools)              │
│    ├── rent_renewal/   (Lease renewal options & tenant responses)        │
│    └── rent_reminder/  (Workflows 4 & 5: 30-Day Ping, 35-Day Followup,      │
│                         Human Manager Escalation, Manual Hold)              │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. HUMAN & SYSTEM CONNECTIONS LAYER (database/ & mcp_servers/)              │
│    Postgres DB (Neon/SQLite) | Property MCP Server | Checkpointer           │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. OUTPUTS & BUSINESS OUTCOMES LAYER                                        │
│    Automated WhatsApp/Voice Replies | Audit Trail Logs | KPI Metrics        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Comprehensive Domain Sub-Workflows

### 1. Maintenance Request Automation (`app/core_workflows/maintenance/`)
- **Purpose**: Processes tenant maintenance complaints (burst pipes, lockouts, AC failure).
- **Pipeline**: 11-step LangGraph graph assessing issue category, urgency detection (Emergency vs Normal), permission to enter, ticket payload generation, and automated vendor matching.

### 2. Tenant Support & FAQ Automation (`app/core_workflows/faq/`)
- **Purpose**: Answers tenant questions regarding lease rules, pet policies, amenities, and available rental listings.
- **Pipeline**: RAG (Retrieval-Augmented Generation) pipeline over vector embeddings + Stdio MCP client for property search queries.

### 3. Rent Renewal Workflow (`app/core_workflows/rent_renewal/`)
- **Purpose**: Handles tenant inquiries regarding upcoming lease expirations and renewal terms.

### 4. Rent Reminder & Human Escalation (`app/core_workflows/rent_reminder/`) — *Workflows 4 & 5*
- **Purpose**: Fully automated daily scanning engine for overdue rent recovery and manager escalations.
- **Key Features**:
  - **Day 30 (Reminder #1)**: Dispatches initial overdue notification via WhatsApp/Email & logs `reminder_30_sent_at`.
  - **Day 35 (Reminder #2)**: Dispatches urgent final notice 5 days later & logs `reminder_5_sent_at`.
  - **Day 36+ (Human Escalation)**: If tenant has not paid and no response was received (`response_received = False`), triggers `human_escalation_node` to notify assigned Property Manager.
  - **Manual Hold Override (`manual_hold=True`)**: Pauses automated messages for tenants under custom payment plans.
  - **Idempotency & Audit Logging**: Prevents double pings using timestamp flags and maintains append-only logs.

---

## 🗄️ Database & Schema Management

All database models reside in `database/`:
- **`database/rent_models.py`**: Python SQLite/Postgres database adapter for `tenants` table schema, state updates, and mock seed generation.
- **`database/schema.sql`**: Table definitions for `properties` and `tenants`.
- **`elarion.db`**: Local SQLite database storage.

---

## 🧪 Unified Test Suites & Organization

All test suites are centralized under `langgraph_agent/tests/`:

| Test Suite | Purpose |
| :--- | :--- |
| **`tests/test_rent_reminder.py`** | Tests Rent Reminder rules, Day 30/Day 35 pings, escalation triggers, manual holds, and DB persistence. |
| **`tests/test_orchestrator.py`** | Tests Layer 2 intent classification, urgency scoring, and department router. |
| **`tests/test_maintenance_stage1.py`** | Tests maintenance ticket creation & vendor matching. |
| **`tests/test_faq_stage1.py`** | Tests FAQ RAG vector search & property query matching. |
| **`tests/test_production_readiness.py`** | Tests full end-to-end pipeline execution. |

To run all tests:
```powershell
cd langgraph_agent
python -m pytest tests/
```
