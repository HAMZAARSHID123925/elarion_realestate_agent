# Phase 5 — Project-Wide Scheduling & Alerting

> **Document Path:** `docs/SDD/phases/Phase_5_Scheduling_And_Alerting.md`
> **Status:** Planned Phase
> **Scope:** Project-Wide (Maintenance, Rent Reminder, Lease Expiry, Renewal)

---

## 1. Purpose

The purpose of Phase 5 is to establish background job automation, periodic cron execution, and event-driven alerting across all four workflow domains on the Elarion Platform.

---

## 2. Phase Objectives

1. Centralize background scheduler execution for all recurring daily batch scans:
   - **Daily Rent Reminder Scan** (08:00 AM) -> `run_daily_rent_reminder_workflow()`
   - **Daily Lease Expiry Window Scan** (07:00 AM) -> `run_daily_lease_expiry_scan()`
   - **Daily Renewal Reminder Stage Scan** (08:30 AM) -> `run_daily_renewal_reminder_scan()`
2. Implement **Maintenance Emergency & Stale Ticket Alerting**:
   - Escalate unassigned emergency maintenance tickets exceeding 1 hour.
   - Alert managers for unassigned standard tickets exceeding 24 hours.
3. Implement **Rent Escalation Notifications**:
   - Package full escalation dossiers when tenants reach Day 35+ non-responsive status.
4. Provide structured execution telemetry, run logs, and dead-letter retry safety.

---

## 3. Phase 5 Exit Criteria

* [ ] Background job scheduler runs on defined cadences without manual intervention.
* [ ] All 3 daily recurring scans execute idempotently and record scan summaries to PostgreSQL.
* [ ] Alert handlers dispatch notifications for chronic rent arrears and maintenance emergencies.
* [ ] Stale maintenance ticket monitor alerts staff on overdue assignments.
* [ ] Concurrency locks prevent overlapping executions of identical batch jobs.
* [ ] Full regression suite continues to pass.
