# Workflow #4 — Lease / Renewal Workflow
# Phase 1 — Lease Expiry Tracking
## Implementation Specification (SDD)

> **Status:** Draft specification for implementation. No code has been written or modified as part of producing this document.
>
> **Basis of inspection:** This specification was produced from the repository **directory/file structure** supplied by the project owner (folder tree of `realestate_agent/`), not from a live inspection of file contents (`schema.sql`, `rent_models.py`, `docs/architecture.md`, `docs/api_contracts.md`, `rent_reminder/scheduler.py`, etc. were **not** opened/read). Wherever a design decision depends on the *actual contents* of an existing file, this document says so explicitly and flags it as **`VERIFY AGAINST SOURCE`**. The implementing coding agent MUST open and confirm these files before writing code, and must adjust this spec's assumptions if the real content differs.

---

## 1. Phase Overview

Phase 1 of Workflow #4 (Lease/Renewal Workflow) implements **Lease Expiry Tracking**: a scheduled, deterministic backend process that scans active leases in PostgreSQL, determines which leases have crossed a configured "renewal window" boundary (e.g. 90/60/30/7 days before expiry), and emits a structured, idempotent internal event per (lease, window) pair. This event is the sole hand-off artifact to Phase 2 (Renewal Reminder & Follow-up).

Phase 1 does **not**:
- talk to tenants,
- decide renewal outcomes,
- involve the LLM in date math,
- send notifications on any channel.

It is a pure **detection and event-recording** service.

---

## 2. Business Objective

Ensure no active lease reaches expiry without the business being alerted with enough lead time to run a renewal process, by deterministically and repeatably identifying leases entering configured renewal windows and recording that fact in a form other workflow phases can safely consume — without duplicate alerts and without relying on non-deterministic (LLM) reasoning for date arithmetic.

---

## 3. Scope

- Scheduled/periodic scan of active leases.
- Deterministic calculation of days-remaining-to-expiry per lease.
- Classification of each lease against configured expiry windows (90/60/30/7 days, configurable).
- Creation of exactly one expiry event per (lease, window) combination, idempotently.
- Persistence of expiry events in PostgreSQL.
- Emitting/making available a trigger signal that Phase 2 can consume (queue row / event table row — see §16).
- Logging, observability, and error handling for the scan/detection process itself.
- Lease status handling (active vs. non-active leases).
- Timezone-safe date handling for expiry math.

## 4. Out of Scope

- Any tenant-facing communication (SMS/WhatsApp/Email/Voice) — belongs to Phase 2.
- Manager notification — belongs to Phase 3.
- Document collection/tracking — belongs to Phase 4.
- Human escalation — belongs to Phase 5.
- Lease creation, lease editing, or lease termination workflows.
- Rent collection / `rent_reminder` logic (separate workflow; only reused as an *architectural pattern*, not functionally coupled).
- Any new UI.
- LLM-based reasoning of any kind inside this phase.

---

## 5. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-1 | The system SHALL periodically query all leases with an "active" status. |
| FR-2 | The system SHALL compute `days_remaining = expiry_date - current_business_date` deterministically, in application/service code (not LLM, not raw SQL date-diff unless verified equivalent — see §23). |
| FR-3 | The system SHALL compare `days_remaining` against a configurable, ordered list of expiry windows. |
| FR-4 | The system SHALL create exactly one expiry event per (lease_id, window_value) the first time that window is reached or passed. |
| FR-5 | The system SHALL NOT create a duplicate event for a (lease_id, window_value) pair that already has a recorded event, even across repeated scheduler runs. |
| FR-6 | The system SHALL skip leases that are not active (terminated, draft, cancelled, already-renewed, etc.), per §18. |
| FR-7 | The system SHALL record leases with missing or invalid expiry dates as a data-quality error, not silently skip or crash the whole scan. |
| FR-8 | The system SHALL persist every generated event with enough information for Phase 2 to act without re-querying lease internals from scratch (denormalized event payload, §16). |
| FR-9 | The system SHALL expose a way for Phase 2 (or a dispatcher) to discover new/unconsumed events (status field, see §16, §25). |
| FR-10 | The system SHALL be safely re-runnable (idempotent) at any interval without operator intervention. |

---

## 6. Non-Functional Requirements

- **Determinism:** identical DB state + identical "current date" input ⇒ identical output events, every run. No LLM involvement.
- **Idempotency:** re-running the scan must never create duplicate events (see §17).
- **Reliability:** a single lease with bad data must not abort the scan for all other leases (partial-failure isolation).
- **Auditability:** every event and every skip/error must be traceable (which lease, which window, when, why).
- **Extensibility:** new expiry windows must be addable via configuration, not code changes.
- **Performance:** the scan must operate on active leases only via an indexed query; it must not full-table-scan an unbounded leases table without a WHERE-status filter.
- **Isolation from conversational graph:** this phase must not require an active LangGraph conversational thread/session to run (see §26).

