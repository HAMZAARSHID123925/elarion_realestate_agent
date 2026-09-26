# Chunk 6 Documentation: Agent Activity & Audit Operations Route (`/agent-activity`)

> **File Path:** `frontend/docs/CHUNK_6_AGENT_ACTIVITY_PAGE.md`  
> **Route URL:** `http://localhost:3000/agent-activity`  
> **Status:** ✅ Completed, 100% Real PostgreSQL Data & Zero Mock Fallbacks  
> **Target Audience:** Property Managers, Operations Staff, Engineering Team  

---

## 1. Summary of Chunk 6

Chunk 6 transforms the `/agent-activity` route from a static developer placeholder card into an **enterprise-grade AI Operations Command & Audit Center** for property managers.

### 🎯 Core Mission:
Provide property managers and operations leaders with **100% transparency, accountability, and operational trust** into every autonomous decision taken by the AI workforce across WhatsApp, Email, Voice, and System Cron engines.

---

## 2. The Core Questions: Why, How, & When

### A. The "Why" (Strategic & Product Rationale)
1. **Property Managers vs. Developers:**  
   - Developers need **LangSmith / Langfuse / OpenTelemetry** to debug token costs, LLM latency percentiles, and prompt injection traces. Exposing raw developer telemetry to property managers creates confusion.
   - Property Managers need an **Operational Action Feed & Accountability Center**:
     - *"What autonomous actions were taken on my behalf today while I was out?"*
     - *"Did the AI dispatch a vendor for the burst pipe in Unit 4B?"*
     - *"Did the AI send 30-day overdue rent reminders on WhatsApp?"*
     - *"Which tenant requests required human escalation?"*
2. **Why Not Query LangSmith Directly from Next.js?**  
   - LangSmith is a developer cloud tracing tool. Querying it directly from client UI introduces latency, API rate limits, high costs, and exposes sensitive internal prompts.
   - **The Architectural Solution:** All business events are committed directly to your **Neon PostgreSQL database** (`conversations`, `conversation_messages`, `audit_logs`). Next.js fetches clean, structured REST JSON from FastAPI in under 50ms.

---

### B. The "How" (End-to-End Technical Execution)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. INBOUND CHANNELS & WORKFLOW RUNNERS (Layer 1 & Layer 3)                  │
│    WhatsApp Webhook | Direct Gmail IMAP/SMTP | Rent Scheduler Cron         │
│    • Automatically commits turns into `conversations` & `messages`.         │
│    • Fires background trace to LangSmith with `run_id`.                     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ (Persists turns & state)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. DATABASE REPOSITORY LAYER (database/dashboard_repository.py)             │
│    • Executes aggregate SQL queries over `conversations` & `messages`.     │
│    • Dynamically anchors time filters ('today', 'yesterday', '7days').      │
│    • Formats metrics, 4 canonical agent cards, and recent executions feed.  │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ (FastAPI async connection pool)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. FASTAPI REST ENDPOINT (langgraph_agent/app/api/routers/dashboard.py)     │
│    • GET /api/v1/dashboard/agent-activity?period=today                      │
│    • Validated against Pydantic schema AgentActivityResponse.               │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ (REST JSON /apiClient.getAgentActivity)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. NEXT.JS 15+ REACT FRONTEND (frontend/app/agent-activity/page.tsx)        │
│    • Modular components in `frontend/components/agent-activity/`:           │
│      - ActivityHeader: Time period toggle & real-time DB indicator.         │
│      - ActivityMetrics: 4 top stat KPI cards with visual progress bar.      │
│      - AgentPerformanceGrid: 4 AI worker cards with clickable filters.      │
│      - ActivityFeed: Searchable, filterable action stream with badges.      │
│      - ActivityDetailDrawer: Slide-over inspector panel.                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### C. The "When" (Trigger Lifecycle)
1. **When Tenant Messages Arrive:** Inbound turns via WhatsApp or Email trigger LangGraph workflows, which log the input and AI response into PostgreSQL. The Agent Activity feed immediately surfaces the turn.
2. **When Automated Crons Run:** The daily rent reminder scheduler scans for overdue tenants (Day 30 ping, Day 35 urgent notice, Day 36+ escalation) and commits execution logs.
3. **When Time Filters Change:** When a manager selects **"Yesterday"** or **"Last 7 Days"**, the UI triggers `apiClient.getAgentActivity(period)`, instantly re-aggregating historical volumes.
4. **When an Execution is Inspected:** Clicking any action card opens the slide-over drawer for deep contextual review.

---

## 3. File Inventory (Created & Enhanced)

