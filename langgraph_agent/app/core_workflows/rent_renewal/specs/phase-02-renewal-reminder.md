# Workflow #4 — Lease / Renewal Workflow
# Phase 2 — Renewal Reminder & Follow-up
## Implementation Specification (SDD)

> **Status:** Draft specification for implementation. No code has been written or modified as part of producing this document.
>
> **Basis of inspection:** Produced from the repository **directory/file structure** supplied by the project owner, plus the Phase 1 — Lease Expiry Tracking specification produced previously in this same effort. File **contents** of `input_channels/*`, `whatsapp_server.py`, `vapi_server.py`, `email_server.py`, `checkpointer.py`, `department_nodes.py`, `orchestrator/*`, `rent_reminder/*`, `database/rent_models.py`, `schema.sql`, `docs/architecture.md`, `docs/api_contracts.md` were **not** opened/read — only their names/locations are known from the tree. Every design decision that depends on those contents is explicitly flagged **`VERIFY AGAINST SOURCE`**. The implementing coding agent MUST confirm these before writing code and must adjust this spec if reality differs.

---

## 1. Phase Overview

Phase 2 consumes the `lease_expiry_events` produced by Phase 1 (status `PENDING`) and is responsible for the tenant-facing side of renewal: deciding which reminder to send, sending it over an appropriate existing channel, tracking whether it was delivered, detecting whether the tenant responded, and running a configurable follow-up cadence — stopping automatically once the tenant responds, an opt-out is recorded, or an escalation condition is reached. It hands off to Phase 3 (Renewal Intent + Manager Notification) the moment there is a tenant response to interpret, or an escalation condition is met.