---

## 7. Existing Components That Should Be Reused

Based on the supplied structure, the following existing pieces should be reused rather than recreated:

| Existing Component | Path | Reuse Purpose |
|---|---|---|
| Postgres checkpointer | `langgraph_agent/app/checkpointer.py` | Reuse the existing Postgres connection/session pattern for any LangGraph-side state if Phase 1 needs to hand off into a graph node (see §26). Do **not** create a second, parallel Postgres connection mechanism if this file already exposes a reusable session/engine — `VERIFY AGAINST SOURCE`. |
| Lease/rent DB models | `database/rent_models.py` | This is the presumptive home of any existing `Lease` (or similarly named) model. Must be opened and confirmed before designing new columns/tables — `VERIFY AGAINST SOURCE`. |
| DB schema | `database/schema.sql`, `database/seed.sql` | Source of truth for existing table definitions and current seed/test data shape. Any new table/column must be expressed as an additive migration against this file, not a rewrite — `VERIFY AGAINST SOURCE`. |
| Scheduler pattern | `langgraph_agent/app/core_workflows/rent_reminder/scheduler.py` | This is the only existing scheduler-shaped module in the repo. Per the supplied tree it currently supports **manual run only (no cron)**. Its interface/shape (however it currently triggers a scan) should be mirrored for consistency, but its lack of cron means actual periodic execution is a **NEW COMPONENT** for both this workflow and, implicitly, a gap in `rent_reminder` too (out of scope to fix here, but noted). |
| Workflow skeleton | `langgraph_agent/app/core_workflows/rent_renewal/{graph.py, nodes.py, state.py}` | This is the existing (stub) home of Workflow #4. Phase 1's LangGraph-facing surface (if any — see §26) belongs here, not in a new top-level workflow folder. |
| Workflow routing | `langgraph_agent/app/department_nodes.py` | Existing router that dispatches to each workflow. If/when Phase 2+ needs to enter the conversational graph, routing should go through this existing router rather than a bespoke dispatch mechanism. |
| MCP service pattern | `mcp_servers/property_search/{server.py, database.py, ...}` | Reference pattern for how this repo structures a standalone service with its own DB access module, if Phase 1's scheduler is implemented as an out-of-graph service process rather than an in-graph node (recommended — see §26). |
| Logging | `langgraph_agent/app/utils/loggers.py` | Reuse existing logger configuration instead of introducing a second logging setup — `VERIFY AGAINST SOURCE` for logger names/format. |
| Helpers | `langgraph_agent/app/utils/helper.py` | Check for existing date/time or DB helper utilities before writing new ones — `VERIFY AGAINST SOURCE`. |
| Orchestrator state/schemas | `langgraph_agent/app/orchestrator/{state.py, schemas.py}` | Reuse existing state/schema conventions (naming, typing style) if any typed models are needed for the event payload, for consistency with the rest of the codebase. |
| Test conventions | `langgraph_agent/tests/test_rent_reminder.py` and root `tests/` folder | Reuse existing test scaffolding/conventions (fixtures, DB test setup) rather than inventing a new test harness. Note: the repo currently has **three scattered test locations** (root `tests/`, `langgraph_agent/test_*.py` loose files, `langgraph_agent/tests/`) — this is a pre-existing inconsistency, not something Phase 1 should silently "fix" by adding a fourth location. Phase 1 tests should be placed per §29/§30 recommendation and this should be flagged to the team separately. |

---

## 8. Components That Must Be Added — **NEW COMPONENT**

| Component | Why it's new |
|---|---|
| **Lease Expiry Rule Engine** (pure function/module: lease + windows + today → classification) | Nothing in the supplied tree performs deterministic expiry classification. |
| **Lease Repository / Data Access module** for `rent_renewal` (query active leases, read expiry fields) | `rent_renewal/` currently has only `graph.py`, `nodes.py`, `state.py` — no data-access layer exists there. |
| **Expiry Event table + model** (Postgres) | No such table is referenced anywhere in the supplied structure. |
| **Expiry Window Configuration mechanism** (e.g. config table or config file: `[90, 60, 30, 7]`, editable without code change) | Nothing currently externalizes business-rule thresholds. |
| **Cron/periodic trigger** for the scan (actual scheduling mechanism, not just a manually-invoked function) | `rent_reminder/scheduler.py` is explicitly "no cron — manual run only" per the supplied tree; Phase 1 needs true periodic execution. |
| **Idempotency constraint** (DB unique constraint / conflict-safe upsert logic) | No existing uniqueness guarantee for lease-window events exists. |
| **Data-quality/error log for leases with missing/invalid expiry data** | Not present in supplied structure. |
| **Phase-1 → Phase-2 hand-off contract/consumer marker** (`status` field / outbox pattern) | No event/outbox mechanism currently exists in the tree. |
| **Migration script(s)** for the above additive schema changes | To be added under wherever the project's migration convention lives — `VERIFY AGAINST SOURCE` (no migrations directory is visible in the supplied tree; if none exists, this itself is a **NEW COMPONENT**: a migrations folder, e.g. `database/migrations/`). |

