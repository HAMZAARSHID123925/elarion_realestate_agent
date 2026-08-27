# TenantFlow.ai — Next.js AI Operations Dashboard Implementation Plan

This implementation plan outlines the architecture, database schema enhancements, backend REST API creation, Next.js frontend structure, and end-to-end integration strategy for building the **TenantFlow.ai AI Operations Layer Dashboard** based on your 5 UI screenshots.

---

## 1. Project Analysis & Current Standing

### Current State of the Codebase
1. **Backend & Orchestration**:
   - Built on **Python FastAPI** (`langgraph_agent/app/server.py`).
   - Powered by **LangGraph** multi-agent pipeline (`langgraph_agent/app/pipeline.py`) routing requests across four specialized domain subgraphs: **Maintenance**, **FAQ/Search**, **Rent Reminders**, and **Lease Renewals**.
   - Connected to **PostgreSQL / Neon** with an `AsyncPostgresSaver` checkpointer for graph state persistence (`langgraph_agent/app/checkpointer.py`).
   - Supports **WhatsApp Webhook Ingestion** (`langgraph_agent/input_channels/whatsapp_server.py`) and VAPI voice integration.

2. **Database Schema & Repositories**:
   - Contains PostgreSQL base tables (`properties`, `units`, `tenants`, `vendors`, `maintenance_tickets`, `ticket_status_log`, `audit_logs`, `assignment_attempts`, `human_escalations`, `dead_letter_jobs`, `leases`, `renewal_reminders`, `renewal_intents`, `renewal_documents`).
   - Includes data access repositories in `database/` (`tenant_repository.py`, `maintenance_repository.py`, `property_repository.py`, `dead_letter_repository.py`, `audit_repository.py`).

3. **Gaps Identified for Dashboard Integration**:
   - **No Structured Conversations/Messages Table**: Currently, WhatsApp / VAPI channels pass text into `handle_request()`. While LangGraph saves state checkpoints, there is **no queryable `conversations` or `conversation_messages` table** in PostgreSQL to power the **Conversations List** and **Transcript View** in the dashboard.
   - **Missing Dedicated Dashboard REST Aggregator Endpoints**: Current APIs (`/api/v1/metrics`, `/api/v1/maintenance`, `/api/v1/tenants`) return raw table dumps or basic counters. The dashboard requires aggregated summary views (e.g., Automation Rate %, Average Response Time, Needs Attention actionable queue, Agent Activity breakdown).
   - **No Next.js Application Setup**: The project currently only contains the Python backend and SQL migrations.

---

## 2. Target Screenshots & Page Breakdown Analysis

Based on your 5 screenshots, here is the exact data mapping required for each page:

