# Workflow #4 — Lease / Renewal Workflow
# Phase 3 — Renewal Intent + Manager Notification
## Implementation Specification (SDD)

> **Status:** Draft specification for implementation. No code has been written or modified as part of producing this document.
>
> **Basis of inspection:** Produced from the repository **directory/file structure** supplied by the project owner, plus the Phase 1 (Lease Expiry Tracking) and Phase 2 (Renewal Reminder & Follow-up) specifications produced previously in this same effort. File **contents** of `orchestrator/*`, `checkpointer.py`, `department_nodes.py`, `nodes/intent_node.py`, `maintenance/nodes/human_approval.py`, `faq/nodes/classify_intent.py`, `database/rent_models.py`, `schema.sql`, `docs/architecture.md`, `docs/api_contracts.md`, and the two launcher/input-channel modules were **not** opened/read — only their names/locations are known from the tree. Every design decision that depends on those contents is explicitly flagged **`VERIFY AGAINST SOURCE`**. The implementing coding agent MUST confirm these before writing code and must adjust this spec if reality differs.

---

## 1. Phase Overview

Phase 3 is the first phase of Workflow #4 that performs genuine LLM-assisted **interpretation** rather than pure deterministic detection/communication. It picks up where Phase 2 leaves off: Phase 2 hands off a `renewal_response_events` row whenever a tenant responds, opts out, or the reminder cycle is exhausted. Phase 3's job is to classify the tenant's actual reply into a structured **renewal intent** (`YES` / `NO` / `NEGOTIATE` / `UNCLEAR` / `NO_RESPONSE`), deterministically transition the lease's renewal status based on that classification, and — when intent is `YES` (and, per §20, potentially `NEGOTIATE`) — deterministically notify the correct property manager with structured context, then stop and wait for manager-controlled next steps.

```
Phase 2 hand-off (renewal_response_events, PENDING)
        │
        ▼
   RETRIEVE TENANT MESSAGE + CONTEXT
        │
        ▼
   LLM: CLASSIFY INTENT (YES/NO/NEGOTIATE/UNCLEAR/NO_RESPONSE)
        │
        ▼
   DETERMINISTIC: UPDATE renewal_status
        │
        ▼
   DETERMINISTIC: STOP reminder loop (already stopped by Phase 2, confirmed here)
        │
        ▼
   IF intent qualifies → DETERMINISTIC: NOTIFY MANAGER (structured payload)
        │
        ▼
   HAND OFF → Phase 4 / human-in-the-loop manager action (out of Phase 3's control)
```

Phase 3 does **not** approve, reject, or negotiate the renewal itself. It classifies intent, changes status, and informs a human. The human (property manager) owns everything after that.

---

## 2. Business Objective

Ensure that once a tenant replies to a renewal reminder, their reply is understood correctly (using the LLM only for language interpretation, never for business decisions), the renewal record accurately reflects that intent, unnecessary further reminders definitively stop, and the right property manager is proactively given everything they need to act — without the system ever silently deciding the renewal outcome on the tenant's or its own behalf.

---

## 3. Scope

- Consuming `renewal_response_events` rows from Phase 2 (`event_status = PENDING`), specifically those with `stop_reason = TENANT_RESPONDED` as the primary driver of intent classification; other stop reasons are handled per §17/§18.
- Retrieving the actual tenant message content/context needed for classification.
- LLM-assisted classification of tenant intent into a fixed taxonomy (§5).
- Deterministic update of a `renewal_status` field/record based on classified intent.
- Deterministic confirmation that the reminder loop is stopped (defensive re-check against Phase 2).
- Deterministic manager identification/routing and structured notification (§14–§16) when intent qualifies.
- Multi-turn handling for `UNCLEAR` responses (asking a clarifying follow-up) and `NEGOTIATE` responses (capturing conditions, still routed to a manager, not resolved automatically).
- State schema, LangGraph node design, database changes, idempotency, and audit trail for all of the above.

## 4. Out of Scope

- Actually approving, rejecting, or setting new lease terms — exclusively a manager/human action (Phase 3 only reaches `PENDING_MANAGER_REVIEW`-type statuses, never `APPROVED`/`REJECTED`).
- Document collection for the renewal (Phase 4).
- Escalation workflows for non-responsive or stuck cases beyond what Phase 2 already flags as `MAX_REMINDERS_REACHED` (Phase 5, though Phase 3 must correctly route that stop-reason without misclassifying it as a "no response" *intent* — see §18).
- Building a new manager-facing UI/dashboard — Phase 3 only defines and sends the notification; how the manager reads/acts on it (app, email inbox, dashboard) depends on the notification channel actually available (§14).
- Contract/lease term negotiation logic — Phase 3 records that negotiation was requested and forwards it; it does not attempt to counter-offer or calculate new terms.

---

## 5. Intent Classification