---

## 9. Architecture

Phase 1 is designed as a **backend batch/service component**, deliberately kept outside the LangGraph conversational graph, because it performs no reasoning and needs to run on a schedule independent of any conversation/session.

```
                    ┌───────────────────────────────┐
                    │   Scheduler (NEW: cron/worker) │
                    └───────────────┬────────────────┘
                                    │ triggers
                                    ▼
                    ┌───────────────────────────────┐
                    │  Lease Expiry Tracking Service │
                    │  (NEW, lives under              │
                    │   rent_renewal/lease_expiry/)   │
                    └───────────────┬────────────────┘
                                    │ uses
                 ┌──────────────────┼──────────────────┐
                 ▼                                     ▼
     ┌───────────────────────┐             ┌───────────────────────┐
     │ Lease Repository (NEW) │             │ Expiry Rule Engine(NEW)│
     │ reads active leases    │             │ pure deterministic     │
     │ via database/rent_models│───lease────▶ date/window logic      │
     │ + schema.sql (existing) │             └───────────┬───────────┘
     └───────────────────────┘                            │ classification
                                                            ▼
                                             ┌───────────────────────┐
                                             │  Event Writer (NEW)    │
                                             │  idempotent insert     │
                                             │  into lease_expiry_    │
                                             │  events table (NEW)    │
                                             └───────────┬───────────┘
                                                          │ event rows,
                                                          │ status=PENDING
                                                          ▼
                                             ┌───────────────────────┐
                                             │ Phase 2 (Renewal       │
                                             │ Reminder) — consumer,  │
                                             │ out of scope here      │
                                             └───────────────────────┘
```

Postgres (existing, reused) underlies both the Lease Repository read path and the new Expiry Event write path — a single database, no new datastore introduced.

---

## 10. End-to-End Flow

1. Scheduler fires (interval configurable, e.g. daily at a fixed operational time — see §15).
2. Lease Expiry Tracking Service starts a scan run (assigns a `run_id` for observability/correlation).
3. Lease Repository queries all leases where `status = 'active'` (and any other existing "is active" predicate — `VERIFY AGAINST SOURCE` in `rent_models.py`/`schema.sql`).
4. For each lease:
   a. Validate presence/validity of `expiry_date` (or equivalently named existing field). If missing/invalid → log data-quality error, record lease in a skipped/error list, continue to next lease (do not abort run).
   b. Compute `days_remaining` deterministically (§13, §23).
   c. Run Expiry Rule Engine: classify against configured windows (§14).
   d. For each window crossed that does **not** already have an event for this lease → attempt idempotent insert of an expiry event (§17).
   e. If insert is a no-op due to existing event (conflict) → log as "already recorded", not an error.
5. After all leases processed, the service writes a run summary (counts: scanned, classified, events created, duplicates skipped, errors) to logs/observability (§21).
6. Newly created events sit in the `lease_expiry_events` table with `status = 'PENDING'`, available for Phase 2 to poll/consume (§16, §26).
7. Run ends. No tenant/manager communication occurs.

---

## 11. Database Interaction

- **Read path:** Lease Repository issues a read-only query against the existing lease table (name/location to be confirmed in `database/rent_models.py` — `VERIFY AGAINST SOURCE`), filtered by active status and selecting only the fields needed (§12).
- **Write path:** Event Writer performs an idempotent insert (`INSERT ... ON CONFLICT DO NOTHING`, or equivalent ORM-level upsert) into the new `lease_expiry_events` table.
- No updates or deletes are performed against the lease table itself by Phase 1 — this phase is read-only with respect to lease data.
- All writes happen within a single transaction per lease (not per whole run), so one lease's failure cannot roll back another lease's successfully recorded event.

---

## 12. Lease Data Requirements

Phase 1 needs, at minimum, from the existing lease record:

| Field | Purpose | Status |
|---|---|---|
| `lease_id` (PK) | event identity | Presumed existing |
| `tenant_id` | event payload | Presumed existing |
| `property_id` | event payload | Presumed existing |
| `expiry_date` (or `lease_end_date`/similar) | expiry math | Presumed existing — **exact field name must be confirmed** `VERIFY AGAINST SOURCE` |
| `status` (active/terminated/etc.) | §18 filtering | Presumed existing — **exact enum values must be confirmed** `VERIFY AGAINST SOURCE` |