| Page / Screenshot | Primary UI Elements & Cards | Data Sources & Required API Endpoints |
|---|---|---|
| **1. Overview** (`input_file_0.png`) | • **Top Stat Cards**: Conversations (428), AI Resolved (391), Human Escalations (37), Automation Rate (91.4%), Avg. Response Time (18s)<br>• **Needs Attention**: Urgency cards (Water Leak, Rent Overdue, Owner Report) with `Review`/`Approve` action buttons<br>• **Agent Activity Today**: Table showing workflow runs & success rates<br>• **Automation Status**: Active automation health | `GET /api/v1/dashboard/overview`<br>`POST /api/v1/human-escalations/{id}/action` |
| **2. Conversations List** (`input_file_1.png`) | • **Multi-Filter Bar**: Search, Property, Unit, Channel, Intent, Urgency, Status, Date Range<br>• **Conversations Data Table**: Date & Time, Property/Unit, Contact, Channel, Intent, Urgency, Workflow, Status, Action link<br>• **Pagination & Count**: "Showing 1 to 3 of 142 entries" | `GET /api/v1/dashboard/conversations` (with pagination, search, and filter params) |
| **3. Conversation Detail / Transcript** (`input_file_2.png`) | • **Transcript Panel**: Full chat message timeline (User text, AI response, `SYSTEM: INTENT CLASSIFIED` event tags)<br>• **Decision Context**: Classified Intent, Calculated Urgency, Escalation Status<br>• **Conversation Info**: Property, Unit, Contact, Channel, Triggered Workflow, Human Intervention status<br>• **Actions**: `Mark Reviewed`, `View Workflow` | `GET /api/v1/dashboard/conversations/{id}`<br>`POST /api/v1/dashboard/conversations/{id}/review` |
| **4. Automations Grid** (`input_file_3.png`) | • **Automation Workflow Cards**: Maintenance Request, Rent Reminder, Resident Support, Lease Renewal, Owner Reporting<br>• **Card Details**: Active badge, Handles description, Channels, Escalation Conditions bullet list, Property Scope (e.g. "All Properties (42)"), `View Details`, `Configure` buttons<br>• **New Automation Action**: Button to add automation rules | `GET /api/v1/dashboard/automations`<br>`PATCH /api/v1/dashboard/automations/{id}` |
| **5. Agent Activity & Logs** (`input_file_4.png`) | • **Execution Metrics**: Total Executions (428), AI Completed (391), Human Escalations (37), Failed (4), Automation Rate (91.4% ^2.1%) with Time Filter (Today, Yesterday, Last 7 Days)<br>• **Workflow Performance Table**: Runs, AI Resolved, Escalated, Failed, Auto Rate %, Export CSV action<br>• **Recent Executions Timeline**: Live execution log stream with status pills and timestamps | `GET /api/v1/dashboard/agent-activity` (filtered by period)<br>`GET /api/v1/dashboard/agent-activity/export` |

---

## 3. Architecture & Production Best Practices

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend App Router                      │
│     (TypeScript, Tailwind CSS / Vanilla CSS, React Query / SWR)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST API Calls
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Core API Server                        │
│                 (langgraph_agent/app/server.py :8080)                  │
│                                                                        │
│   ┌───────────────────────┐             ┌──────────────────────────┐   │
│   │ Dashboard Router      │             │ LangGraph Master Pipeline│   │
│   │ /api/v1/dashboard/... │             │ (Orchestrator + Subgraphs)│  │
│   └──────────┬────────────┘             └────────────┬─────────────┘   │
└──────────────┼───────────────────────────────────────┼─────────────────┘
               │ PostgreSQL Queries                    │ Log Turns / Escalations
               ▼                                       ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        PostgreSQL Database (Neon)                      │
│   (properties, tenants, maintenance_tickets, human_escalations,        │
│    conversations, conversation_messages, dead_letter_jobs, etc.)       │
└────────────────────────────────────────────────────────────────────────┘
```

### Key Technical Guidelines Enforced
1. **Strict Decoupling**: The Next.js frontend will communicate strictly with FastAPI backend REST endpoints via a typed API client (`lib/api-client.ts`). **No direct SQL database connections will be made from Next.js.**
2. **Real-time Live Data Binding**: All metrics, transcripts, and tables will read directly from PostgreSQL via FastAPI endpoints. When a WhatsApp message arrives, it will immediately insert into `conversations` & `conversation_messages`, allowing the dashboard to reflect real live incoming data.
3. **Structured API Responses**: Standardized JSON envelopes across all routes with TypeScript interfaces matching FastAPI Pydantic schemas.

---

## 4. Next.js Directory & Component Architecture

We will create a clean, modular Next.js application in `frontend/`:

```
frontend/
├── package.json
├── next.config.mjs
├── tsconfig.json
├── app/
│   ├── layout.tsx                     # Global Root Layout (Sidebar + Top Navbar)
│   ├── page.tsx                       # Redirect to /overview
│   ├── globals.css                    # Design Tokens, Color Variables & Aesthetics
│   ├── overview/
│   │   └── page.tsx                   # Overview Dashboard Page (Screenshot 0)
│   ├── conversations/
│   │   ├── page.tsx                   # Conversations List Page (Screenshot 1)
│   │   └── [id]/
│   │       └── page.tsx               # Conversation Transcript & Details (Screenshot 2)
│   ├── automations/
│   │   └── page.tsx                   # Automations Configuration Grid (Screenshot 3)
│   └── agent-activity/
│       └── page.tsx                   # Agent Activity & Log Timeline (Screenshot 4)
├── components/
│   ├── layout/
│   │   ├── sidebar.tsx                # Left Navigation Sidebar (TenantFlow.ai branding)
│   │   └── top-bar.tsx                # Top Search Bar, Notifications, User Profile
│   ├── overview/
│   │   ├── summary-cards.tsx          # Stat Cards (Conversations, Automation Rate, etc.)
│   │   ├── needs-attention-card.tsx   # Critical Action Items with Approve/Review buttons
│   │   └── activity-today-table.tsx   # Workflow Runs & Success Rates
│   ├── conversations/
│   │   ├── conversation-filters.tsx   # Property, Unit, Urgency, Intent filters
│   │   ├── conversation-table.tsx     # Filtered Data Table & Pagination
│   │   ├── transcript-feed.tsx        # Chat Bubbles & SYSTEM event badges
│   │   ├── decision-context-card.tsx  # Intent, Urgency, Escalation summary
│   │   └── conversation-info-card.tsx # Property, Tenant, Channel details
│   ├── automations/
│   │   └── automation-card.tsx        # Workflow Rule Card with active toggle & conditions
│   ├── agent-activity/
│   │   ├── performance-table.tsx      # Workflow Performance matrix with CSV export
│   │   └── execution-timeline.tsx     # Real-time execution log feed
│   └── ui/                            # Reusable UI primitives (Badge, Card, Button, Modal, Table)
└── lib/
    ├── api-client.ts                  # Axios/Fetch wrapper for FastAPI calls
    ├── types.ts                       # TypeScript interfaces matching backend models
    └── utils.ts                       # Date formatters, status color helpers
