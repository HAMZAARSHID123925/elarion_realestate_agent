# Lease Expiry & Rent Renewal Workflow Architecture

> **Document Path:** `docs/SDD/Lease_Expiry_Renewal_Architecture.md`
> **Status:** Active Architectural Reference
> **Domain:** Lease Expiry & 5-Stage Rent Renewal Lifecycle

---

## 1. Domain Purpose

The **Lease Expiry & Rent Renewal Domain** (`langgraph_agent/app/core_workflows/rent_renewal/`) manages the multi-month lifecycle of expiring tenant leases, staged renewal notices, intention extraction, document verification, and manager escalation across 5 sub-domains:
1. `lease_expiry` — Proactive scanning for upcoming expirations.
2. `renewal_reminder` — Staged notification dispatch (90, 60, 30, 7 days).
3. `renewal_intent` — AI-powered intent extraction from tenant replies.
4. `document_tracking` — Document upload tracking and automated verification.
5. `human_escalation` — Property manager escalation for disputes or complex negotiations.

---

## 2. 5-Stage Subsystem Architecture

```text
  ┌─────────────────┐       ┌────────────────────┐       ┌────────────────────┐
  │  Stage 1: Scan  │ ────► │  Stage 2: Remind   │ ────► │  Stage 3: Intent   │
  │ (lease_expiry)  │       │ (renewal_reminder) │       │  (renewal_intent)  │
  └────────┬────────┘       └────────┬───────────┘       └─────────┬──────────┘
           │                         │                             │
           │ (Window Crossed)        │ (Reminder Sent)             │ (Tenant Replies)
           ▼                         ▼                             ▼
  ┌─────────────────┐       ┌────────────────────┐       ┌────────────────────┐
  │  lease_expiry_  │       │ renewal_reminders  │       │  renewal_intents   │
  │     events      │       │                    │       │                    │
  └─────────────────┘       └────────────────────┘       └─────────┬──────────┘
                                                                   │
                                  ┌────────────────────────────────┴──────────────────┐
                                  ▼                                                   ▼
                       ┌─────────────────────┐                             ┌─────────────────────┐
                       │  Stage 4: Documents │                             │ Stage 5: Escalation │
                       │ (document_tracking) │                             │ (human_escalation)  │
                       └──────────┬──────────┘                             └──────────┬──────────┘
                                  ▼                                                   ▼
                       ┌─────────────────────┐                             ┌─────────────────────┐
                       │  renewal_documents  │                             │  human_escalations  │
                       └─────────────────────┘                             └─────────────────────┘
```

---

## 3. Database Persistence & Migrations

Managed in PostgreSQL via versioned migrations `001` through `005`:
* **Migration 001**: `leases`, `lease_expiry_events`, `lease_expiry_scan_runs`.
* **Migration 002**: `renewal_reminders` (tracks stage-specific dispatches with `UNIQUE(lease_id, reminder_stage)`).
* **Migration 003**: `renewal_intents`, `manager_notifications`.
* **Migration 004**: `renewal_documents` (stores verification status and document hashes).
* **Migration 005**: `human_escalations`, `escalation_audit_logs`.

---

## 4. LangGraph Workflow Graph

Compiled via `build_rent_renewal_graph()`:
* **13 Specialized Nodes**: `lease_check_node`, `decision_engine_node`, `reminder_send_node`, `intent_classification_node`, `offer_generation_node`, `document_validation_node`, `human_escalation_node`, and supporting audit/routing nodes.
* **Master Pipeline Integration**: Wired through `app/department_nodes.py:run_rent_renewal`.