**Taxonomy (fixed, deterministic set — the LLM's output must be constrained to exactly these values, never free text passed downstream as if it were a status):**

| Intent | Meaning | Example tenant text |
|---|---|---|
| `YES` (`WANTS_TO_RENEW`) | Tenant clearly wants to continue the lease, no conditions attached | "Yes", "I want to stay", "I'd like another year", "Can I continue?" |
| `NO` (`DOES_NOT_WANT_TO_RENEW`) | Tenant clearly does not want to renew | "No, I'll move out", "I'm leaving" |
| `NEGOTIATE` (`HAS_CONDITIONS`) | Tenant is willing to consider renewing but attaches a condition | "I'll stay if the rent doesn't increase", "Only if you fix the AC" |
| `UNCLEAR` | Message is renewal-related but does not clearly map to the above | "I'm not sure", "Let me think about it", "Maybe" |
| `NO_RESPONSE` | No tenant message content is actually present to classify (defensive case — see §18) | N/A — Phase 2 stop-reason was `MAX_REMINDERS_REACHED`, not an actual reply |

- **Classification mechanism:** the LLM is given the tenant's message plus minimal structured context (lease end date, days remaining, that this is a renewal-reminder reply) and is constrained (via structured/JSON output, function-calling, or equivalent — reusing whatever structured-output pattern the project already uses elsewhere, e.g. `faq/schemas.py` or `orchestrator/schemas.py` — `VERIFY AGAINST SOURCE`) to return one of exactly the five taxonomy values plus a short extracted rationale/quote for audit (§26), never a freeform status string.
- **Preferred reuse:** the existing `classify_intent` pattern from the FAQ workflow (`app/core_workflows/faq/nodes/classify_intent.py`) and/or the general-purpose `app/nodes/intent_node.py` are the most likely existing precedents for "LLM classifies into a fixed taxonomy" in this codebase — `VERIFY AGAINST SOURCE` for whether either can be extended with a renewal-intent taxonomy, or whether a new, narrowly-scoped classifier node is warranted because the taxonomy and context are domain-specific. Either way, the *pattern* (constrained structured-output classification, not open-ended generation) should match what's already established, not be invented fresh.
- **Confidence handling:** if the classification mechanism exposes a confidence score, a low-confidence result should be treated as `UNCLEAR` regardless of the raw label the LLM proposed, rather than trusting a low-confidence `YES`/`NO` — this is a deterministic downstream rule applied to the LLM's output, not a second LLM judgment call.

---

## 6. Conversation Flow

1. Phase 3 sweep/consumer picks up a `renewal_response_events` row (`PENDING`, `stop_reason = TENANT_RESPONDED`).
2. Retrieves the actual inbound tenant message text (and immediate surrounding context, e.g. which reminder it replied to) — via `related_reminder_id` (Phase 2 §23) and whatever inbound-message store the existing pipeline already persists (`VERIFY AGAINST SOURCE`, likely something the `checkpointer.py`-backed conversation state or the input-channel modules already retain).
3. Runs intent classification (§5).
4. Deterministically updates `renewal_status` (§12) based on the classified intent.
5. Branches:
   - `YES` → notify manager (§14), status → `PENDING_MANAGER_REVIEW`.
   - `NEGOTIATE` → notify manager with condition captured (§20), status → `PENDING_MANAGER_REVIEW` (with a `has_conditions` flag/marker).
   - `NO` → status → `DECLINED_BY_TENANT`, no manager notification required by default (configurable — some businesses may still want a manager FYI; see §14 routing note), reminder loop confirmed stopped, workflow instance for this lease effectively concludes (no further Phase 3 action).
   - `UNCLEAR` → status → `AWAITING_CLARIFICATION`, triggers a single clarifying follow-up message (§7, §19), not a full reminder-loop restart.
   - `NO_RESPONSE` (defensive/§18 case) → status → `PENDING_MANAGER_REVIEW` with an explicit "no engagement / max reminders reached" reason, routed to the manager as an FYI/escalation-adjacent case, distinct from a `YES`.
6. Every branch marks the `renewal_response_events` row `CONSUMED` and writes an audit record (§26).

---

## 7. Multi-turn Conversation Handling

- `UNCLEAR` is the only branch that reopens a conversational loop. Phase 3 sends one deterministic clarifying question (template-based, mirroring Phase 2's template approach — §11 of Phase 2 spec) asking the tenant to confirm intent in simpler terms.
- This clarification is **bounded**: at most one clarification round by default (configurable, e.g. `max_clarification_attempts`), after which a still-`UNCLEAR` or non-response result routes to the manager as `PENDING_MANAGER_REVIEW` with an "intent unresolved after clarification" marker, rather than looping indefinitely — this mirrors Phase 2's own anti-spam bounding principle (§7 of Phase 2 spec) so the two phases behave consistently.
- The tenant's reply to the clarification question re-enters the same classification step (§5) — it is not treated as a brand-new Phase 2 reminder-response, since Phase 2's reminder loop is already stopped by the time Phase 3 is active (§17).
- `NEGOTIATE` does not, by default, trigger an automatic multi-turn back-and-forth about terms — per §4/§20, negotiating terms is a human/manager job. Phase 3 may optionally send a single deterministic acknowledgement ("Thanks, we've shared your note with the property manager") but does not attempt to resolve the condition conversationally.

---

## 8. State Machine

**`renewal_status`** (deterministic, LLM never sets this value directly — only the classified `renewal_intent` feeds into the deterministic transition table below):

```
PENDING_TENANT_RESPONSE   (set by Phase 2 implicitly / default state while reminders are active)
        │ tenant intent = YES
        ▼
PENDING_MANAGER_REVIEW ──────────────► (Phase 3 ends here; Phase 4/manager action takes over)
        ▲
        │ tenant intent = NEGOTIATE
        │ (with has_conditions = true)
        │
        │ tenant intent = NO_RESPONSE (max reminders reached, no reply)
        │
PENDING_TENANT_RESPONSE
        │ tenant intent = NO
        ▼
DECLINED_BY_TENANT   (terminal for this phase)

PENDING_TENANT_RESPONSE
        │ tenant intent = UNCLEAR
        ▼
AWAITING_CLARIFICATION
        │ clarifying reply classified
        ├── resolves to YES/NO/NEGOTIATE/NO_RESPONSE → follow transitions above
        └── still UNCLEAR after max_clarification_attempts → PENDING_MANAGER_REVIEW (flagged "unresolved")
```

This state machine is implemented as deterministic application logic (a lookup/transition table keyed by classified intent + current status), not as LLM reasoning — consistent with the phase's core architectural rule.

---

## 9. LangGraph Nodes

Phase 3 is the first phase that meaningfully populates `rent_renewal/graph.py` and `nodes.py` (Phase 1 stayed graph-free by design; Phase 2 only lightly touched the graph for hand-off — Phase 3's classification step is inherently LLM-driven and belongs in the graph):

| Node (proposed) | Responsibility | LLM involved? |
|---|---|---|
| `intake_response_node` | Load the `renewal_response_events` row + related tenant message/context (§6 step 1–2) | No |
| `classify_intent_node` | Run §5 classification, return constrained taxonomy value + rationale | Yes (constrained/structured output only) |
| `apply_status_transition_node` | Deterministic §8 transition; writes `renewal_status` | No |
| `notify_manager_node` | Builds and sends §16 payload via existing Notification Service (reused from Phase 2 §24) | No |
| `clarification_node` | Sends the bounded clarifying question (§7) when intent is `UNCLEAR` | No (template-based, optional LLM polish only, same boundary rule as Phase 2 §10) |

This node set should be built following whatever conventions the existing `maintenance/nodes/` (11-node) and `faq/nodes/` (9-node) workflows already establish for node structure/naming — `VERIFY AGAINST SOURCE` — rather than inventing a new node-authoring style for this workflow. The `maintenance/nodes/human_approval.py` node in particular is the closest existing precedent in this repo for "system pauses and hands off to a human decision-maker," and its pattern (however it currently signals "waiting on a human") should be reused/mirrored for Phase 3's manager hand-off, rather than building a second human-in-the-loop mechanism — `VERIFY AGAINST SOURCE`.

---

## 10. State Schema

Extends `rent_renewal/state.py` (currently a stub). Proposed fields (exact typing/style to match whatever convention `maintenance/state.py` or `faq/state.py` already use — `VERIFY AGAINST SOURCE`):

```
RenewalIntentState:
  lease_id
  tenant_id
  property_id
  source_response_event_id        (FK → renewal_response_events)
  tenant_message_text              (raw text being classified)
  classified_intent                (YES | NO | NEGOTIATE | UNCLEAR | NO_RESPONSE)
  classification_rationale         (short LLM-extracted justification, audit only)
  clarification_attempts           (int, bounded per §7)
  renewal_status                   (current value per §8 state machine)
  has_conditions                   (bool, set when NEGOTIATE)
  condition_text                   (raw captured condition, if any)
  manager_notified                 (bool)
  manager_notification_id          (FK → manager_notifications, §16)
```

This state is scoped to a single lease's Phase 3 processing instance — it is not the whole conversation's global state, only the slice Phase 3 needs, consistent with how Phase 2 avoided introducing a parallel global state mechanism (§20 of Phase 2 spec) and instead relies on the existing checkpointer for any actual multi-turn conversational persistence.

---

## 11. Database Schema Changes

Additive only:

| Table/Field | Status |
|---|---|
| `renewal_status` field on the lease record (or a dedicated `lease_renewal_status` table if the lease table shouldn't be widened — decision depends on existing schema conventions) | **NEW COMPONENT** — `VERIFY AGAINST SOURCE` in `database/rent_models.py`/`schema.sql` for whether a renewal-status concept already exists anywhere (unlikely, since Workflow #4 is only a skeleton, but must be checked before assuming) |
| `renewal_intent_classifications` (audit table: every classification run, input text, output intent, rationale, timestamp) | **NEW COMPONENT** |
| `manager_notifications` (§16) | **NEW COMPONENT** |
| `renewal_response_events.event_status` | Existing (from Phase 2) — Phase 3's only write to that table is `PENDING → CONSUMED` |
| Manager/property-manager identity table (mapping property → responsible manager + contact info) | **Likely NEW COMPONENT** — nothing in the supplied tree suggests a manager/staff table exists; `VERIFY AGAINST SOURCE` in `rent_models.py` before assuming. If genuinely absent, this is a hard prerequisite blocker for §15 (notification routing) and must be flagged to the team as a dependency, not silently invented. |

---

## 12. Renewal Status Model

`renewal_status` enum (deterministic, exhaustive, matches §8):

```
PENDING_TENANT_RESPONSE
AWAITING_CLARIFICATION
PENDING_MANAGER_REVIEW
DECLINED_BY_TENANT
```

Values like `APPROVED` / `REJECTED` / `RENEWED` are explicitly **not** part of Phase 3's vocabulary — those belong to whatever Phase 4/manager-action process eventually sets them, and Phase 3 must never write them, even speculatively.

---

## 13. Intent Status Model

`classified_intent` enum (matches §5 taxonomy exactly): `YES`, `NO`, `NEGOTIATE`, `UNCLEAR`, `NO_RESPONSE`. Stored per-classification-attempt in `renewal_intent_classifications` (§11) — the *current* intent on the lease's renewal record is the most recent classification, but history is retained for audit (§26), not overwritten destructively.

---

## 14. Manager Notification

- Triggered deterministically (not by LLM judgment) whenever `apply_status_transition_node` (§9) results in `renewal_status = PENDING_MANAGER_REVIEW` — i.e., on `YES`, `NEGOTIATE`, and the `NO_RESPONSE`-after-max-reminders defensive case (§18). Not triggered on `NO` or `AWAITING_CLARIFICATION` (configurable per business preference whether `NO` also gets a manager FYI — default: no, since no manager action is required, but flagged as an easy config toggle, not a hardcoded exclusion).
- **Reuses the Notification Service built in Phase 2 (§24 of Phase 2 spec)** — the same channel-agnostic dispatch layer, extended (not duplicated) to support a "manager" recipient type in addition to "tenant." If the existing channel modules (`whatsapp_server.py`, `email_server.py`) only currently model tenant-facing contacts, sending to a manager's contact info is functionally the same operation (send a message to a phone/email) and should not require a new transport layer — only a new recipient-resolution step (§15).

---

## 15. Notification Routing

- **Manager resolution:** given a `property_id`, determine the responsible manager's contact info. This requires the manager/staff table flagged in §11 — if it does not exist, this is the single largest **NEW COMPONENT** dependency of this phase and must be resolved (even if only as a simple `property_id → manager_contact` mapping table) before notification can function at all. `VERIFY AGAINST SOURCE` exhaustively before assuming absence.
- **Channel for manager notification:** likely Email by default (managers are typically reached differently than tenants — e.g. an internal ops inbox), but should be configurable per manager, reusing the same channel-selection principle as Phase 2 §9 (explicit preference field if available, deterministic fallback order otherwise).
- Routing logic itself is fully deterministic — no LLM involvement in *deciding who* gets notified, only (optionally) in phrasing the notification body if any natural-language summary is included (§16).

---

## 16. Notification Payload

**NEW COMPONENT:** `manager_notifications` table + structured contract:

| Field | Notes |
|---|---|
| `id` | PK |
| `lease_id`, `tenant_id`, `property_id` | denormalized, consistent with Phase 1/2 pattern |
| `manager_id` / `manager_contact` | resolved per §15 |
| `tenant_name` | for display (matches the example: "Tenant: Ahmed") |
| `property_label` | e.g. "Unit 204" |
| `lease_end_date` | current lease end date |
| `renewal_intent` | classified intent (`YES` / `NEGOTIATE` / `NO_RESPONSE`-escalation) |
| `condition_text` | populated only when intent = `NEGOTIATE` |
| `response_datetime` | when the tenant replied (or when max-reminders was reached, for the `NO_RESPONSE` case) |
| `conversation_context_summary` | short, deterministically-templated summary (not free LLM narrative) referencing the actual reminder/response exchange — may optionally be LLM-polished for readability per the same boundary rule as §10 of Phase 2 (facts injected, not invented) |
| `renewal_status` | value at time of notification (`PENDING_MANAGER_REVIEW`) |
| `required_manager_action` | fixed, deterministic string per intent type, e.g. "Review and approve/reject renewal" (YES) or "Review tenant's condition and decide" (NEGOTIATE) or "Tenant unresponsive after N reminders — decide next step" (NO_RESPONSE) |
| `sent_at`, `delivery_status`, `channel` | mirrors Phase 2 §18 conventions |
| `run_id`, `correlation_id`, `created_at` | mirrors Phase 1/2 conventions |

This directly matches the example in the requirements ("Tenant: Ahmed / Property: Unit 204 / Lease End: Dec 31 / Intent: Wants to Renew / Status: Pending Manager Review") as a rendering of this structured payload via a template, not as free text generated per-instance.

---

## 17. Stop/Continue Rules

- Phase 3 must **confirm** (defensively re-check, not blindly trust) that Phase 2's reminder loop is stopped for this lease before proceeding — i.e., no reminder should be in-flight or scheduled once a `renewal_response_events` row is being processed. If Phase 2's stop-condition write and Phase 3's pickup could theoretically race (e.g. Phase 2 sweep and Phase 3 sweep run at overlapping times), Phase 3 should treat the presence of an unconsumed `renewal_response_events` row as authoritative that the loop is stopped (Phase 2 only creates that row *because* a stop-condition fired — §7 of Phase 2 spec) and does not need to independently re-verify Phase 2's internal state, only confirm no *new* Phase 2-originated reminder was sent after the stop (a data consistency assumption, not a new mechanism — flagged for the implementing agent's awareness, not a required new safeguard unless testing reveals an actual race).
- Once Phase 3 reaches a terminal-for-this-phase status (`PENDING_MANAGER_REVIEW` or `DECLINED_BY_TENANT`), no further Phase 2 or Phase 3 automatic messaging should occur for that lease's *current* renewal cycle — this is enforced by Phase 2 already having stopped (its own §7 stop-conditions) and by Phase 3 not re-opening the reminder loop under any classified intent.

---

## 18. Reminder Interaction

- Phase 3 consumes **all** `renewal_response_events` stop reasons from Phase 2 (§23 of Phase 2 spec: `TENANT_RESPONDED`, `OPT_OUT`, `MAX_REMINDERS_REACHED`, `LEASE_NO_LONGER_ACTIVE`), not only `TENANT_RESPONDED` — but only `TENANT_RESPONDED` (and its downstream clarification replies) actually goes through LLM classification (§5).
- `OPT_OUT` → Phase 3 sets `renewal_status` to a status indicating no further automated contact is appropriate (could reuse `DECLINED_BY_TENANT` if the business treats opt-out as equivalent to "not interested," or a distinct status if it should be tracked separately for compliance reasons — **business decision to confirm with the project owner, not assumed here**; default recommendation: treat as distinct from `DECLINED_BY_TENANT` since opt-out is about communication preference, not necessarily renewal intent, and route to manager as an FYI so a human decides how to proceed).
- `MAX_REMINDERS_REACHED` → treated as `NO_RESPONSE` intent per §5/§6, routed to manager per §14 as an escalation-flavored notification (distinct wording from a `YES`, via `required_manager_action`).
- `LEASE_NO_LONGER_ACTIVE` → no classification needed (there's no renewal decision to track); Phase 3 simply marks the event `CONSUMED` and logs it — no manager notification, no status write (the lease is already handled outside this workflow's renewal path).

---

## 19. Ambiguous Responses

- Handled via the `UNCLEAR` branch (§6, §7) — a single bounded clarification round, not an assumption in either direction (never silently default `UNCLEAR` to `YES` or `NO`).
- If the clarifying question itself goes unanswered (tenant doesn't reply to the clarification within a configurable window), this is treated the same as `NO_RESPONSE` after clarification exhaustion — routed to manager, not left open indefinitely.
- Classification of `UNCLEAR` vs. attempting to force a `YES`/`NO` is a deliberate design choice: false-positive `YES` classification is a worse business outcome (manager acts on a renewal that wasn't really confirmed) than an extra clarification round, so the classifier/prompt design should be biased toward `UNCLEAR` when genuinely ambiguous rather than guessing — this should be reflected in the classification prompt's instructions (an implementation detail for the coding agent, but the *bias direction* is a specification requirement).

---

## 20. Negotiation Handling

- `NEGOTIATE` is captured as a distinct intent, not folded into `YES` — the manager needs to know a condition was attached before the tenant would confirm.
- `condition_text` (§16) stores the tenant's actual stated condition (e.g. "if the rent doesn't increase"), extracted by the same constrained-classification step (§5) as a secondary structured field alongside the primary intent label — not a second LLM call, ideally a single structured-output call returning both `intent` and `extracted_condition` together.
- Phase 3 does **not** evaluate, accept, or reject the condition — that determination is exclusively the manager's, consistent with §4. Phase 3's only job is faithful capture and routing.
- No automatic counter-offer or re-negotiation loop is initiated by Phase 3.

---

## 21. Human-in-the-loop

- The property manager is the human decision-maker for every `PENDING_MANAGER_REVIEW` case. Phase 3's responsibility ends at delivering the notification (§14–§16); it does not poll for or process the manager's eventual decision — that is Phase 4's concern (per the master workflow's phase breakdown, document tracking, and presumably further phases beyond the five listed handle the actual approval capture) — `VERIFY AGAINST SOURCE`/confirm with the project owner exactly where "manager approves/rejects" is captured if not explicitly Phase 4, since the five phases listed for Workflow #4 (Expiry Tracking, Reminder, Intent+Notification, Document Tracking, Escalation) don't explicitly name an "approval capture" phase — flagged as an open question for the master SDD, not resolved by invention here.
- The `maintenance` workflow's `human_approval.py` node is the closest existing precedent in the repo for a system waiting on a human decision — its mechanism (webhook callback? polling? manual DB update? admin UI?) should be inspected and reused for however Phase 4/beyond eventually captures the manager's decision, even though that capture itself is out of Phase 3's scope — `VERIFY AGAINST SOURCE`.

---

## 22. Error Handling

- **Classification failure** (LLM call errors, times out, or returns a value outside the fixed taxonomy): treated as `UNCLEAR` by default (fail-safe, not fail-open to `YES`), logged as a classification error distinct from a genuine tenant `UNCLEAR` response (so error-rate monitoring — §25/§27 — can distinguish "tenant was ambiguous" from "the classifier broke").
- **Manager resolution failure** (no manager found for a property — §15 dependency gap): logged as a critical data-quality error; the `renewal_status` still transitions to `PENDING_MANAGER_REVIEW` (the tenant's intent is still correctly recorded) but `manager_notified = false` with a flagged error, so this doesn't silently disappear — it must surface for manual follow-up, not block the status transition itself.
- **Notification send failure:** reuses Phase 2's retry pattern (§17 of Phase 2 spec) — bounded retries via the shared Notification Service, terminal `FAILED` status logged if exhausted, not retried forever.
- **Per-event isolation:** one lease's classification/notification failure must not block processing of other `renewal_response_events` rows in the same sweep — same principle as Phase 1 §19 / Phase 2 §25.

---

## 23. Idempotency

- **Classification idempotency:** re-processing the same `renewal_response_events` row (e.g. due to a crash-and-retry) must not produce a second, conflicting classification record for the same source event — enforced via a unique constraint on `renewal_intent_classifications.source_response_event_id` for the *initial* classification (clarification-round replies get their own new source correlation, not reusing the same row, so they are naturally distinct).
- **Status-transition idempotency:** applying the same classified intent twice to the same lease must be a no-op (transition table is idempotent by construction — re-applying `YES` when already `PENDING_MANAGER_REVIEW` doesn't create a second review cycle).
- **Notification idempotency:** exactly one `manager_notifications` row per (lease_id, triggering classification event) — enforced via a unique constraint mirroring Phase 1/2's pattern, preventing a duplicate manager notification if the sweep is re-triggered.

---

## 24. Duplicate Notification Prevention

- DB-level unique constraint on `manager_notifications` keyed by `(lease_id, source_classification_id)` (or equivalently, `(lease_id, renewal_status)` at the point of transition into `PENDING_MANAGER_REVIEW`, whichever is less likely to be legitimately re-triggered — recommend `(lease_id, source_classification_id)` since a lease can only meaningfully enter `PENDING_MANAGER_REVIEW` once per classification event).
- Same `INSERT ... ON CONFLICT DO NOTHING`-then-check pattern established in Phase 1 §17 and Phase 2 §16 — the notify step only actually sends if the insert claims the row.
- If a manager needs to be re-notified deliberately (e.g. they missed it, ops wants a nudge), that is an explicit manual/operational action outside Phase 3's automatic flow, not a code-level retry of the same idempotency key.

---

## 25. Logging

Reuses `app/utils/loggers.py` exactly as Phase 1 (§20) and Phase 2 (§26) — `VERIFY AGAINST SOURCE`, no new logging setup.

Minimum log events:
- classification start/result (intent, confidence if available) — info; raw tenant text at debug level only (privacy consideration, §28)
- classification error (fail-safe to `UNCLEAR`) — error
- status transition applied (`from_status → to_status`) — info
- manager resolution success/failure — info/error
- notification sent/failed — info/error
- clarification round sent, and its eventual resolution — info
- sweep run summary (events consumed, classifications by intent type, notifications sent, errors) — info

---

## 26. Audit Trail

- `renewal_intent_classifications` (§11) is the authoritative audit record of every classification attempt: input text (or a reference to it), output intent, rationale, timestamp, whether it was the initial classification or a clarification-round follow-up.
- `manager_notifications` (§16) is the authoritative audit record of what was sent to which manager and when.
- Both tables are append-only from Phase 3's perspective — no destructive updates, only new rows, so the full history of how a lease's renewal intent was determined and communicated is reconstructable after the fact (important given the "tenant YES does not equal approval" business rule — an auditor should be able to see exactly what the tenant said and how it was interpreted).

---

## 27. Security

- Same least-privilege principle as Phase 1 §22 / Phase 2 §28: Phase 3 has read access to lease/tenant/manager data and insert-only access to its own new audit/notification tables, plus a narrow update on `renewal_response_events.event_status` and the `renewal_status` field/table.
- Manager contact info is handled only within the Notification Service/channel modules, never logged verbatim (§25).
- LLM classification calls should not include more tenant PII than necessary for the classification task (name/lease context may be relevant for a coherent prompt, but no unrelated tenant data should be included) — `VERIFY AGAINST SOURCE` for whatever data-minimization convention the existing `classify_intent`/`intent_node.py` already follows, and match it.

---

## 28. Privacy

- Raw tenant message text is sensitive; access to `renewal_intent_classifications.tenant_message_text` (or wherever it's stored) should be restricted the same way any other tenant conversational content already is in this codebase — `VERIFY AGAINST SOURCE` for existing conversational-data access controls (likely governed by however `checkpointer.py` state or input-channel message logs are currently protected).
- The manager notification payload (§16) intentionally includes only what's needed for the manager to act (lease/tenant/intent/condition) — it should not forward the tenant's full raw message verbatim unless the business wants that; the `conversation_context_summary` field is deliberately a *summary*, not a full transcript dump, to limit unnecessary PII exposure to the manager notification channel (which may be less access-controlled than the core system, e.g. a shared email inbox).
- If opt-out (§18) has legal/compliance implications (e.g., "do not contact" preferences), the distinct-status recommendation in §18 should be revisited with the project owner/legal stakeholder — this specification flags the consideration but does not resolve compliance policy.

---

## 29. Tests

Covered in detail across §30–§32 below; summary of coverage areas: intent classification accuracy across the taxonomy, deterministic status transitions, manager resolution and routing, notification payload correctness, idempotency/duplicate-prevention, clarification-round bounding, and error/fail-safe behavior.

## 30. Unit Tests

- Status transition table: every (current_status, classified_intent) pair maps to the exact expected `renewal_status`, including the terminal `NO` → `DECLINED_BY_TENANT` and the clarification-exhaustion → `PENDING_MANAGER_REVIEW` path.
- Fail-safe rule: classifier error or out-of-taxonomy output → `UNCLEAR`, never silently defaults to `YES`.
- Low-confidence classification (if confidence scoring exists) → forced to `UNCLEAR` regardless of raw label.
- Notification payload builder: given a lease/tenant/property/intent combination, produces a payload matching the §16 contract exactly (all required fields populated, `required_manager_action` text matches intent type).
- Clarification-round counter: increments correctly, forces manager routing once `max_clarification_attempts` exceeded.

## 31. Conversation Tests

- "Yes" / "I want to stay" / "I'd like another year" / "Can I continue?" → all classify as `YES`.
- "No, I'll move out" → classifies as `NO`.
- "I'll stay if the rent doesn't increase" → classifies as `NEGOTIATE`, `condition_text` populated with the rent-increase condition.
- "I'm not sure" / "Let me think about it" → classifies as `UNCLEAR`, triggers one clarification round.
- Clarification round: tenant follows up with "Actually yes" → re-classifies to `YES`, proceeds to manager notification.
- Clarification round: tenant does not reply within the configured window → treated as `NO_RESPONSE`-after-clarification, routed to manager.
- Multi-sentence/mixed message (e.g. "I'm happy here but need to check with my spouse") → should not be forced into `YES`; expected `UNCLEAR` or `NEGOTIATE` depending on prompt design — test asserts it is **not** `YES` (a conservative-classification regression guard, exact resulting label may be tuned during implementation but must never resolve to a false-positive `YES`).

## 32. Integration Tests

- Full flow: `renewal_response_events` row (`TENANT_RESPONDED`) → classification → status transition → manager notification row created → event marked `CONSUMED`.
- `OPT_OUT` stop-reason → no LLM classification call made, status set per §18 business rule, manager FYI routed.
- `MAX_REMINDERS_REACHED` stop-reason → treated as `NO_RESPONSE` intent, manager notified with escalation-flavored `required_manager_action` text.
- `LEASE_NO_LONGER_ACTIVE` stop-reason → event consumed, no status write, no notification.
- Duplicate sweep execution on the same classification outcome → no duplicate `manager_notifications` row (constraint from §24 verified).
- Manager resolution failure (no manager mapped to property) → status still transitions correctly, `manager_notified = false`, error logged and surfaced — verified it does not block the classification/status-write path.
- Notification channel send failure → bounded retries per Phase 2's pattern, terminal `FAILED` status, no duplicate notification row created by retries.

---

## 33. Acceptance Criteria (Given/When/Then)

```
Scenario: Clear renewal intent triggers manager notification
  Given a renewal_response_events row with stop_reason = TENANT_RESPONDED
   And the tenant's message is "Yes, I'd like another year"
  When Phase 3 processes the event
  Then classified_intent = YES
   And renewal_status transitions to PENDING_MANAGER_REVIEW
   And exactly one manager_notifications row is created
   And the payload includes tenant, property, lease end date, intent, and required manager action

Scenario: Tenant YES does not equal approval
  Given the scenario above has completed
  When the manager_notifications row is inspected
  Then renewal_status is PENDING_MANAGER_REVIEW, never APPROVED or RENEWED
   And no field in the system indicates the renewal has been finalized

Scenario: Negotiation is captured, not resolved automatically
  Given a tenant message "I'll stay if the rent doesn't increase"
  When Phase 3 processes the event
  Then classified_intent = NEGOTIATE
   And condition_text captures the rent condition
   And renewal_status transitions to PENDING_MANAGER_REVIEW
   And no automatic counter-offer or acceptance occurs

Scenario: Ambiguous response triggers one bounded clarification
  Given a tenant message "I'm not sure"
  When Phase 3 processes the event
  Then classified_intent = UNCLEAR
   And renewal_status transitions to AWAITING_CLARIFICATION
   And exactly one clarifying message is sent
   And no manager notification is sent yet

Scenario: Unresolved ambiguity after clarification routes to manager
  Given a lease already in AWAITING_CLARIFICATION with one clarification attempt used
   And the tenant's follow-up reply is again ambiguous
  When Phase 3 processes the follow-up
  Then no further clarification is sent
   And renewal_status transitions to PENDING_MANAGER_REVIEW
   And the notification indicates the intent was unresolved after clarification

Scenario: Duplicate processing does not double-notify
  Given a classification event has already produced a manager_notifications row
  When the same source event is processed again (e.g. due to a retry)
  Then no second manager_notifications row is created
```

---

## 34. Definition of Done

- [ ] All `VERIFY AGAINST SOURCE` items resolved against actual `orchestrator/`, `checkpointer.py`, `intent_node.py`/`classify_intent.py`, `human_approval.py`, and `rent_models.py` contents.
- [ ] Manager/property-manager identity resolution mechanism exists and is confirmed working (§11, §15) — this is a hard prerequisite; if genuinely absent from the existing schema, its addition is explicitly scoped and migrated as part of this phase.
- [ ] Intent classification is constrained to the fixed five-value taxonomy; no free-text intent ever reaches the status-transition logic.
- [ ] Status transitions are implemented as a deterministic lookup table, not LLM-driven branching.
- [ ] `renewal_status` never reaches an approval/rejection value from Phase 3 code.
- [ ] Manager notification reuses Phase 2's Notification Service rather than a new transport layer.
- [ ] Duplicate-notification and duplicate-classification constraints enforced at the DB level; tests in §32 pass.
- [ ] Clarification loop is bounded (`max_clarification_attempts` configurable, not hardcoded, not infinite).
- [ ] Fail-safe classification error handling (defaults to `UNCLEAR`, never `YES`) verified by test.
- [ ] Full audit trail (`renewal_intent_classifications`, `manager_notifications`) is append-only and queryable.
- [ ] Privacy considerations (§28) reviewed; manager payload does not over-expose raw tenant conversation.
- [ ] `docs/architecture.md` updated (or flagged for the team) to reflect Phase 3's new tables/nodes and the open question noted in §21 about where manager approval is actually captured.

---

## 35. Dependencies on Phase 2

- Phase 3 cannot run without Phase 2 producing `renewal_response_events` rows — it has no independent way to know a tenant responded, opted out, or exhausted reminders.
- Phase 3 reuses Phase 2's Notification Service (§24 of Phase 2 spec), template/messaging conventions, and idempotency/observability patterns for consistency.
- Any change to Phase 2's `renewal_response_events` contract (§23 of Phase 2 spec) is a breaking change for Phase 3 and must be coordinated.

## 36. Dependencies on Phase 4

- Phase 4 (Document Tracking) presumably begins once a renewal has actually progressed past manager review toward being finalized — the exact hand-off point (does Phase 4 start at `PENDING_MANAGER_REVIEW`, or only after a manager explicitly approves?) is **not fully specified by the master workflow description available** and should be confirmed with the project owner before Phase 4's spec is written; this document does not invent that boundary.
- What Phase 3 guarantees to Phase 4 (or whatever phase/mechanism captures manager approval first): an accurate, audited `renewal_status = PENDING_MANAGER_REVIEW` record, a complete `manager_notifications` entry, and — for `NEGOTIATE` cases — a captured `condition_text` that any downstream terms-finalization step will need.
- Phase 3 does not depend on Phase 4 for its own completion — it is functionally done once the manager is notified; Phase 4 depends on Phase 3, not the reverse.

## 37. Implementation Sequence

1. Confirm/resolve the manager-identity data gap (§11, §15) — this blocks everything else if genuinely missing.
2. Confirm actual conventions in `classify_intent.py`/`intent_node.py`, `human_approval.py`, `checkpointer.py`, and structured-output schema patterns (`orchestrator/schemas.py` or `faq/schemas.py`) — resolve remaining `VERIFY AGAINST SOURCE` items.
3. Write additive migrations: `renewal_intent_classifications`, `manager_notifications`, `renewal_status` field/table, manager-identity table if missing.
4. Implement the deterministic status-transition table (§8) and unit-test it exhaustively in isolation, before any LLM wiring.
5. Implement the constrained intent-classification node (§5, §9), reusing the existing classification pattern; unit- and conversation-test against the examples in §31.
6. Implement manager resolution + notification payload builder (§15, §16), extending Phase 2's Notification Service.
7. Implement clarification-round handling (§7, §19) with bounded retries.
8. Wire the LangGraph nodes (§9) into `rent_renewal/graph.py`/`nodes.py`/`state.py`, replacing the stubs.
9. Implement idempotency/duplicate-prevention constraints (§23, §24) and verify via the integration tests in §32.
10. Add logging/audit trail (§25, §26) and confirm privacy handling (§28).
11. Run full test suite (§30–§32), confirm Definition of Done (§34), and document the open Phase 3→Phase 4 boundary question (§36) for the project owner before proceeding to Phase 4's spec.