If any of these do not exist in `rent_models.py`/`schema.sql`, they are **NEW COMPONENT** (additive columns) and must be added via migration, not invented as assumptions in code. The implementing agent must halt and confirm actual field names before coding — do not guess field names.

---

## 13. Expiry Calculation Logic

- `days_remaining = expiry_date - current_business_date`, where both are **calendar dates** (not datetimes) to avoid time-of-day drift (§23).
- Calculation occurs entirely in the Expiry Rule Engine (application code), never in the LLM, and never implicitly inside a prompt.
- SQL may be used only for the *filtering* of candidate leases (e.g. "expiry_date within the next N days") as a performance optimization, but the **authoritative** window classification decision is made in deterministic application code, not inferred from the SQL filter alone — this avoids off-by-one/timezone bugs living in two places.

---

## 14. Configurable Expiry Windows

- Windows (default: `[90, 60, 30, 7]` days) MUST be stored as data, not hardcoded constants, so they can change without a code deploy.
- Recommended representation: a small configuration table, e.g. `lease_renewal_windows(id, days_before_expiry, is_active, description)`, seeded with the four defaults. Alternative (lighter-weight) acceptable representation: an environment-driven/config-file list (consistent with how the project already handles config, per `.env`/`.env.example` — `VERIFY AGAINST SOURCE` for existing config conventions before choosing table vs. env).
- The Rule Engine reads this configuration at run start (not per-lease) and treats it as an ordered, deduplicated set of integers.
- Adding/removing a window value must require only a data/config change, never a code change to the Rule Engine.
- Windows are explicitly documented as **configurable business rules**, not legal requirements.

---

## 15. Scheduler Requirements

- **NEW COMPONENT.** The existing `rent_reminder/scheduler.py` is manual-run only (no cron) per the supplied structure, so true periodic execution does not yet exist anywhere in this repo and must be added for Phase 1.
- Requirements:
  - Must run at least once per operational day (exact cadence configurable).
  - Must be safe to also trigger manually/on-demand (for ops/debugging), reusing the same underlying service entry point as the cron path — one code path, two triggers.
  - Must not require an open LangGraph conversation/session/thread to execute.
  - Must record `run_id`, `started_at`, `finished_at`, `outcome_summary` for every run (§21).
  - Concurrency: if a run is still in progress when the next trigger fires, the new trigger must either be skipped/queued (not run concurrently against the same lease set) — exact mechanism (advisory lock / run-status guard row) is an implementation decision left to the coding agent, but the *requirement* of "no concurrent overlapping scans" is mandatory.
- Suggested implementation shape: mirror the standalone-service pattern seen in `mcp_servers/property_search/` (own entry point, own DB access) rather than embedding scheduling logic inside the LangGraph process — keeps this phase decoupled from conversational infra per §26.

---

## 16. Event Generation — Event Contract

Table: `lease_expiry_events` (**NEW COMPONENT**)

| Field | Type | Notes |
|---|---|---|
| `id` | UUID / bigserial PK | internal identity |
| `event_name` | text | e.g. `LEASE_EXPIRY_90_DAYS`, `LEASE_EXPIRY_60_DAYS`, `LEASE_EXPIRY_30_DAYS`, `LEASE_EXPIRY_7_DAYS` — derived from window value, not free text |
| `lease_id` | FK → leases | required |
| `tenant_id` | FK → tenants | denormalized copy for Phase 2 convenience |
| `property_id` | FK → properties | denormalized copy for Phase 2 convenience |
| `expiry_date` | date | lease's expiry date at time of event creation |
| `days_remaining` | integer | value computed at classification time |
| `window_days` | integer | the configured window value that was crossed (e.g. `90`) — this is the true uniqueness key, see §17 |
| `event_date` | date | the business date the scan ran on / event was created |
| `event_status` | enum/text | `PENDING` → (consumed by Phase 2) → `CONSUMED` / `FAILED` (Phase 2 owns the transition beyond `PENDING`) |
| `run_id` | UUID | correlates event to the scheduler run that created it (§21) |
| `correlation_id` | UUID | optional external correlation id if the wider platform uses one — `VERIFY AGAINST SOURCE` for an existing correlation-id convention (e.g. in `orchestrator/schemas.py`) before inventing a new one |
| `metadata` | jsonb | free-form extension point (e.g. raw source values, calculation notes) |
| `created_at` | timestamptz | audit |

**Phase 2 consumption model:** Phase 2 (Renewal Reminder) is expected to poll (or be triggered off) rows where `event_status = 'PENDING'`, process them, then update `event_status` accordingly. Phase 1 does not call into Phase 2 directly — this preserves phase isolation and lets Phase 2 be built/deployed independently of Phase 1's cadence.

---

## 17. Duplicate Event Prevention / Idempotency

