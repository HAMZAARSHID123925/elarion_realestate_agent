# 09 — Background Jobs and Scheduling Architecture

> **Document Path:** `docs/SDD/09_Background_Jobs_And_Scheduling.md`
> **Version:** 2.0 (Project-Wide Multi-Workflow Scheduling)
> **Status:** Active
> **Audience:** Developers, AI Coding Agents, Reviewers

---

## 1. Document Purpose

This document defines the Background Jobs, Recurring Scans, and Scheduled Task architecture for the **Elarion Real Estate Agent Platform**.

The platform requires both timed periodic background scans and asynchronous event-driven worker tasks to monitor leases, overdue rent, reminder windows, and maintenance escalations.

---

## 2. Recurring Scheduled Scans Map

| Scan Job Name | Implementation Location | Default Cadence | Purpose & Target Tables |
| :--- | :--- | :--- | :--- |
| **1. Daily Rent Reminder Scan** | [rent_reminder/scheduler.py](file:///c:/Users/ali/Desktop/realestate_agent/langgraph_agent/app/core_workflows/rent_reminder/scheduler.py) (`run_daily_rent_reminder_workflow`) | Daily (08:00 AM) | Scans unpaid overdue tenants; evaluates Day 30 / Day 35 reminder rules; persists reminder timestamps to `tenants`. |
| **2. Daily Lease Expiry Window Scan** | [lease_expiry/scheduler_entry.py](file:///c:/Users/ali/Desktop/realestate_agent/langgraph_agent/app/core_workflows/rent_renewal/lease_expiry/scheduler_entry.py) (`run_daily_lease_expiry_scan`) | Daily (07:00 AM) | Scans active leases approaching 90, 60, 30, and 7-day expiry windows; logs idempotent events to `lease_expiry_events`. |
| **3. Daily Renewal Reminder Stage Scan** | [renewal_reminder/scheduler_entry.py](file:///c:/Users/ali/Desktop/realestate_agent/langgraph_agent/app/core_workflows/rent_renewal/renewal_reminder/scheduler_entry.py) (`run_daily_renewal_reminder_scan`) | Daily (08:30 AM) | Scans pending lease expiry events; dispatches stage-specific renewal notifications; persists status to `renewal_reminders`. |
| **4. Maintenance Ticket Escalation Check** | Planned (Phase 5) | Hourly | Scans open maintenance tickets where `created_at < NOW() - INTERVAL '24 hours'` and `assignment_status = 'UNASSIGNED'`. |

---

## 3. Background Execution Architecture

```text
                             [ SCHEDULER ENGINE ]
                         (APScheduler / Cron / Celery)
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
 [ Rent Reminder Job ]        [ Lease Expiry Job ]       [ Renewal Reminder Job ]
 (Daily 08:00 AM)             (Daily 07:00 AM)           (Daily 08:30 AM)
        │                              │                              │
        ▼                              ▼                              ▼
 run_daily_rent_reminder_      run_daily_lease_expiry_    run_daily_renewal_reminder_
 workflow()                    scan()                     scan()
        │                              │                              │
        ▼                              ▼                              ▼
 TenantRepository              LeaseExpiryService         RenewalReminderService
        └──────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
                          Unified PostgreSQL Database
```

---

## 4. Idempotency & Concurrency Safety

1. **Unique Constraints**:
   - `lease_expiry_events` enforces `UNIQUE(lease_id, window_days)`.
   - `renewal_reminders` enforces `UNIQUE(lease_id, reminder_stage)`.
2. **Atomic Status Conditions**:
   - Rent reminder updates apply `WHERE payment_status != 'paid'`.
3. **Observability**: Every scan execution logs a structured run summary (`records_scanned`, `reminders_sent`, `escalated`, `errors`).
