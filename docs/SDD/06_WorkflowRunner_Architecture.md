# 06 — Workflow Runner & Orchestration Architecture

> **Document Path:** `docs/SDD/06_WorkflowRunner_Architecture.md`
> **Version:** 2.0 (Project-Wide Multi-Workflow Orchestration)
> **Status:** Active
> **Audience:** Developers, AI Coding Agents, Reviewers

---

## 1. Document Purpose

This document defines the Workflow Runner and Orchestration architecture for the **Elarion Real Estate Agent Platform**.

The Workflow Runner sits between the external trigger/API layer and domain-specific LangGraph workflows. It is responsible for:
- Orchestrating multi-workflow routing based on extracted tenant intent.
- Managing persistent execution checkpoints (`AsyncPostgresSaver` / `MemorySaver`).
- Pausing execution for human approval and resuming when input is received.
- Providing batch runner interfaces for scheduled recurring scans.

---

## 2. Multi-Workflow Execution Architecture

```text
                                  External Trigger
                       (API Call / Inbound Message / Cron Scan)
                                        │
                                        ▼
                           [ MASTER PIPELINE RUNNER ]
                               (app/pipeline.py)
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │      LAYER 2 ORCHESTRATOR     │
                        │  - Intent Extraction (LLM)    │
                        │  - Urgency & Route Rules      │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │       DEPARTMENT ROUTER       │
                        │  Command(goto=<department>)   │
                        └───────┬───────┬───────┬───────┘
                                │       │       │       │
                 ┌──────────────┘       │       │       └──────────────┐
                 ▼                      ▼       ▼                      ▼
        ┌─────────────────┐    ┌─────────────┐ ┌──────────────┐ ┌──────────────┐
        │   MAINTENANCE   │    │RENT REMINDER│ │ FAQ & SEARCH │ │ RENT RENEWAL │
        │    SUBGRAPH     │    │  SUBGRAPH   │ │   SUBGRAPH   │ │   SUBGRAPH   │
        └────────┬────────┘    └──────┬──────┘ └──────┬───────┘ └──────┬───────┘
                 │                    │               │                │
                 └────────────────────┴───────┬───────┴────────────────┘
                                              │
                                              ▼
                                 [ PERSISTENT CHECKPOINTER ]
                                 PostgreSQL / MemorySaver
                                 thread_id = "<channel>:<user_id>"
```

---

## 3. Workflow Domain Execution Patterns

### 3.1 Maintenance Workflow Runner Pattern
* **Pattern**: Multi-turn slot-filling with human-in-the-loop pause.
* **Mechanism**: When non-contracted or emergency vendor approval is required, `human_approval_node` triggers `interrupt()`. State is durably preserved in PostgreSQL. When the manager approves via API or chat, `resume_pipeline()` continues execution to `ticket_creation_node`.

### 3.2 Rent Reminder Workflow Runner Pattern
* **Pattern**: Deterministic rule evaluation with live database hydration.
* **Mechanism**: 
  - **Batch Run**: `run_daily_rent_reminder_workflow()` queries all overdue candidates and invokes `rent_reminder_graph` per tenant.
  - **Single Turn**: `run_rent_reminder()` hydrates missing tenant state via `payment_check_node` and returns dynamic, context-aware responses.

### 3.3 FAQ & Property Search Runner Pattern
* **Pattern**: Single/multi-turn retrieval-augmented generation (RAG) and tool calling.
* **Mechanism**: Queries vector knowledge base for policy questions and dispatches property queries to `mcp_server.py`. Clears active department after answering.

### 3.4 Lease Expiry & Rent Renewal Runner Pattern
* **Pattern**: 5-stage lifecycle state machine with document tracking.
* **Mechanism**: Evaluates expiry windows (90/60/30/7 days), dispatches stage-specific renewal notices, classifies tenant intent (accept/negotiate/terminate), tracks upload verification, and routes to manager review.

---

## 4. Checkpointing & State Persistence

1. **Unified Checkpointer**: All subgraphs and master pipeline share the centralized checkpointer initialized in `app/checkpointer.py`.
2. **Thread ID Keying**: Sessions are keyed by `thread_id = f"{channel}:{user_id}"` ensuring multi-turn context is preserved per user.
3. **Graceful Fallback**: If PostgreSQL checkpointer is unavailable, the runner falls back to in-memory `MemorySaver` without breaking test or offline execution.