- **Event identity** = `(lease_id, window_days)`. Not `(lease_id, event_date)` — because the scan can run daily and a lease can remain within the same window for multiple consecutive days; only the *first* crossing should produce an event.
- **Uniqueness strategy:** a database-level unique constraint on `(lease_id, window_days)` in `lease_expiry_events`.
- **Safe retry behavior:** Event Writer performs `INSERT ... ON CONFLICT (lease_id, window_days) DO NOTHING` (or ORM equivalent). A conflict is logged as "already recorded" (info level), not treated as an error.
- **Scheduler re-run safety:** because the constraint is enforced at the database level (not just in application logic), even a concurrent double-trigger of the scheduler (§15) cannot produce duplicate events — the DB is the final arbiter, application-level checks are a performance optimization only, not the sole safety net.
- If a lease's expiry date changes (e.g. lease amended) after a window's event was already recorded, that is explicitly **out of scope** for Phase 1 (no automatic event invalidation) — flagged here as a known limitation/future-phase consideration, not silently handled.

---

## 18. Lease Status Handling

- Only leases in an "active" status are scanned. Exact status field/enum values must be confirmed against `rent_models.py`/`schema.sql` — `VERIFY AGAINST SOURCE`.
- Leases that are already expired (past `expiry_date` with no window bucket, e.g. beyond the smallest configured window and past zero days remaining) should still be classified consistently: if `days_remaining <= 0`, this is a distinct condition (see §33 edge cases) and should NOT silently map onto the `7`-day window — it should either be its own explicit event type (`LEASE_EXPIRED`) or explicitly excluded, per business decision. **Recommendation:** treat as a separate `LEASE_EXPIRED` event type for future-phase (escalation) use, but do not implement Phase 2 behavior for it here — only ensure Phase 1 records it correctly and does not crash or misclassify.
- Inactive/terminated/cancelled leases are excluded entirely from the scan (not merely skipped-with-log — they are filtered out at the query level for performance).

---

## 19. Error Handling

- **Per-lease isolation:** an exception while processing one lease (bad data, unexpected null, etc.) is caught, logged with lease id + reason, added to the run's error list, and processing continues to the next lease.
- **Database connectivity failure:** if the DB is unreachable at scan start, the run fails fast, logs a `run_status = FAILED` summary, and does not partially write. The next scheduled trigger will retry naturally (no special backoff logic required for Phase 1 beyond standard connection retry already used elsewhere in the codebase — `VERIFY AGAINST SOURCE` for any existing retry/backoff utility before adding a new one).
- **Event write failure for a single lease/window:** logged, added to error list, does not abort the rest of the run.
- No error in Phase 1 should ever be silently swallowed — every skip/error has a corresponding log entry (§20) and is counted in the run summary (§21).

---

## 20. Logging

- Reuse existing logging setup from `langgraph_agent/app/utils/loggers.py` — `VERIFY AGAINST SOURCE` for logger naming convention, then follow it (e.g. module-scoped logger named after this service).
- Minimum log events per run:
  - run start (`run_id`, scheduled vs. manual trigger, window config snapshot)
  - per-lease classification result (debug level)
  - per-event creation (info level, includes event id, lease id, window)
  - per-duplicate-skip (info level)
  - per-error (error level, includes lease id + exception detail)
  - run end summary (info level: counts of scanned/created/skipped/errored, duration)

---

## 21. Observability

- Every run persists a summary record (either in a dedicated `lease_expiry_scan_runs` table — **NEW COMPONENT**, or reusing an existing run/audit table if one exists — `VERIFY AGAINST SOURCE`) containing: `run_id`, `started_at`, `finished_at`, `leases_scanned`, `events_created`, `duplicates_skipped`, `errors_count`, `status`.
- This run-summary table (or log-derived equivalent) is what ops/monitoring should alert on (e.g. `errors_count > threshold`, or "no run has completed successfully in >36h").
- Metrics worth exposing (mechanism — logs vs. metrics system — depends on what observability stack the project already uses; none is visible in the supplied structure, so exact wiring is left to the implementing agent, flagged **NEW COMPONENT** if no metrics pipeline exists): scan duration, events created per run, error rate per run.

---

## 22. Security Considerations

- Lease Expiry Tracking Service performs **read-only** access to lease/tenant/property data and **insert-only** access to its own new event table — no update/delete privileges required on core lease tables. DB role/grants should reflect this least-privilege principle when the migration is applied.
- No PII beyond IDs is required in the event payload for Phase 1 (tenant name/contact details are deliberately excluded — Phase 2 can join back to tenant data using `tenant_id` when it actually needs to communicate). This limits blast radius if the event table is ever exposed more broadly.
- Scheduler trigger endpoint (if the manual-trigger path is exposed over HTTP rather than purely CLI/cron) must be protected by the same auth mechanism already used for other internal endpoints — `VERIFY AGAINST SOURCE` in `docs/api_contracts.md` before designing a new auth path.