Phase 2 is a **communication and tracking** layer. It does not decide whether a lease will be renewed, does not negotiate terms, and does not notify managers (Phase 3's job).

```
Phase 1 event (PENDING)
        │
        ▼
DETERMINE REMINDER → CONTACT TENANT → TRACK DELIVERY → TRACK RESPONSE → FOLLOW-UP
        │                                                     │
        │                                        tenant responds / escalation
        ▼                                                     ▼
   (loop, bounded)                                    HAND OFF → Phase 3
```

---

## 2. Business Objective

Make sure every tenant with an approaching lease expiry is proactively, but not excessively, contacted about renewal — using the channel(s) the project already supports — with a bounded, configurable, auditable reminder/follow-up cadence that stops the moment the tenant engages, opts out, or a defined escalation threshold is hit, and that reliably hands off to human/manager-facing Phase 3 rather than trying to close the renewal itself.

---

## 3. Scope

- Consuming `PENDING` events from `lease_expiry_events` (Phase 1 output).
- Deciding which reminder (first reminder, follow-up N, final follow-up) applies to a given lease at a given point in time.
- Composing a tenant-facing message from a template.
- Sending that message via an existing communication channel (WhatsApp / Email / Voice-VAPI — whichever is confirmed reachable outbound, see §8).
- Recording reminder history per lease (what was sent, when, via which channel, delivery status).
- Detecting a tenant response (inbound message on the same channel/thread) as a stop-condition.
- Running a configurable, bounded follow-up loop when there is no response.
- Handling opt-out signals if the existing channel infrastructure supports them.
- Emitting a hand-off event/state for Phase 3 when a response arrives or escalation triggers.
- Idempotency, retries, rate limiting, and observability of the whole reminder/follow-up process.

## 4. Out of Scope

- Determining whether a lease *will* be renewed (Phase 3).
- Notifying property managers (Phase 3).
- Collecting/validating renewal documents (Phase 4).
- Human escalation workflows beyond raising the escalation *condition* as a signal for Phase 3/5 to act on (Phase 5 owns actual escalation handling).
- Building new channel infrastructure from scratch if `input_channels/` already provides usable send/receive capability for a channel — extending an existing channel's capability (if something is missing, e.g. outbound-initiated WhatsApp send) is in scope only as a clearly marked gap, not a rebuild.
- Any LLM-driven decision about *whether* to send a reminder or *how many* follow-ups to allow — those are deterministic, configuration-driven decisions (see §6, §7), mirroring Phase 1's rule that date/threshold logic must not be delegated to the LLM. The LLM (if used at all in this phase) is scoped only to natural-language message composition from a template and/or interpreting free-text tenant replies for the narrow purpose of detecting "this is a response" vs. "this is noise" — not to make renewal or scheduling decisions.

---

## 5. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-1 | The system SHALL poll or otherwise consume `lease_expiry_events` rows with `event_status = PENDING`. |
| FR-2 | The system SHALL, for each consumed event, determine the correct reminder stage (first / follow-up-N / final) deterministically from reminder history + configuration (§6). |
| FR-3 | The system SHALL compose a tenant-facing message using a template (§10, §11), populated with lease/tenant/property data. |
| FR-4 | The system SHALL send the message via a channel selected per §9, reusing existing channel infrastructure. |
| FR-5 | The system SHALL record every reminder attempt (sent or failed) in a reminder-history table (§15) before considering the event `CONSUMED`. |
| FR-6 | The system SHALL NOT send a duplicate reminder for the same (lease_id, reminder_stage) pair (§16). |
| FR-7 | The system SHALL track delivery status per reminder where the channel provides delivery confirmation (§18). |
| FR-8 | The system SHALL detect an inbound tenant response correlated to an outstanding reminder and treat it as an immediate stop-condition for further automatic follow-ups on that lease (§19). |
| FR-9 | The system SHALL run follow-ups on a configurable schedule, bounded by a configurable maximum reminder count (§7). |
| FR-10 | The system SHALL stop the reminder loop and mark the lease's renewal-reminder cycle as "awaiting Phase 3" when: a tenant responds, an opt-out is recorded, or the maximum follow-up count is reached (escalation condition) (§7, §16). |
| FR-11 | The system SHALL emit a structured hand-off signal for Phase 3 consumption on every stop-condition, not only on "response received" (§23). |
| FR-12 | The system SHALL NOT contact a tenant on a lease-window event that Phase 1 has not actually recorded (no direct date computation inside Phase 2 — window/date truth comes only from Phase 1's event, per the shared architectural rule against LLM/duplicate date logic). |

---

## 6. Reminder Rules

- The **first reminder** for a lease is triggered by the *earliest* unconsumed `lease_expiry_events` row for that lease reaching Phase 2 (i.e., the largest configured window, e.g. `90` days, assuming default config from Phase 1 §14 — actual first-trigger window is whatever Phase 1's configuration currently defines, not hardcoded here).
- Each subsequent Phase 1 event for the same lease (e.g. the `60`-day, then `30`-day, then `7`-day event) is a candidate trigger for a **follow-up**, but only if the reminder loop for that lease is still active (i.e., no stop-condition has fired — §7, §19).
- If a stop-condition already fired for a lease (tenant responded / opted out / max-reminder reached), any *later* Phase 1 event for that same lease is still marked `CONSUMED` (so Phase 1's queue doesn't back up) but produces **no** outbound message — this is logged, not silently dropped.
- Reminder **stage** is derived from reminder history count for the lease (`stage = count(reminders already sent for this lease) + 1`), not from the Phase 1 window value directly — this decouples "how many Phase 1 windows exist" from "how many reminders Phase 2 sends," per the requirement that these intervals be independently configurable.

---

## 7. Follow-up Rules

- **NEW COMPONENT (configuration):** a `renewal_reminder_policy` configuration (table or config file, mirroring Phase 1's window-configuration approach in its own §14) defining, at minimum:
  - `max_reminder_count` (e.g. 3 — first reminder + 2 follow-ups) — configurable, not hardcoded.
  - `min_interval_between_reminders` (e.g. "no more than one reminder per lease per N days") — configurable, independent of Phase 1's window spacing, because Phase 1's windows (90/60/30/7) are not necessarily the desired *reminder* cadence.
  - `final_follow_up_marks_escalation` (boolean) — whether reaching `max_reminder_count` without a response automatically raises the escalation condition for Phase 3/5.
- The follow-up loop is **event-driven, not time-driven in isolation**: a follow-up is only actually sent when (a) a new Phase 1 event arrives for that lease AND (b) `min_interval_between_reminders` has elapsed since the last reminder AND (c) `max_reminder_count` has not been reached AND (d) no stop-condition is active. If (a) and (b)/(c) conflict (e.g. Phase 1 fires the `30`-day event but `min_interval_between_reminders` hasn't elapsed since the `90`-day reminder), the candidate follow-up is deferred, not dropped — see §14 for how deferred follow-ups are re-evaluated.
- **Stop conditions** (any one is sufficient):
  1. Tenant response detected (§19).
  2. Opt-out recorded (§7a below).
  3. `max_reminder_count` reached with no response → triggers `final_follow_up_marks_escalation` behavior if enabled.
  4. Lease status changes to non-active in the source lease table (e.g., manually renewed outside the system, terminated) — Phase 2 must re-check lease status before each send, not assume Phase 1's snapshot is still current (Phase 1 event data is a point-in-time snapshot; §12/§13 require a freshness check).
- **Opt-out handling (§7a):** if the underlying channel infrastructure exposes an opt-out/unsubscribe signal (e.g. WhatsApp opt-out, email unsubscribe) — `VERIFY AGAINST SOURCE` in `input_channels/whatsapp_server.py`, `input_channels/email_server.py` for whether this concept already exists. If it does not exist yet, an opt-out interpretation mechanism for Phase 2 is a **NEW COMPONENT**, scoped narrowly to "tenant text matches an opt-out pattern" recorded against the lease/tenant, not a full preference-center feature.

---

## 8. Communication Channels

Per the supplied tree, three input/output channel shims exist:

| Channel | Existing files | Status |
|---|---|---|
| WhatsApp | `input_channels/whatsapp_server.py`, launcher shim `whatsapp_server.py` at `langgraph_agent/` root | Existing — inbound handling presumed (it's under `input_channels/`); **outbound send capability for a proactive, non-reply message must be confirmed** — `VERIFY AGAINST SOURCE`. If only reactive (reply-to-inbound) sending exists, proactive outbound send is a **NEW COMPONENT** (or an extension of the existing WhatsApp module). |
| Email | `input_channels/email_server.py`, launcher shim `email_server.py`, plus `EMAIL_CHANNEL_ARCHITECTURE_REPORT.md` (existing doc — should be read by the implementing agent before building) | Existing — same caveat: confirm proactive-send capability exists — `VERIFY AGAINST SOURCE`. |
| Voice (VAPI) | `input_channels/vapi_server.py`, launcher shim `vapi_server.py` | Existing — voice is a poor fit for an unattended reminder message by default (no async "response tracking" equivalent to a text reply); recommend **not** selecting VAPI as a default reminder channel unless the existing architecture already uses it for outbound proactive calls — `VERIFY AGAINST SOURCE`. |

- **Reuse principle:** Phase 2 must not build a new send-message abstraction if `input_channels/` already exposes one usable across channels. If each channel module currently only exposes inbound webhook handling (typical for chat-platform integrations), the **outbound send** capability per channel — if missing — is the one legitimately **NEW COMPONENT** piece here, and should be added *inside* the existing channel module (e.g. `input_channels/whatsapp_server.py`) rather than as a parallel notification stack, to keep channel credentials/config in one place.
- A **Notification Service** (§24) sits above the channel modules as a thin, channel-agnostic dispatch layer used by Phase 2 — this is the one clearly new orchestration piece, but it should call *into* the existing channel modules, not reimplement channel transport.

---

## 9. Channel Selection

- Preferred channel per tenant should come from existing tenant/lease data if such a preference field already exists — `VERIFY AGAINST SOURCE` in `database/rent_models.py`. If no such field exists, this is a **NEW COMPONENT** (an additive `preferred_channel` column, or a simple deterministic fallback order).
- **Recommended deterministic fallback order** (only used if no explicit preference exists): WhatsApp → Email → (Voice/VAPI only if explicitly enabled for proactive outbound, per §8). This order is a configuration value, not a hardcoded chain, so it can be changed without a code deploy.
- Channel selection logic must be deterministic and independent of the LLM — the LLM (if involved at all) only composes the message text after the channel is already chosen.

---

## 10. Message Generation

- Message text is produced by filling a **template** (§11) with structured data: tenant name, property address, expiry date, days remaining, reminder stage (first/follow-up/final).
- **LLM usage boundary:** the LLM MAY be used to naturalize/polish template output (tone, phrasing) but MUST NOT be the source of factual content (dates, counts, lease terms) — those are injected as already-computed values from Phase 1's event + Phase 2's own reminder-history count, consistent with the project's standing rule that deterministic facts never originate from the LLM. If the project's existing `orchestrator/` nodes already have a pattern for "template + LLM polish" (e.g. used in `faq/nodes/compose_response.py` or `maintenance/nodes/response_generator.py`), that pattern should be reused rather than inventing a new one — `VERIFY AGAINST SOURCE`.
- Every generated message is persisted verbatim in reminder history (§15) — not just the template ID — so the exact text sent is auditable even if the template later changes.

---

## 11. Template Management

- **NEW COMPONENT** unless an existing template mechanism is found — `VERIFY AGAINST SOURCE` in `app/prompts/property_prompts.txt` (this looks like a prompts file for a different workflow, likely not a renewal-reminder template store, but must be checked) and in the `faq/knowledge_base/` pattern for any precedent on how the project stores reusable text content.
- Recommended representation: a small `renewal_reminder_templates` table (or a project-convention-consistent file store, matching whatever `property_prompts.txt` demonstrates) keyed by `(reminder_stage, channel)`, so first-reminder-via-WhatsApp can differ in tone/length from final-follow-up-via-Email.
- Templates use named placeholders (e.g. `{tenant_name}`, `{expiry_date}`, `{days_remaining}`) resolved deterministically by Phase 2 before any LLM polishing step.
- Template versioning: each stored/sent message in reminder history should reference which template (and version, if versioning is introduced) produced it, for audit purposes.

---

## 12. Tenant Identification

- Tenant identity for a given lease comes from `tenant_id` on the Phase 1 event payload (already denormalized per Phase 1 §16) — Phase 2 does not need to re-derive it, only to look up current contact details.
- **Freshness check requirement:** because Phase 1's event is a point-in-time snapshot, Phase 2 must re-fetch current tenant contact info (phone/email) from the source tenant table at send time, not rely on any contact info potentially embedded in the event — `VERIFY AGAINST SOURCE` for the existing tenant model location (presumed alongside lease data in `database/rent_models.py`).
- If a tenant record has no usable contact info for any allowed channel, this is a data-quality error (§25), not a silent skip.

---

## 13. Lease Identification

- Lease identity comes directly from `lease_id` on the consumed Phase 1 event.
- Before sending, Phase 2 must re-check the lease's current status (§7, stop-condition 4) — a lease could have changed state between Phase 1's scan and Phase 2's processing, especially for leases with long-lived pending events (e.g., a `90`-day event that sits unconsumed for some time). This re-check queries the same lease table Phase 1 reads from (read-only), reusing Phase 1's Lease Repository module (`rent_renewal/lease_expiry/repository.py`) if its query surface already supports a single-lease-by-id lookup, rather than duplicating that access pattern.

---

## 14. Reminder Scheduling

- Phase 2 does not need its own date-window scheduler the way Phase 1 does — it is fundamentally **event-driven off Phase 1's events**, plus a **deferred/retry queue** for follow-ups that are event-ready but blocked by `min_interval_between_reminders` (§7).
- **NEW COMPONENT:** a lightweight periodic sweep (reusing the same scheduler/cron mechanism established in Phase 1 §15, not a second scheduler) that:
  1. Consumes newly `PENDING` Phase 1 events (§5 FR-1).
  2. Re-evaluates any previously **deferred** follow-ups whose `min_interval_between_reminders` has now elapsed.
- This keeps a single scheduling mechanism in the codebase (Phase 1's cron/worker, extended to also invoke Phase 2's consumption step), rather than two independent schedulers — consistent with reusing existing infrastructure. If Phase 1's scheduler is implemented as a standalone service process, Phase 2's consumption step can run as a second job on the same worker/cron mechanism, or as its own worker triggered on the same cadence — implementation detail left to the coding agent, but "one scheduling mechanism, reused" is the requirement.

---

## 15. Reminder History

**NEW COMPONENT:** `lease_renewal_reminders` table.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID / bigserial PK | |
| `lease_id` | FK → leases | |
| `tenant_id` | FK → tenants | |
| `source_event_id` | FK → `lease_expiry_events.id` | the Phase 1 event that triggered this reminder (traceability) |
| `reminder_stage` | integer | 1 = first reminder, 2 = first follow-up, etc. |
| `channel` | text | `whatsapp` / `email` / `vapi` |
| `template_id` | FK / text | which template produced the message |
| `message_text` | text | exact text sent (§10) |
| `sent_at` | timestamptz | |
| `delivery_status` | enum/text | `PENDING`, `SENT`, `DELIVERED`, `FAILED`, `UNKNOWN` (§18) |
| `response_detected_at` | timestamptz, nullable | set when §19 detects a correlated inbound response |
| `run_id` | UUID | correlates to the sweep run that created it (§26) |
| `created_at` | timestamptz | audit |

This table is the single source of truth for §6's "how many reminders already sent" and §7's `max_reminder_count`/interval checks.

---

## 16. Idempotency

- **Event identity for a reminder** = `(lease_id, reminder_stage)`, mirroring Phase 1's `(lease_id, window_days)` uniqueness pattern.
- **DB-level unique constraint** on `(lease_id, reminder_stage)` in `lease_renewal_reminders`, enforced the same way Phase 1 enforces its own uniqueness — the sweep/consumption job uses `INSERT ... ON CONFLICT DO NOTHING` semantics for the "reminder record" row, and only proceeds to actually send if the insert succeeded (claims the stage), preventing two concurrent sweep runs from both sending the same-stage reminder.
- Re-running the periodic sweep must never re-send an already-sent stage for a lease, and must never re-process an already-`CONSUMED` Phase 1 event as if it were new.
- Marking a Phase 1 event `CONSUMED` (§25, Phase 1 §16/§25) happens only after the reminder-history row is durably written (send attempted, whether it ultimately succeeded or failed) — so a crash between "read PENDING event" and "write reminder row" simply leaves the event `PENDING` for the next sweep, which is safe (idempotent) by construction.

---

## 17. Retry Handling

- Send failures (channel API error, transient network failure) are retried a bounded number of times (configurable, e.g. `max_send_retries`), reusing whatever retry/backoff utility already exists in the codebase — `VERIFY AGAINST SOURCE` in `app/utils/helper.py` and the `orchestrator/rate_limiter.py` (its presence suggests the project already has some notion of throttling/backoff worth reusing rather than duplicating).
- After exhausting retries, the reminder row is recorded with `delivery_status = FAILED` and logged as an error (§25) — it does **not** silently count as "reminder sent" for stage-progression purposes, but it also must not be retried forever; the failure is terminal for that attempt, and the *next* eligible stage (if any) proceeds on its own schedule per §7/§14. Whether a failed send should be manually re-triggered is an operational decision, not an automatic Phase 2 behavior, to avoid runaway retries functioning as accidental spam.
- Retries must not create duplicate `lease_renewal_reminders` rows — the same idempotency key (`lease_id`, `reminder_stage`) claims the row once; retries update that row's status rather than inserting new ones.

---

## 18. Delivery Status

- Where the underlying channel provides delivery confirmation (e.g. WhatsApp delivery/read receipts, email bounce/delivery webhooks) — `VERIFY AGAINST SOURCE` for whether `input_channels/whatsapp_server.py` / `email_server.py` already expose such callbacks — Phase 2 should update `delivery_status` on the corresponding `lease_renewal_reminders` row when that confirmation arrives.
- If no delivery-confirmation mechanism currently exists for a channel, `delivery_status` remains `SENT` (meaning "handed to the channel successfully") rather than `DELIVERED`, and this limitation is explicitly documented, not silently assumed away. Building full delivery-receipt plumbing where none exists is flagged **NEW COMPONENT**, optional/lower-priority relative to the core reminder loop.
- `delivery_status = UNKNOWN` is reserved for channels/situations where even "handed to channel" cannot be confirmed synchronously (e.g. fire-and-forget async APIs without immediate ack).

---

## 19. Tenant Response Detection

- An inbound message on the same channel/thread as an outstanding reminder is the primary response signal. This relies on the existing input-channel webhook handling (`input_channels/*`) already routing inbound messages into the orchestrator/pipeline (`pipeline.py`, `department_nodes.py`) — Phase 2 does not reimplement inbound handling, it **subscribes to / is invoked by** that existing pipeline path once an inbound message is correlated to a tenant/lease with an active reminder cycle.
- **Correlation mechanism:** inbound messages must be matched to a `lease_id`/`tenant_id` with an open reminder cycle. If the existing pipeline already resolves inbound messages to a tenant identity (likely, since `intent_node.py` and the orchestrator presumably need this for other workflows too) — `VERIFY AGAINST SOURCE` — Phase 2 reuses that resolution rather than building a second one. The **renewal-specific** part that is genuinely new is: given a resolved tenant, check whether that tenant has an open (non-stopped) reminder cycle for any lease, and if so, mark it stopped (§7) and set `response_detected_at`.
- **Response vs. noise:** not every inbound message from a tenant with an open reminder cycle is necessarily about the lease (e.g., unrelated maintenance request). Per §4, narrow LLM/intent-classification use is acceptable here — reusing the existing `intent_node.py` / `classify_intent` pattern already used by the FAQ workflow (`faq/nodes/classify_intent.py`) is strongly preferred over building a new classifier — `VERIFY AGAINST SOURCE` for whether that classifier's intent taxonomy can be extended with a `renewal_response` intent, or whether a separate lightweight check is more appropriate. Either way: any inbound message from a tenant with an open cycle is treated conservatively — if classification is ambiguous, Phase 2 should still stop the *automatic reminder loop* (to avoid spamming someone who is actively engaging) even if the message content itself needs Phase 3/human interpretation.

---

## 20. Conversation State

- Phase 2 does not need to introduce a new conversational state machine for *reminders themselves* — reminder progression is tracked relationally (§15), not as LangGraph checkpointed conversation state.
- If/when a tenant response triggers hand-off into an actual conversational exchange (e.g., the tenant asks a question that needs a graph-driven reply), that exchange uses the **existing** checkpointer-backed state mechanism (`app/checkpointer.py`) exactly as other workflows do — Phase 2 does not create a parallel state/session mechanism. `VERIFY AGAINST SOURCE` for how `rent_reminder` or `maintenance` currently structure their per-tenant conversational state, and mirror that.

---

## 21. LangGraph Integration

- Consistent with Phase 1's boundary decision (§26 of Phase 1 spec): the **reminder-sending and follow-up-scheduling logic itself** (deciding stage, checking intervals, calling the Notification Service) is deterministic and should run as a backend service/sweep job, **not** as LLM-reasoning inside the graph — this avoids the same risk Phase 1 avoided (deterministic logic drifting into an LLM-controlled node).
- The **only** points where Phase 2 legitimately touches the LangGraph conversational layer are:
  1. Optional LLM polish of template text (§10) — a narrow, stateless node/utility call, not a full graph traversal.
  2. Response detection's intent classification (§19) — reuses existing intent-classification infra.
  3. The actual hand-off into a live conversational exchange once a tenant response needs interpretation — this is where `department_nodes.py` routing is used to enter the `rent_renewal` graph (`rent_renewal/graph.py`, `nodes.py`, `state.py` — currently stubs) for the first time with real behavior, or to route toward Phase 3 once it exists.
- `rent_renewal/graph.py` and `nodes.py` (currently stub files per the supplied tree) are the natural home for whatever minimal LangGraph node(s) handle bullet 3 above — this is the first phase that actually needs to populate those stubs, rather than Phase 1 which deliberately stayed out of the graph.

---

## 22. Database Changes

Additive only, no existing table redefinition:

| Table | Status |
|---|---|
| `lease_renewal_reminders` | **NEW COMPONENT** (§15) |
| `renewal_reminder_policy` (config) | **NEW COMPONENT** (§7) |
| `renewal_reminder_templates` | **NEW COMPONENT**, unless an existing template store is found (§11) |
| `lease_expiry_events` | Existing (from Phase 1) — Phase 2 updates `event_status` (`PENDING → CONSUMED`) as its only write to this table |
| Lease table (name TBD) | Existing — read-only from Phase 2 |
| Tenant table (name/location TBD) | Existing — read-only from Phase 2, `VERIFY AGAINST SOURCE` for exact contact-info fields (phone/email) and whether an opt-out flag already exists |

Migration(s) for the new tables go in the same migrations location established/confirmed in Phase 1 (§8/§29 of Phase 1 spec).

---

## 23. Event Contracts

Phase 2 both **consumes** Phase 1's contract and **produces** a new hand-off contract for Phase 3.

**Consumed (from Phase 1):** `lease_expiry_events` row, `event_status = PENDING`, per Phase 1 §16.

**Produced — NEW COMPONENT:** `renewal_response_events` (or equivalent hand-off table), one row per stop-condition:

| Field | Notes |
|---|---|
| `id` | PK |
| `lease_id`, `tenant_id`, `property_id` | denormalized, mirroring Phase 1's pattern |
| `stop_reason` | `TENANT_RESPONDED` / `OPT_OUT` / `MAX_REMINDERS_REACHED` / `LEASE_NO_LONGER_ACTIVE` |
| `last_reminder_stage` | integer, how many reminders had gone out |
| `related_reminder_id` | FK → `lease_renewal_reminders`, if `stop_reason = TENANT_RESPONDED` |
| `event_status` | `PENDING` → consumed by Phase 3 |
| `run_id`, `correlation_id`, `metadata`, `created_at` | same conventions as Phase 1 §16 |

Phase 3 is expected to poll/consume `renewal_response_events` with `event_status = PENDING`, exactly mirroring how Phase 2 consumes Phase 1's events — keeping a consistent producer/consumer pattern across the whole workflow.

---

## 24. Notification Service

**NEW COMPONENT** (§8): a thin, channel-agnostic dispatch module — e.g. `rent_renewal/notification/service.py` — exposing something like "send(tenant, channel, message) → delivery result," internally delegating to the appropriate existing channel module (`input_channels/whatsapp_server.py`, `email_server.py`, `vapi_server.py`). This is the single place Phase 2's reminder logic calls into for sending, so channel-specific quirks stay isolated from the reminder/follow-up business logic in §6/§7. It does not replace or duplicate the existing channel modules' transport logic — it is a thin router in front of them.

---

## 25. Error Handling

- **Per-lease isolation**, exactly as Phase 1 §19: one lease's failure (bad tenant data, channel error) must not abort the sweep for other leases.
- **Missing/invalid tenant contact info:** logged as data-quality error, event still marked `CONSUMED` (so it doesn't block the Phase 1 queue), but flagged for manual follow-up — no automatic retry loop for permanently-missing data.
- **Channel send failure:** handled per §17 (bounded retries, terminal `FAILED` status, no infinite retry).
- **Database failure at sweep start:** sweep run fails fast, recorded as `FAILED` (§26), next scheduled run retries naturally — same pattern as Phase 1 §19/§24.
- No error is silently swallowed; every skip/failure has a log entry and is counted in the run summary.

---

## 26. Logging

Reuse `app/utils/loggers.py` exactly as Phase 1 does (§20 of Phase 1 spec) — `VERIFY AGAINST SOURCE` for conventions, no second logging setup.

Minimum log events per sweep run:
- run start (`run_id`, number of pending Phase 1 events, number of deferred follow-ups re-evaluated)
- per-reminder decision (stage determined, channel selected) — debug
- per-send attempt (success/failure, channel) — info/error
- per-stop-condition fired (reason) — info
- per-hand-off event created for Phase 3 — info
- run end summary (counts: events consumed, reminders sent, deferred, stopped, errors)

---

## 27. Observability

- Reuse the run-summary pattern from Phase 1 §21 — either extend the same `lease_expiry_scan_runs`-style table with a Phase 2 run type, or a parallel `renewal_reminder_sweep_runs` table (**NEW COMPONENT** either way) with: `run_id`, `started_at`, `finished_at`, `events_consumed`, `reminders_sent`, `reminders_deferred`, `stop_conditions_fired`, `errors_count`, `status`.
- Useful metrics: reminders sent per stage (funnel: how many leases reach stage 2, stage 3), response rate (stop-condition breakdown), average time-to-response, escalation rate (`MAX_REMINDERS_REACHED` proportion) — exact wiring depends on whatever metrics pipeline the project uses, none of which is visible in the supplied structure (**NEW COMPONENT** if none exists, same caveat as Phase 1 §21).

---

## 28. Security

- Phase 2 has **read** access to lease/tenant contact data and **write/insert** access only to its own new tables (`lease_renewal_reminders`, `renewal_response_events`, config/template tables) plus a narrow **update** on `lease_expiry_events.event_status` — least-privilege, consistent with Phase 1 §22.
- Tenant contact info (phone/email) is handled only by the Notification Service and channel modules — it must not be duplicated into logs verbatim (log tenant/lease IDs, not raw phone numbers/emails) — `VERIFY AGAINST SOURCE` for whether existing channel modules already follow this convention, and match it.
- Any inbound-message correlation (§19) must not leak cross-tenant data — response detection must be scoped strictly to the responding tenant's own lease(s).
- Manual-trigger/admin endpoints (if any expose "force-send reminder" for ops) must reuse existing auth mechanisms — `VERIFY AGAINST SOURCE` in `docs/api_contracts.md`, same caveat as Phase 1 §22.

---

## 29. Rate Limiting

- The project already has `app/orchestrator/rate_limiter.py` — this **must** be inspected and reused if it provides per-tenant or per-channel throttling suitable for outbound reminder sends, rather than building a second rate-limiting mechanism — `VERIFY AGAINST SOURCE`.
- Independent of any technical rate limiter, the **business-level** anti-spam controls are the ones defined in §7 (`max_reminder_count`, `min_interval_between_reminders`) — these are mandatory regardless of whether a technical rate limiter exists, since they encode "don't annoy the tenant" rules, not just "don't overload the channel API" rules.
- If sending to many tenants in one sweep, outbound sends should be throttled at the channel-API level to respect provider rate limits (e.g. WhatsApp/Email provider limits) — reusing `rate_limiter.py` if it already models this, otherwise flagged **NEW COMPONENT** (thin wrapper, not a new rate-limiting algorithm from scratch).

---

## 30. Failure Recovery

- Same principle as Phase 1 §24: because reminder-sending is idempotent (§16) and state lives entirely in the database (reminder history, event statuses), recovery from any failure is "re-run the sweep." No compensating transactions needed.
- A partially-completed sweep (some reminders sent, then a crash) leaves the successfully-sent reminders correctly recorded and the not-yet-processed events still `PENDING` — the next sweep picks up exactly where it left off, with no duplicate sends (guaranteed by the `(lease_id, reminder_stage)` constraint).

---

## 31. Suggested File Structure

```
langgraph_agent/app/core_workflows/rent_renewal/
├── graph.py                          (existing stub — first real usage: §21 bullet 3, hand-off/response-interpretation entry node)
├── nodes.py                          (existing stub — same)
├── state.py                          (existing stub — same)
│
├── lease_expiry/                     (Phase 1 — already specified)
│   └── ...
│
└── renewal_reminder/                 ← NEW COMPONENT (Phase 2 module)
    ├── __init__.py
    ├── service.py                    ← orchestrates one sweep (consume events + re-evaluate deferrals)
    ├── policy.py                     ← loads renewal_reminder_policy config (§7)
    ├── stage_resolver.py             ← determines reminder stage from history (§6)
    ├── template_engine.py            ← template resolution + placeholder fill (§10, §11)
    ├── notification/
    │   ├── __init__.py
    │   └── service.py                ← channel-agnostic dispatch (§24), calls into input_channels/*
    ├── response_detector.py          ← correlates inbound messages to open reminder cycles (§19)
    ├── repository.py                 ← DB access for lease_renewal_reminders, renewal_response_events
    └── scheduler_entry.py            ← hooks into Phase 1's scheduler mechanism (§14)

database/
├── rent_models.py                    (existing — extend with new models, VERIFY AGAINST SOURCE for convention)
├── schema.sql                        (existing — additive changes only)
└── migrations/
    └── xxxx_add_renewal_reminder_tracking.sql
```

Tests placed under `langgraph_agent/tests/` alongside `test_rent_reminder.py` and the Phase 1 tests, as `test_renewal_reminder.py` / a `test_renewal_reminder/` subpackage — consistent with the Phase 1 spec's decision not to add a fourth scattered test location.

---

## 32. Tests

**Unit tests** (pure logic, no DB/channel):
- Stage resolution: 0 prior reminders → stage 1; 1 prior → stage 2; etc.
- Policy evaluation: reminder blocked when `min_interval_between_reminders` not yet elapsed; allowed once elapsed.
- Policy evaluation: reminder blocked once `max_reminder_count` reached, escalation flag set correctly.
- Template placeholder resolution with complete vs. missing data.

**Integration tests** (DB + mocked channel modules):
- First Phase 1 event for a lease → exactly one `lease_renewal_reminders` row created, `reminder_stage = 1`, `PENDING` Phase 1 event marked `CONSUMED`.
- Second Phase 1 event for the same lease, interval satisfied → stage 2 reminder created.
- Second Phase 1 event, interval **not** satisfied → deferred, no row created yet; later re-swept once interval elapses → row created then.
- Duplicate sweep execution → no duplicate `lease_renewal_reminders` row for the same `(lease_id, reminder_stage)`.
- Tenant response arrives after stage-1 reminder → stop-condition fires, `renewal_response_events` row created with `stop_reason = TENANT_RESPONDED`, no further reminders sent for that lease even if more Phase 1 events arrive.
- Max reminder count reached with no response → `stop_reason = MAX_REMINDERS_REACHED` event created.
- Lease becomes inactive between Phase 1 event creation and Phase 2 processing → `stop_reason = LEASE_NO_LONGER_ACTIVE`, no send attempted.
- Missing tenant contact info → data-quality error logged, event marked `CONSUMED`, no reminder row with a `SENT` status created.
- Channel send failure with retries → row ends `FAILED` after exhausting `max_send_retries`, no duplicate rows from retry attempts.
- Opt-out signal detected → stop-condition fires, `stop_reason = OPT_OUT`.

---

## 33. Edge Cases

- Multiple Phase 1 events for the same lease become `PENDING` simultaneously (e.g. after a long scheduler outage, mirroring Phase 1 §33) — Phase 2 must process them in window order (largest window / earliest stage first) and correctly derive incremental stages, not attempt to send multiple reminders in the same sweep pass for the same lease.
- Tenant responds to an **old** reminder thread (e.g. replies to the first reminder days after a follow-up was already sent) — still a valid stop-condition; Phase 2 does not need to disambiguate which specific reminder was replied to, only that the tenant engaged.
- Tenant has no active reminder cycle but sends a message referencing "my lease renewal" unprompted — out of scope for Phase 2's automatic stop-detection (which is scoped to *open cycles*); this is a Phase 3/general-conversation concern.
- A lease's expiry date changes after reminders have already gone out (lease amended) — Phase 1 §17 already flags this as an out-of-scope limitation for event invalidation; Phase 2 inherits that limitation and should not attempt to "unsend" or invalidate already-sent reminders — flagged as a known limitation, not silently handled.
- Two different Phase 1 windows collapse onto the same computed reminder stage due to `min_interval_between_reminders` deferral logic causing re-ordering — stage numbers must still be assigned strictly by actual send order, not by which Phase 1 window triggered them.

---

## 34. Acceptance Criteria (Given/When/Then)

```
Scenario: First reminder is sent on first Phase 1 event
  Given a lease with no prior renewal reminders
   And a new lease_expiry_events row with event_status = PENDING for that lease
  When the renewal reminder sweep runs
  Then a lease_renewal_reminders row is created with reminder_stage = 1
   And the message is sent via the selected channel
   And the source lease_expiry_events row is marked CONSUMED

Scenario: Follow-up is deferred until the minimum interval elapses
  Given a lease whose stage-1 reminder was sent 2 days ago
   And min_interval_between_reminders = 5 days
   And a new PENDING Phase 1 event for that lease
  When the sweep runs
  Then no new reminder is sent
   And the follow-up is recorded as deferred, to be re-evaluated later

Scenario: Tenant response stops the reminder loop
  Given a lease with an open reminder cycle at stage 1
  When an inbound message from that tenant is correlated to the open cycle
  Then a renewal_response_events row is created with stop_reason = TENANT_RESPONDED
   And no further automatic reminders are sent for that lease
   And a hand-off event is available for Phase 3

Scenario: Maximum reminder count reached without response
  Given a lease that has already received max_reminder_count reminders with no response
   And a further PENDING Phase 1 event exists for that lease
  When the sweep runs
  Then no additional reminder is sent
   And a renewal_response_events row is created with stop_reason = MAX_REMINDERS_REACHED
   And the Phase 1 event is still marked CONSUMED

Scenario: Duplicate sweep execution does not double-send
  Given the sweep is triggered twice in rapid succession
  When both runs attempt to process the same PENDING event
  Then only one lease_renewal_reminders row exists for that lease/stage
   And no duplicate message is sent to the tenant
```

---

## 35. Definition of Done

- [ ] All fields/assumptions marked `VERIFY AGAINST SOURCE` in this document confirmed against actual channel modules, tenant/lease models, and existing rate-limiter/logging/intent-classification code.
- [ ] Migrations applied additively for `lease_renewal_reminders`, `renewal_reminder_policy`, `renewal_reminder_templates`, `renewal_response_events`, and any run-summary table.
- [ ] Reminder cadence (`max_reminder_count`, `min_interval_between_reminders`) is configurable without a code change.
- [ ] Uniqueness constraint on `(lease_id, reminder_stage)` enforced at the DB level; duplicate-sweep test passes.
- [ ] Notification Service dispatches through existing channel modules (`input_channels/*`) without duplicating transport logic.
- [ ] Tenant response detection reuses existing inbound-message/intent-classification pipeline rather than building a parallel one.
- [ ] Reminder loop correctly stops on all four stop-conditions (§7) and produces a `renewal_response_events` row in every case.
- [ ] All tests in §32 pass, including deferred-follow-up and duplicate-sweep cases.
- [ ] Run-level logging and observability in place (§26, §27).
- [ ] No renewal *decision* is made by Phase 2 anywhere in the code — only communication, tracking, and hand-off.
- [ ] `docs/architecture.md` updated (or a note added for the team to update it) to reflect Phase 2's new tables and its position between Phase 1 and Phase 3.

---

## 36. Dependency on Phase 1

- Phase 2 cannot run meaningfully without Phase 1 producing `lease_expiry_events` rows — it has no independent notion of "which leases are approaching expiry."
- Phase 2 reuses Phase 1's scheduler mechanism (§14), Lease Repository read pattern (§13), and general architectural conventions (event contract shape, idempotency-via-unique-constraint pattern, run-summary observability pattern) for consistency.
- Any change to Phase 1's event contract (§16 of Phase 1 spec) is a breaking change for Phase 2 and must be coordinated.

## 37. Dependency on Phase 3

- Phase 3 (Renewal Intent + Manager Notification) is the consumer of `renewal_response_events` — Phase 2 is complete/functional on its own (reminders go out, loop stops correctly) even before Phase 3 exists, but its output has no downstream effect until Phase 3 is built to consume it.
- Phase 3 is expected to interpret the tenant's actual response content (intent: wants to renew / does not want to renew / has questions) — Phase 2 deliberately does **not** attempt this interpretation beyond the narrow "is this a response at all" check in §19, keeping the renewal-decision boundary clean between phases.
- The `related_reminder_id` and `last_reminder_stage` fields on `renewal_response_events` (§23) exist specifically so Phase 3 has enough context (what was last sent, when) without re-querying Phase 2's full reminder history for every hand-off.