```

---

## 5. Phased Chunk-by-Chunk Implementation Roadmap

To avoid errors, ensure smooth execution, and allow thorough verification at every step, the project is divided into **6 clear Chunks**.

---

### Chunk 1: Database Schema Expansion & Backend Dashboard API Engine

#### 1. Database Schema Additions
Create database migration `database/migrations/007_add_conversations_and_messages.sql`:
- **`conversations` table**:
  - `conversation_id` (PK, e.g., `TF-10482` or UUID)
  - `tenant_id` (FK to `tenants`)
  - `property_id` (FK to `properties`)
  - `unit_id` (FK to `units`)
  - `channel` (`whatsapp`, `vapi`, `email`, `web`)
  - `intent` (`Maintenance Request`, `Rent Follow-up`, `Resident Support`, `Lease Renewal`)
  - `urgency` (`Critical`, `High`, `Normal`, `Low`)
  - `status` (`AI Resolved`, `Escalated`, `In Progress`, `Pending Review`)
  - `workflow_triggered` (`Maintenance Request`, `Rent Reminder`, `Resident Support`, `Lease Renewal`)
  - `human_intervention` (`None`, `Property Manager`, `Human Required`)
  - `is_reviewed` (BOOLEAN DEFAULT FALSE)
  - `last_message_at` (TIMESTAMP)
  - `created_at`, `updated_at` (TIMESTAMP)
- **`conversation_messages` table**:
  - `message_id` (PK, SERIAL/UUID)
  - `conversation_id` (FK to `conversations`)
  - `sender_type` (`tenant`, `ai`, `system`)
  - `sender_name` (TEXT)
  - `content` (TEXT)
  - `system_event` (TEXT, e.g., `INTENT CLASSIFIED & PRIORITY UPDATED`)
  - `timestamp` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

#### 2. Hooking Channel Ingestion to Record Real Messages
- Update `langgraph_agent/app/pipeline.py` and `whatsapp_server.py` so whenever an inbound message arrives or an outbound response is generated, it automatically:
  1. Creates/fetches the active `conversation` record by `(channel, user_id)`.
  2. Inserts tenant message into `conversation_messages`.
  3. Inserts AI response into `conversation_messages`.
  4. Updates conversation status, intent, and urgency based on LangGraph pipeline output.

#### 3. New FastAPI Router: `langgraph_agent/app/api/routers/dashboard.py`
Expose endpoints:
- `GET /api/v1/dashboard/overview` -> Aggregated stats, Needs Attention items from `human_escalations` & `maintenance_tickets`, Agent Activity Today metrics.
- `GET /api/v1/dashboard/conversations` -> Paginated & filtered conversations.
- `GET /api/v1/dashboard/conversations/{id}` -> Full detail including transcript messages.
- `POST /api/v1/dashboard/conversations/{id}/review` -> Mark conversation reviewed.
- `GET /api/v1/dashboard/automations` -> Automation workflows status & conditions.
- `GET /api/v1/dashboard/agent-activity` -> Performance breakdown & execution timeline.
- `POST /api/v1/human-escalations/{id}/action` -> Handle Manager `Approve` / `Review` / `Resolve` actions.

#### Chunk 1 Verification Plan:
- Run migration script: `python database/migrations/run_migration.py`.
- Seed test conversations matching the screenshots using a python script.
- Execute cURL / Pytest requests to test all `/api/v1/dashboard/*` endpoints.

---

### Chunk 2: Next.js Setup & Overview Dashboard (`input_file_0.png`)

#### 1. Next.js Application Initialization
- Initialize Next.js app with App Router, TypeScript, and Vanilla CSS/Tailwind CSS styling.
- Create core layout shell with sidebar navigation (`TenantFlow.ai` logo, Overview, Conversations, Automations, Agent Activity, Reports, Properties, Agents & Workflows, Settings).
- Configure API client in `lib/api-client.ts` pointing to `http://localhost:8080/api/v1`.

#### 2. Overview Component Implementation
- **Top Summary Cards Component**: Render 5 cards (Conversations, AI Resolved, Human Escalations, Automation Rate, Avg Response Time).
- **Needs Attention Section**: Render dynamic alert cards for urgent cases with action buttons (`Review`, `Approve`).
- **Agent Activity Today Table**: Render workflow runs and completion rates.

#### Chunk 2 Verification Plan:
- Start FastAPI server on port 8080 and Next.js dev server on port 3000.
- Verify Overview dashboard renders data directly fetched from FastAPI endpoint `/api/v1/dashboard/overview`.
- Click `Approve` or `Review` buttons and confirm status updates in backend PostgreSQL.

---

### Chunk 3: Conversations List & Real-Time Detail Transcript (`input_file_1.png` & `input_file_2.png`)

#### 1. Conversations List Page (`frontend/app/conversations/page.tsx`)
- Render multi-filter header (Search input, Property dropdown, Unit input, Channel select, Intent select, Urgency select, Status select, Date Range).
- Render responsive data table with formatted columns and pagination ("Showing 1 to 3 of 142 entries").
- Wire filter controls to refetch data from `GET /api/v1/dashboard/conversations`.

#### 2. Conversation Detail & Transcript Page (`frontend/app/conversations/[id]/page.tsx`)
- Render header with back button, conversation title (`Conversation #TF-10482`), status badge, `Mark Reviewed` button, `View Workflow` button.
- **Left Panel (Transcript)**:
  - User message bubbles (avatar + timestamp + text).
  - TenantFlow AI response bubbles (bot icon + timestamp + text).
  - System event banners (`⚡ SYSTEM: INTENT CLASSIFIED & PRIORITY UPDATED`).
- **Right Panel (Decision Context & Info)**:
  - Decision Context card (Classified Intent, Calculated Urgency badge, Escalation Status).
  - Conversation Information card (Property, Unit, Contact, Channel, Triggered Workflow, Human Intervention status).

#### Chunk 3 Verification Plan (WhatsApp Integration Test):
- Trigger a real inbound WhatsApp message (or via WhatsApp test endpoint).
- Check that the conversation automatically appears in the Next.js Conversations List.
- Open the conversation detail view and verify the incoming message, classified intent, and AI response appear in real time in the transcript!

---

### Chunk 4: Automations Grid & Workflow Management (`input_file_3.png`)

#### 1. Automations Page (`frontend/app/automations/page.tsx`)
- Render grid of workflow cards matching Screenshot 3:
  - **Maintenance Request**: Active badge, handles description, channels supported, escalation conditions list, property scope count.
  - **Rent Reminder**: Active badge, late fee calculation description, escalation rules.
  - **Resident Support**: Active badge, policy FAQ handles, frustration sentiment escalation.
  - **Lease Renewal**: Document collection & pre-renewal intent checks.
  - **Owner Reporting**: Automated portfolio reporting.
  - **+ New Automation** action card.
- Wire `View Details` and `Configure` action buttons to automation detail modal/page.

#### Chunk 4 Verification Plan:
- Verify active state toggles update workflow status in the database via `PATCH /api/v1/dashboard/automations/{id}`.

---

### Chunk 5: Agent Activity Page & Execution Analytics (`input_file_4.png`)

#### 1. Agent Activity Page (`frontend/app/agent-activity/page.tsx`)
- Render metric summary cards (Total Executions, AI Completed, Human Escalations, Failed, Automation Rate %) with Time Period Selector (Today, Yesterday, Last 7 Days).
- **Workflow Performance Table**: Display table with Agent/Workflow, Runs, AI Resolved, Escalated, Failed, Auto Rate %, and `Export CSV` action button.
- **Recent Executions Feed**: Render real-time timeline stream of recent workflow executions with status badges (e.g. `Plumbing Agent`, `AI Resolved`, `Collection Agent`, `Failed`).

#### Chunk 5 Verification Plan:
- Test period filter tabs (Today / Yesterday / Last 7 Days) and confirm table recalculates statistics from backend API.
- Test `Export CSV` button to download performance metrics.

---

### Chunk 6: Production Hardening, CORS & Integration Verification

- Verify CORS settings in `langgraph_agent/app/server.py` allow origins `http://localhost:3000`.
- Verify error handling and empty state designs across all dashboard pages.
- Execute full system walkthrough from WhatsApp message receipt -> Database persistence -> Next.js Dashboard UI update -> Manager Escalation Approval.

---

## 6. Proposed Summary of File Modifications & Additions

### Backend (`langgraph_agent` & `database`)
- **[NEW]** [`database/migrations/007_add_conversations_and_messages.sql`](file:///d:/ELARION/elarion_realestate_agent/database/migrations/007_add_conversations_and_messages.sql)
- **[NEW]** [`database/conversation_repository.py`](file:///d:/ELARION/elarion_realestate_agent/database/conversation_repository.py)
- **[NEW]** [`langgraph_agent/app/api/routers/dashboard.py`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/app/api/routers/dashboard.py)
- **[MODIFY]** [`langgraph_agent/app/server.py`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/app/server.py) (Mount dashboard router & update CORS)
- **[MODIFY]** [`langgraph_agent/app/pipeline.py`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/app/pipeline.py) (Inject conversation log hooks)
- **[MODIFY]** [`langgraph_agent/input_channels/whatsapp_server.py`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/input_channels/whatsapp_server.py) (Pass conversation metadata)

### Frontend (`frontend/`)
- **[NEW]** Next.js App Router Structure in `frontend/` directory with layout, pages, components, and TypeScript API client.

---

## 7. Verification Plan & Automated Commands

### Automated Tests & Verification Commands
1. **Database Migration Verification**:
   ```bash
   python d:/ELARION/elarion_realestate_agent/database/migrations/run_migration.py
   ```
2. **Backend Dashboard API Unit & Integration Tests**:
   ```bash
   pytest d:/ELARION/elarion_realestate_agent/langgraph_agent/tests -k dashboard
   ```
3. **FastAPI Server Launch**:
   ```bash
   python -m uvicorn app.server:app --host 0.0.0.0 --port 8080 --reload
   ```
4. **Next.js Development Server**:
   ```bash
   cd frontend && npm run dev
   ```

### Manual Verification Steps
1. Navigate to `http://localhost:3000/overview` and verify all 5 top stat cards and Needs Attention cards match `input_file_0.png`.
2. Navigate to `http://localhost:3000/conversations` and filter by status/channel to verify query filters work.
3. Click a conversation to open `/conversations/[id]` and verify full transcript, decision context, and conversation info cards match `input_file_2.png`.
4. Trigger a live message via WhatsApp or API test script, then refresh the dashboard to verify real-time data persistence.