---

## 23. Timezone / Date Handling

- **Principle:** lease expiry is a *calendar-date* concept, not a *point-in-time* concept. `expiry_date` should be stored/treated as a `DATE` (no time-of-day, no timezone) if it is not already — `VERIFY AGAINST SOURCE` against `schema.sql` for its actual current type.
- The "current business date" used for comparison must be computed from a single, explicit, configured timezone (recommended: the property's/organization's operating timezone, or UTC if the project has no per-property timezone concept yet — `VERIFY AGAINST SOURCE` for any existing timezone convention in `rent_models.py`/`checkpointer.py` before deciding). Do not use the application server's local OS timezone implicitly.
- If `expiry_date` is currently stored as a `timestamptz`/`datetime` rather than a plain `date`, this is flagged as a data-modeling risk: comparisons must explicitly truncate to date-in-the-correct-timezone before diffing, to avoid off-by-one-day errors near midnight boundaries or DST transitions. This truncation logic lives once, inside the Expiry Rule Engine — never duplicated ad hoc elsewhere.
- Daylight Saving Time must not affect `days_remaining` calculations because the calculation is date-arithmetic (whole calendar days), not elapsed-duration arithmetic — this is a design constraint the Rule Engine must satisfy (i.e. implement via calendar-date subtraction, not `timedelta` over datetimes with wall-clock hours).

---

## 24. Failure Recovery

- Because the scan is idempotent (§17) and stateless between runs (all state lives in the DB, not in-memory), recovery from any failure is simply: **re-run the scan**. No compensating transactions or manual cleanup are required after a partial/failed run.
- A failed run's partially-written events (those that succeeded before the failure point) remain valid and correctly deduplicated on the next run — no rollback of successfully-written events is needed or desired.

---

## 25. State Changes

Phase 1 introduces exactly these persistent state transitions:
- Lease table: **no state change** (read-only).
- `lease_expiry_events`: rows created with `event_status = PENDING`. No other status transition is owned by Phase 1 (Phase 2 owns `PENDING → CONSUMED/FAILED`).
- `lease_expiry_scan_runs` (or equivalent): rows created/updated to reflect run lifecycle (`RUNNING → COMPLETED/FAILED`).

No LangGraph conversational state (`checkpointer.py`-backed thread state) is created or modified by Phase 1 itself, unless the implementing team chooses the in-graph trigger option in §26, in which case that specific hand-off node's state changes are scoped narrowly to "an expiry event exists, hand off to Phase 2 entry node" — no broader conversational state should be touched.

---

## 26. LangGraph Integration Boundary

- **Recommended design:** Phase 1 runs **entirely outside** the LangGraph conversational graph, as a standalone scheduled service/worker (consistent with §9, §15). This is intentional and matches the explicit architectural rule that the LLM must not be responsible for deterministic date calculations — keeping this phase graph-free removes any temptation to route date logic through a node that has LLM access.
- The **only** boundary/interface Phase 1 exposes to the graph world is the `lease_expiry_events` table itself (`status = PENDING`). Phase 2, when built, is responsible for either polling this table on its own schedule or being triggered by a lightweight dispatcher — that dispatcher, if it needs to enter the LangGraph graph (e.g. to eventually compose a reminder message), would do so via the existing `department_nodes.py` routing pattern, mirroring how other workflows are entered.
- Phase 1 itself should **not** define any LangGraph node, since it has no conversational or reasoning responsibility. If the team prefers a single "entry point" LangGraph node purely as a uniform triggering convention (for operational consistency with other workflows), that node's *only* job would be to invoke the Phase 1 service function and return — it must not perform date logic itself. This is presented as an option, not a requirement.

---

## 27. Service Boundaries

- **Lease Expiry Tracking Service** — owns: scheduling trigger handling, orchestrating repository + rule engine + event writer, run-level logging/observability. Does not own: lease CRUD, tenant communication, renewal decisioning.
- **Lease Repository** — owns: all SQL/ORM access to lease (and minimal tenant/property) data needed for classification. Does not own: business rules about what counts as "active" beyond translating the existing status field (business meaning of statuses is defined by the existing lease domain model, not redefined here).
- **Expiry Rule Engine** — owns: pure, deterministic classification logic (date math + window comparison). Has no DB access, no side effects — fully unit-testable in isolation.
- **Event Writer** — owns: idempotent persistence of classification results into `lease_expiry_events`. Does not own: any decision logic about *whether* to write, only *how* to write safely.

---

## 28. Repository/Data Access Layer