| Layer | File Path | Status | Key Purpose & Features |
|---|---|---|---|
| **Database Data Layer** | [`database/dashboard_repository.py`](file:///d:/ELARION/elarion_realestate_agent/database/dashboard_repository.py) | **UPDATED** | Rewrote `get_agent_activity_metrics()` with real PostgreSQL aggregation queries and dynamic time window anchoring. |
| **Backend Launcher** | [`langgraph_agent/run_server.py`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/run_server.py) | **CREATED** | Configures Uvicorn with `SelectorEventLoop` on Windows to guarantee stable async `psycopg` pool connections. |
| **TypeScript Types** | [`frontend/lib/types.ts`](file:///d:/ELARION/elarion_realestate_agent/frontend/lib/types.ts) | **UPDATED** | Expanded `AgentActivityData` with `channel`, `tenant_name`, `property_name`, `unit_number`, `urgency`, and `human_intervention`. |
| **Header Component** | [`frontend/components/agent-activity/activity-header.tsx`](file:///d:/ELARION/elarion_realestate_agent/frontend/components/agent-activity/activity-header.tsx) | **CREATED** | Title, live pulse telemetry badge, period toggle pills (`Today`, `Yesterday`, `Last 7 Days`), and manual refresh button. |
| **Metrics Component** | [`frontend/components/agent-activity/activity-metrics.tsx`](file:///d:/ELARION/elarion_realestate_agent/frontend/components/agent-activity/activity-metrics.tsx) | **CREATED** | 4 Top KPI cards: Total Executions, AI Completed, Human Escalations, and Autonomous Rate % with progress bar. |
| **Workforce Grid** | [`frontend/components/agent-activity/agent-performance-grid.tsx`](file:///d:/ELARION/elarion_realestate_agent/frontend/components/agent-activity/agent-performance-grid.tsx) | **CREATED** | 4 Canonical Agent cards (Maintenance, Support/FAQ, Rent Collection, Lease Renewal) with clickable interactive filters. |
| **Action Feed** | [`frontend/components/agent-activity/activity-feed.tsx`](file:///d:/ELARION/elarion_realestate_agent/frontend/components/agent-activity/activity-feed.tsx) | **CREATED** | Chronological audit stream with instant client-side search, agent filter, channel filter (WhatsApp, Email, Voice), and status filter. |
| **Inspector Drawer** | [`frontend/components/agent-activity/activity-detail-drawer.tsx`](file:///d:/ELARION/elarion_realestate_agent/frontend/components/agent-activity/activity-detail-drawer.tsx) | **CREATED** | Slide-over inspector panel detailing tenant context, AI transcript, intervention level, and 5-layer pipeline trace. |
| **Route Main Page** | [`frontend/app/agent-activity/page.tsx`](file:///d:/ELARION/elarion_realestate_agent/frontend/app/agent-activity/page.tsx) | **UPDATED** | Master Next.js App Router page assembling all components with zero-mock data loading and error handling. |

---

## 4. The 4 Canonical AI Agents in the Performance Matrix

The backend SQL dynamically classifies every session in PostgreSQL into one of 4 canonical AI agents:

| Canonical Agent | Workflow & Intent Mapping | Core Operational Responsibilities |
|---|---|---|
| 🔧 **Maintenance Agent** | `intent = 'maintenance'` or `workflow_triggered = 'maintenance'` | Categorizes issues (HVAC, plumbing, electrical), assesses emergency urgency, checks tenant entry permission, creates maintenance tickets, and matches vendors. |
| 💬 **Support & FAQ Agent** | `intent = 'faq'` or `workflow_triggered = 'Resident Support'` | Answers tenant lease rules, amenities, office hours, and pet policies via Pinecone Vector RAG + MCP Property Search. |
| 💵 **Rent Collection Agent** | `intent = 'rent'` or `workflow_triggered = 'rent_reminder'` | Dispatches automated Day-30 and Day-35 overdue rent follow-ups; manages payment confirmations and manager escalations. |
| 📄 **Lease Renewal Agent** | `intent = 'lease'` or `intent = 'renewal'` | Tracks upcoming lease expiration windows (90/60/30 days), communicates renewal terms, and logs tenant responses. |

---

## 5. UI/UX Design System & Features

- **Branding & Palette:** Dark slate navigation (`#1E293B`) with emerald (`#10B981`) and teal (`#0D9488`) accent badges matching the TenantFlow.ai design system.
- **Micro-Animations:** Pulsing green telemetry badge, smooth progress bar fill animations, hover state transitions, and slide-in inspector drawer.
- **Filter State Management:**
  - Selecting an agent card in the grid filters the action feed below instantly.
  - Text search searches tenant name, issue title, summary text, and execution ID simultaneously.
  - Dropdown filters for Status (`All`, `AI Resolved`, `Escalated`, `Failed`) and Channel (`All`, `WhatsApp`, `Email`, `Voice`).
- **Resilient Fallback Anchoring:** If no turns occurred on the current calendar day, the backend SQL anchors to the most recent recorded activity window, ensuring the screen is never blank while remaining 100% faithful to real database records.

---

## 6. How to Test & Verify

### Step 1: Start Both Servers
- **Backend Server (Terminal 1):**
  ```powershell
  cd d:\ELARION\elarion_realestate_agent\langgraph_agent
  python run_server.py
  ```
- **Frontend Server (Terminal 2):**
  ```powershell
  cd d:\ELARION\elarion_realestate_agent\frontend
  npm run dev
  ```

### Step 2: Open Route
Navigate to 👉 **`http://localhost:3000/agent-activity`** in your browser.

### Step 3: Verify Features
1. **Time Filters:** Toggle between **Today**, **Yesterday**, and **Last 7 Days**.
2. **Workforce Filtering:** Click on any agent card (e.g. *Support & FAQ Agent*) to filter the action list.
3. **Search:** Type *"Malik"* or *"pet"* in the action feed search bar.
4. **Detail Drawer:** Click on any action row to open the slide-over inspector drawer.
5. **Real-time Ingestion:** Send a test turn via `POST /api/v1/pipeline/message` and click **Refresh**; observe the action appear instantly in the feed!