- **NEW COMPONENT:** `rent_renewal/lease_expiry/repository.py` (see §29) — provides functions such as "get all active leases with expiry data" and "check/insert expiry event," built on top of whatever DB access pattern `database/rent_models.py` already establishes (SQLAlchemy models / raw SQL / other — `VERIFY AGAINST SOURCE` and match the existing pattern rather than introducing a second ORM or query style).
- No direct SQL should be scattered in the service/rule-engine layers — all persistence goes through this repository module, consistent with keeping the Rule Engine pure/testable (§27).

---

## 29. Suggested File/Module Structure

```
langgraph_agent/app/core_workflows/rent_renewal/
├── graph.py                         (existing stub — extend only if §26 optional node is chosen)
├── nodes.py                         (existing stub — untouched by Phase 1 unless above)
├── state.py                         (existing stub — untouched by Phase 1 unless above)
│
└── lease_expiry/                    ← NEW COMPONENT (Phase 1 module)
    ├── __init__.py
    ├── service.py                   ← orchestrates one scan run (§9, §10)
    ├── repository.py                ← DB access, built on database/rent_models.py (§28)
    ├── rule_engine.py                ← pure deterministic classification logic (§13, §14)
    ├── event_writer.py               ← idempotent event persistence (§16, §17)
    ├── config.py                     ← loads configured expiry windows (§14)
    ├── scheduler_entry.py            ← cron/worker entry point (§15)
    └── models.py                     ← (if not colocated in database/rent_models.py) ORM/typed models for lease_expiry_events, lease_expiry_scan_runs

database/
├── rent_models.py                    (existing — extend with new models per project convention, VERIFY AGAINST SOURCE for where models currently live)
├── schema.sql                        (existing — additive changes only)
└── migrations/                       ← NEW COMPONENT if no migrations folder currently exists (VERIFY AGAINST SOURCE)
    └── xxxx_add_lease_expiry_tracking.sql
```

Tests: given the repo currently has three scattered test locations (§7), Phase 1 tests should go under `langgraph_agent/tests/` (the most "proper" existing test folder, alongside `test_rent_reminder.py`), as `test_lease_expiry_tracking.py` and/or a `test_lease_expiry/` subpackage if the test count grows large — not a fourth new location.

---

## 30. Test Strategy

- **Unit tests** target the Rule Engine exclusively (pure functions, no DB) — fastest, most numerous.
- **Integration tests** target Repository + Event Writer against a real/test Postgres instance (reusing whatever test-DB fixture convention `test_rent_reminder.py` or `test_db.py` already establishes — `VERIFY AGAINST SOURCE`), verifying idempotency at the DB constraint level.
- **Service-level tests** run the full Phase 1 flow against a seeded set of leases (multiple windows, edge cases) and assert on resulting `lease_expiry_events` rows.
- No LLM/mocked-LLM tests are needed for Phase 1, since no LLM is invoked.

---

## 31. Unit Tests (Rule Engine)

- Given a lease exactly 90 days from expiry → classified into `90` window.
- Given a lease exactly 60/30/7 days from expiry → classified accordingly.
- Given a lease 45 days from expiry (between 60 and 30) → no window match (not yet crossed 30).
- Given a lease with `days_remaining <= 0` → classified as expired condition (§18), not into the `7` window.
- Given an empty/None `expiry_date` → raises a well-defined validation error (not an unhandled exception type).
- Given a window configuration list in unsorted order → engine still classifies correctly (order-independent).
- Given duplicate values in window configuration (e.g. `[90, 90, 60]`) → engine de-duplicates, does not classify twice.

## 32. Integration Tests (Repository + Event Writer)

- Active lease expiring in 90 days → one event with `window_days=90` created.
- Active lease expiring in 60 days → one event with `window_days=60` created.
- Active lease expiring in 30 days → one event with `window_days=30` created.
- Active lease outside all windows → zero events created.
- Already-expired active lease → handled per §18 (expired-condition path), no crash.
- Inactive lease → excluded from query entirely, zero events, zero errors logged for it.
- Lease with missing `expiry_date` → logged as data-quality error, zero events for that lease, run continues.
- Lease with invalid (unparseable) date value → same as above.
- Running the scan twice in a row against the same DB state → second run creates zero new events (all duplicates correctly skipped via §17 constraint).
- Explicit duplicate-insert attempt (simulating a race) → DB constraint prevents duplicate row; no exception surfaces as a run-fatal error.
- Timezone boundary: lease expiry date at the edge of a window when "now" is evaluated near midnight in the configured timezone → correct, non-off-by-one classification.
- Simulated database failure at scan start → run recorded as `FAILED`, no partial writes, no crash of the scheduler process itself.
- Simulated scheduler failure mid-run (process killed) → next run is idempotent-safe per §17/§24, no manual cleanup required.
- Retry behavior: after a mid-run failure, re-triggering the scan produces the correct final event set with no duplicates and no missing events.

---

## 33. Edge Cases

- Lease expiry date falls exactly on a window boundary (0-day rounding ambiguity) — must be resolved with a single, documented rounding rule (recommend: `days_remaining = (expiry_date - today).days`, no rounding, integer calendar-day difference).
- Lease with `days_remaining` far outside all windows (e.g. expiry two years away) — no event, cheap to filter early at query level.
- Lease that is already expired but still marked "active" in status (data inconsistency) — must not crash; treated as expired-condition per §18 and logged as a data-quality flag for operator visibility.
- Multiple windows crossed at once (e.g. first scan run after a long outage where a lease has simultaneously passed the 90-, 60-, and 30-day marks) — all applicable un-recorded windows must each get their own event in that single run, not just the nearest one.
- Very large number of active leases — query must be index-backed (§9 performance note) and paginated/batched if volume requires it (exact batching threshold left to implementing agent, but must not load an unbounded result set into memory naively without at least considering this).

---

## 34. Acceptance Criteria (Given/When/Then)

```
Scenario: Lease crosses the 90-day window
  Given an active lease with expiry_date exactly 90 days from today
  When the Lease Expiry Tracking scan runs
  Then exactly one lease_expiry_events row is created
   And its window_days = 90
   And its event_status = PENDING

Scenario: Scan re-run does not duplicate events
  Given a lease that already has a recorded 90-day event
  When the scan runs again with no change in lease data
  Then no new event is created for that lease/window pair
   And the existing event is unchanged

Scenario: Inactive lease is excluded
  Given a lease with status = terminated and expiry_date 30 days from today
  When the scan runs
  Then no lease_expiry_events row is created for that lease

Scenario: Missing expiry date is handled gracefully
  Given an active lease with a null expiry_date
  When the scan runs
  Then the lease is logged as a data-quality error
   And no event is created for that lease
   And the scan completes successfully for all other leases

Scenario: Duplicate scheduler execution is safe
  Given the scheduler is triggered twice in rapid succession
  When both runs attempt to classify the same lease/window
  Then only one lease_expiry_events row exists for that lease/window pair
   And no unhandled exception is raised by either run
```

---

## 35. Definition of Done

- [ ] All fields referenced in §12 confirmed against actual `rent_models.py`/`schema.sql` (no guessed field names remain in the implementation).
- [ ] Migration(s) applied additively; existing lease table untouched structurally beyond confirmed-necessary additive columns.
- [ ] `lease_expiry_events` table exists with the unique `(lease_id, window_days)` constraint enforced at the DB level.
- [ ] Expiry windows are configurable without a code change.
- [ ] Scheduler runs periodically without manual intervention and is safe to also trigger manually.
- [ ] Rule Engine has no DB or LLM dependency and is independently unit-testable.
- [ ] All tests in §31/§32 pass, including the duplicate-run and timezone-boundary cases.
- [ ] Run-level logging and a queryable run summary exist (§20, §21).
- [ ] No tenant-facing communication occurs anywhere in this phase's code.
- [ ] Documentation updated: this spec file plus a short addition to `docs/architecture.md` noting Phase 1's existence and its DB additions (actual edit of that file is out of scope for this spec, but implementing agent should do it as part of DoD).

---

## 36. Dependencies on Future Phases

- **Phase 2 (Renewal Reminder & Follow-up)** depends entirely on `lease_expiry_events` rows with `event_status = PENDING` produced by this phase — Phase 2 cannot be meaningfully tested end-to-end until Phase 1 is live.
- **Phase 3 (Renewal Intent + Manager Notification)** and **Phase 5 (Human Escalation)** may eventually want the `LEASE_EXPIRED` condition noted in §18/§33 as a trigger — Phase 1 only needs to record it correctly now, not act on it.
- **Phase 4 (Document Tracking)** has no direct dependency on Phase 1 beyond the shared `lease_id`/`tenant_id` identifiers already available in the existing lease model.

## 37. Implementation Sequence

1. Confirm actual schema/fields in `database/rent_models.py` and `schema.sql` (resolve all `VERIFY AGAINST SOURCE` items in this document first).
2. Write additive migration(s): `lease_expiry_events`, `lease_expiry_scan_runs`, expiry-window configuration, plus any missing lease fields identified in step 1.
3. Implement Rule Engine (pure, unit-tested first, in isolation).
4. Implement Repository (read path) against confirmed schema.
5. Implement Event Writer (idempotent insert) and verify duplicate-prevention with integration tests.
6. Implement Service orchestration (`service.py`) tying repository + rule engine + event writer together, with per-lease error isolation.
7. Implement scheduler entry point (cron/worker) and manual-trigger path.
8. Add logging/observability (run summary).
9. Run full integration + edge-case test suite (§31–§33).
10. Confirm Definition of Done (§35) before declaring Phase 1 complete and handing off the event contract (§16) to Phase 2 development.