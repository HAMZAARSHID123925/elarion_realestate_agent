# Workflow #4 — Lease / Renewal Workflow
# Phase 4 — Renewal Document Tracking
## Implementation Specification (SDD)

> **Status:** Draft specification for implementation. No code has been written or modified as part of producing this document.
>
> **Basis of inspection:** Produced from the repository **directory/file structure** supplied by the project owner, plus the Phase 1 (Lease Expiry Tracking), Phase 2 (Renewal Reminder & Follow-up), and Phase 3 (Renewal Intent + Manager Notification) specifications produced previously in this same effort. File **contents** of `database/rent_models.py`, `schema.sql`, `checkpointer.py`, `department_nodes.py`, `orchestrator/*`, `maintenance/nodes/human_approval.py`, `input_channels/*`, `docs/architecture.md`, `docs/api_contracts.md`, `docs/deployement.md` were **not** opened/read — only their names/locations are known from the tree. Every design decision that depends on those contents is explicitly flagged **`VERIFY AGAINST SOURCE`**. The implementing coding agent MUST confirm these before writing code and must adjust this spec if reality differs.
>
> **Open dependency carried forward from Phase 3 (§36 of that spec):** the master workflow's five phases do not explicitly name a step where the property manager's approval decision itself is captured. Phase 3 ends at `renewal_status = PENDING_MANAGER_REVIEW`; this Phase 4 specification assumes an approval-capture mechanism exists or will exist to produce a `renewal_status = APPROVED`-equivalent trigger, but **does not invent that mechanism**. Where this document says "on renewal approval," it means "on whatever event/status the approval-capture step — wherever it lives — emits," and that hand-off point is flagged as a prerequisite to confirm with the project owner, not assumed to already exist in `rent_renewal/nodes.py` today.

---

## 1. Phase Overview

Phase 4 begins once a renewal has moved past manager review to an approved/initiated state (per the open dependency above) and manages the operational lifecycle of the paperwork needed to actually complete the renewal: determining which documents are required, requesting them from the tenant, receiving and tracking their status, reminding the tenant of anything outstanding, and recognizing when the checklist is complete — at which point it hands off to whatever comes next (Phase 5 / final execution, per §26).

```
RENEWAL APPROVED/INITIATED (external trigger, see prerequisite note above)
        │
        ▼
   BUILD DOCUMENT CHECKLIST (from configured requirements)
        │
        ▼
   REQUEST DOCUMENTS (tenant-facing, reuses Phase 2 channel infra)
        │
        ▼
   RECEIVE DOCUMENTS (tenant submission, inbound channel)
        │
        ▼
   TRACK STATUS (per-document, deterministic)
        │
        ├── missing/incomplete → REMIND (bounded, mirrors Phase 2 anti-spam rules)
        │
        ▼
   CHECKLIST COMPLETE
        │
        ▼
   HAND OFF → Phase 5 / next step
```

Phase 4 is a **document lifecycle tracking** layer. It does not draft, generate, or legally validate document content, and it does not make the final decision that a document is acceptable — that is a human review/approval boundary (§11, §19).

---

## 2. Business Objective

Ensure that once a renewal is approved to proceed, the tenant is asked for exactly the right set of documents (as configured by the business, never invented by the system), that submission status is tracked accurately and auditable, that tenants are reminded about outstanding items without being spammed, and that a human reviewer — not the system — is the one who ultimately approves or rejects any submitted document, so the renewal can reliably progress once everything required is in place.

---

## 3. Scope

- Building a per-renewal document checklist from a configured document-requirements definition (§6, §7).
- Requesting documents from the tenant via existing communication channels (reused from Phase 2).
- Receiving tenant-submitted documents (file uploads / attachments) via whichever existing channel supports inbound file transfer.
- Tracking per-document status through a defined lifecycle (§8).
- Detecting missing/outstanding documents and running a bounded reminder cadence (§12, §13).
- Storing document metadata and a reference to the underlying file content (§15, §17) — not necessarily the file bytes themselves in the primary database.
- Recording an audit trail of status changes, submissions, and any human review actions (§21).
- Handing off to whatever consumes a "checklist complete" state (§26).

## 4. Out of Scope

- Drafting, generating, or altering legal document text/clauses — Phase 4 only tracks documents that already exist as configured templates or that the tenant/manager supplies; it never authors legal content.
- Deciding whether a submitted document is legally sufficient/acceptable — that is a human reviewer's call (§11).
- E-signature technology integration itself (the actual cryptographic/legal signing mechanism) unless something already exists in the repository for this — nothing in the supplied tree suggests an e-signature integration exists, so this is flagged **NEW COMPONENT** at the boundary only if genuinely required; Phase 4 tracks *whether* a signature has been captured, but building a signing product from scratch is out of scope of this workflow phase (see §14).
- Final lease execution / countersigning workflow beyond document completeness tracking.
- Escalation handling beyond raising the "checklist stalled" condition for Phase 5 to act on (§26) — Phase 5 owns actual escalation behavior.

---

## 5. Document Types

Per the requirements' example checklist, and treating this as a **configurable list**, not a hardcoded one (consistent with Phase 1's expiry-window and Phase 2's reminder-policy configurability principle):

| Document type | Notes |
|---|---|
| Renewal Agreement | The core renewal contract document — its *content/template* is business-owned, not system-generated (§4). |
| Tenant Identification | Identity verification document (e.g. ID copy). |
| Required Disclosure | Jurisdiction/business-specific disclosure document(s) — plural is likely in practice; the configuration should support zero-or-more disclosure documents, not assume exactly one. |
| Signature | Tracked as a distinct checklist item/state (§14) rather than folded into "Renewal Agreement," since a document can be *received* before it is *signed*. |

This list is the example set from the requirements, not an exhaustive or hardcoded one — see §7 for how the actual per-property/per-jurisdiction requirement set is configured. Nothing in the supplied repository structure suggests an existing document-type taxonomy (no `documents` table or module is visible anywhere in the tree), so the entire document-type concept is **NEW COMPONENT**.

---

## 6. Document Requirements

- **NEW COMPONENT:** a `renewal_document_requirements` configuration (table, mirroring Phase 1 §14's expiry-window configuration pattern and Phase 2 §7's reminder-policy pattern) defining which document types are required, optionally scoped by property/jurisdiction if the business needs that granularity (e.g. some properties may require an additional local-law disclosure).
- Requirements are **configuration data**, never inferred or generated by the LLM — this mirrors the workflow-wide rule (Phase 1's "no LLM date math," Phase 3's "no LLM status transitions") applied here as "no LLM document-requirement invention." The checklist-building step (§7) is a deterministic lookup against this configuration.
- Each requirement entry should specify: document type, whether it's mandatory or conditional, and (if a template exists) a reference to the approved template (§4 — Phase 4 references templates, it does not author them).

---

## 7. Checklist Model

- **NEW COMPONENT:** `renewal_document_checklists` (one row per renewal instance) + `renewal_document_checklist_items` (one row per required document within that checklist), built deterministically from §6's configuration at the moment the renewal-approved trigger fires.
- The checklist is a **snapshot**: once built for a given renewal, later changes to the global requirements configuration do not retroactively alter an in-progress checklist (consistent with Phase 1 §17's point that event data is a point-in-time snapshot) — this avoids a tenant being asked for a document that wasn't on their original checklist, or a checklist silently going stale mid-process. If the business needs to add a requirement to an in-progress renewal, that is an explicit manual/operational action, not automatic.
- Each checklist item tracks its own status (§8) independently — the checklist as a whole is "complete" only when every mandatory item reaches a terminal-accepted status.

---

## 8. Document Status

Per-document-item status lifecycle. Evaluating against what the existing project actually models elsewhere (nothing document-related exists in the supplied tree, so this is derived from first principles, informed by Phase 3's status-model discipline of "only include what's actually needed, don't pre-invent approval-adjacent states the system doesn't act on"):

```
PENDING        (checklist item created, not yet requested)
REQUESTED      (request sent to tenant)
RECEIVED       (tenant submitted something for this item)
UNDER_REVIEW   (received, awaiting human review — see §11)
APPROVED       (human reviewer accepted it)
REJECTED       (human reviewer rejected it — item reverts toward REQUESTED for resubmission, see below)
EXPIRED        (requested but not received within a configured window — mirrors Phase 2's bounded-reminder-then-escalate pattern)
```

- All seven statuses from the requirements' example are architecturally justified and retained: `PENDING`/`REQUESTED`/`RECEIVED` map to the request→receive flow (§10), `UNDER_REVIEW`/`APPROVED`/`REJECTED` map directly to the human-review boundary (§11), and `EXPIRED` is needed to terminate the reminder loop the same way Phase 2 needed `MAX_REMINDERS_REACHED` — without it, missing documents would be tracked indefinitely with no stop condition, which would violate the same anti-open-loop principle established in Phase 2 §7.
- `REJECTED → REQUESTED` is a valid re-transition (not a new status) when a human reviewer rejects a document and the tenant needs to resubmit — this is deterministic re-entry into the request flow, not a special state.
- The **checklist-level** status (distinct from per-item status) is derived, not separately stored redundantly: `COMPLETE` when all mandatory items are `APPROVED`; otherwise `IN_PROGRESS` (or a similarly named non-terminal aggregate) — computing this from item statuses avoids a second source of truth that could drift.

---

## 9. Document Metadata

Per checklist item / per submission, metadata needed regardless of storage mechanism (§15):

| Field | Purpose |
|---|---|
| `document_type` | links back to §5/§6 |
| `status` | §8 |
| `requested_at` | when the request was sent |
| `received_at` | when the tenant's submission arrived |
| `reviewed_at`, `reviewed_by` | human review audit (§11, §21) |
| `expires_at` | deadline before `EXPIRED` (§13) |
| `file_reference` | pointer to actual content (§15/§17), not the content itself |
| `version` | §22 |
| `rejection_reason` | populated by the human reviewer on `REJECTED`, needed so the tenant's resubmission request (§10) can explain what to fix |

---

## 10. Tenant Document Submission

- **Requesting:** reuses Phase 2's Notification Service and channel infrastructure (§24 of Phase 2 spec) exactly — a document request is functionally another templated tenant-facing message (§11 of Phase 2 spec's template-management pattern), just with a different template category (`renewal_document_request` vs. `renewal_reminder`). No new outbound-messaging mechanism should be built.
- **Receiving:** this is the phase's largest genuinely new integration surface. The supplied tree shows `input_channels/whatsapp_server.py` and `input_channels/email_server.py` as the existing inbound paths; whether either currently supports **file/attachment** ingestion (as opposed to plain text) is unconfirmed — `VERIFY AGAINST SOURCE`. If neither channel currently handles inbound file attachments, **inbound file receipt is a NEW COMPONENT** and is the single largest technical dependency of this phase, on par with Phase 3's manager-identity gap. This must be confirmed before implementation sequencing (§35) proceeds past checklist-building.
- Once a file is received, it must be correlated to the correct checklist item — via whatever conversational/reminder correlation Phase 2 (§19 of Phase 2 spec) and Phase 3 already established for matching an inbound message to an open cycle, extended here to also resolve *which document type* the submission is for (either via explicit tenant selection in the request flow, or via a simple "next pending item" default if only one item is outstanding, with ambiguity handled conservatively — flagged to a human/`UNDER_REVIEW` rather than guessed, if multiple items are simultaneously outstanding and the submission's target is unclear).

---

## 11. Validation Boundary

This is the central architectural rule of Phase 4, mirroring Phase 3's "LLM classifies, deterministic logic decides" boundary:

- The system MAY perform **mechanical/structural checks** on a submission — e.g., correct file type present, file not empty/corrupted, expected document category roughly matches what was requested (if inferable, e.g. via filename or a lightweight classification step) — moving status from `RECEIVED` to `UNDER_REVIEW` automatically once these checks pass.
- The system MUST NOT autonomously decide a document is legally/factually correct, complete, or acceptable. Moving a document from `UNDER_REVIEW` to `APPROVED` or `REJECTED` is exclusively a **human reviewer action** — this mirrors Phase 3 §4/§21's rule that final decisions stay with a human, applied here to document content instead of renewal intent.
- If any lightweight LLM-assisted check is used at the `RECEIVED → UNDER_REVIEW` mechanical-check step (e.g., "does this look like an ID document vs. an unrelated photo"), its output is advisory metadata only (e.g. a confidence flag surfaced to the reviewer) — it must never itself set `APPROVED`/`REJECTED`, consistent with the workflow-wide rule that the LLM interprets, deterministic code and humans decide.
- This boundary should reuse whatever human-in-the-loop mechanism `maintenance/nodes/human_approval.py` already establishes in this codebase (Phase 3 §9/§21 already flagged this as the closest existing precedent) — `VERIFY AGAINST SOURCE` and mirror its approval-capture pattern here rather than inventing a second one.

---

## 12. Missing Document Detection

- **NEW COMPONENT:** a periodic sweep (reusing the same scheduler mechanism established in Phase 1 §15 and extended by Phase 2 §14, not a third independent scheduler) that scans checklist items in `REQUESTED` status whose `expires_at` deadline is approaching or has passed, and items that were never requested at all despite the checklist existing (a data-quality/process gap, logged as an error per §23).
- Detection is purely deterministic (date/status comparison against configuration, §13) — no LLM involvement, consistent with Phase 1's core rule applied here to document deadlines instead of lease deadlines.

---

## 13. Reminder Rules

- Mirrors Phase 2 §7 almost exactly, applied to documents instead of lease-renewal reminders: a configurable `document_reminder_policy` (**NEW COMPONENT**) defining `max_reminder_count` and `min_interval_between_reminders` **per outstanding document item**, plus a deadline (`expires_at`, from a configurable `document_response_window_days`) after which the item transitions to `EXPIRED` rather than continuing to remind indefinitely.
- Same anti-spam requirement as Phase 2: bounded count, minimum interval, stop-on-submission (receiving the document is itself a stop-condition for that item's reminder loop, same pattern as Phase 2 §19's stop-on-tenant-response), and a hard `EXPIRED` terminal state instead of infinite reminding.
- Reminders are scoped per-checklist-item, not per-checklist — a tenant who has submitted 3 of 4 documents should only be reminded about the 1 outstanding item, not re-asked for everything (deterministic, derived from item statuses, not a separate tracked concept).
- `EXPIRED` items should raise the same kind of hand-off signal Phase 2 raises for `MAX_REMINDERS_REACHED` (§23 of Phase 2 spec) — surfaced for Phase 5/human escalation (§26), not silently left stalled.

---

## 14. Signature Tracking

- Per §4/§5, Phase 4 tracks **whether** a signature has been captured for the Renewal Agreement item, as its own checklist item with its own status lifecycle (§8) — it does not implement signature capture technology itself.
- If the project already has, or plans to integrate, a specific e-signature mechanism, that integration's "signed" callback/webhook should be the trigger that moves the `Signature` checklist item to `RECEIVED`/`UNDER_REVIEW` — nothing in the supplied tree indicates such an integration exists, so this connection point is **NEW COMPONENT** (an integration seam, not a signing product) and should be designed as a clean boundary (a single "record signature event" entry point) so that whatever actual signing mechanism gets chosen later can plug in without re-architecting the checklist model.
- In the interim / absence of e-signature tooling, "signature received" may simply mean a signed document was uploaded like any other document submission (§10) and a human reviewer visually confirms the signature is present as part of the `UNDER_REVIEW → APPROVED` step (§11) — this is the pragmatic default given no existing tooling was found, not a permanent design assumption.

---

## 15. Storage Abstraction

- Nothing in the supplied repository tree indicates an existing file/blob storage mechanism (no S3/storage client, no upload directory convention visible) — **file storage is a NEW COMPONENT** for this project, not just for this phase.
- Recommended design: a thin storage abstraction (`document_storage.py` or similar) behind an interface (`store(file) → file_reference`, `retrieve(file_reference) → file`), so the actual backing store (local filesystem, cloud object storage, etc.) can be chosen/changed independently of the checklist/tracking logic — this keeps Phase 4's core logic testable without a real storage backend.
- The primary Postgres database (reused, per every prior phase's principle of not introducing a second datastore) stores only `file_reference` metadata (§9, §17), never raw file bytes in a table — this is a deliberate architectural constraint to avoid bloating the operational database, and should be confirmed as consistent with whatever `docs/deployement.md` already assumes about infrastructure — `VERIFY AGAINST SOURCE`.

---

## 16. Database Schema

Additive only, all **NEW COMPONENT** (no document-related tables exist anywhere in the supplied tree):

| Table | Purpose |
|---|---|
| `renewal_document_requirements` | §6 — configuration |
| `renewal_document_checklists` | §7 — one per renewal instance |
| `renewal_document_checklist_items` | §7, §8, §9 — one per required document |
| `document_reminder_policy` | §13 — configuration |
| `document_submissions` | §17 — one row per actual file submission (supports resubmission history, §22) |
| `document_review_actions` | §11, §21 — audit of every human review decision |

Migrations go in the same migrations location established/confirmed in Phase 1 (§8/§29 of Phase 1 spec).

---

## 17. File Metadata

`document_submissions` (per actual uploaded file, distinct from the checklist item's current-state summary in §9):

| Field | Notes |
|---|---|
| `id` | PK |
| `checklist_item_id` | FK |
| `file_reference` | pointer into the storage abstraction (§15), e.g. object key/path |
| `original_filename` | as submitted |
| `mime_type` | |
| `file_size_bytes` | |
| `submitted_via_channel` | `whatsapp` / `email` / etc., mirrors Phase 2's channel field convention |
| `submitted_at` | |
| `checksum` | for integrity verification / duplicate detection (§24) |

---

## 18. Security

- Least-privilege, consistent with every prior phase (Phase 1 §22, Phase 2 §28, Phase 3 §27): Phase 4 has read access to renewal/lease/tenant data and insert/update access scoped to its own new tables.
- File storage access credentials (§15) must be handled with the same care as any other secret in the project — `VERIFY AGAINST SOURCE` for how existing secrets (DB credentials, channel API keys) are currently managed (`.env`/`.env.example` pattern visible in the tree) and follow the same convention, not a new secrets mechanism.
- Uploaded files should be treated as untrusted input: virus/malware scanning before storage is a reasonable operational requirement if the business's risk tolerance requires it — flagged as a recommended **NEW COMPONENT** consideration, not assumed to exist, since nothing in the tree suggests any file-handling security tooling currently exists.

---

## 19. Access Control

- Only the assigned human reviewer (property manager, or whoever the project designates — likely the same manager identity resolved in Phase 3 §15, reused here rather than building a second reviewer-assignment mechanism) can transition a document from `UNDER_REVIEW` to `APPROVED`/`REJECTED` (§11) — enforced at the service layer, not just a UI convention.
- Tenants can only submit documents for their own lease's checklist items — correlation logic (§10) must not allow cross-tenant submission or visibility.
- `VERIFY AGAINST SOURCE` for whether the project has any existing role/permission model (nothing in the supplied tree suggests one beyond implied manager-vs-tenant distinction) before assuming a specific access-control implementation; if none exists, this is a **NEW COMPONENT** at least at the "manager-only review action" enforcement level, even if a full role system isn't built.

---

## 20. Privacy

- Documents like Tenant Identification are highly sensitive PII — storage (§15) and access (§19) controls must reflect this; identification documents should not be exposed in the manager notification payload pattern established in Phase 3 §16 (that payload intentionally excludes raw sensitive content, §28 of Phase 3 spec) — Phase 4's equivalent "reviewer needs to see the document" access should be a scoped, audited retrieval action (§21), not a broadcast/forward of the file.
- Rejection reasons (§9) and review notes should avoid unnecessarily restating sensitive document content in plain log text (§23) — reference the checklist item and status, not embedded PII, mirroring Phase 3 §28's summary-not-transcript principle.

---

## 21. Audit Trail

- `document_review_actions` (§16) is the authoritative, append-only record of every human review decision: who reviewed, when, what status was set, and any rejection reason — mirrors Phase 3 §26's audit-table pattern exactly.
- Every status transition on a `renewal_document_checklist_items` row should be logged (either via this table for review-specific actions, or a general status-history log for all transitions including automated ones like `REQUESTED`/`EXPIRED`) so the full lifecycle of "was this document ever actually requested, when, and what happened to it" is reconstructable — same auditability principle as every prior phase.

---

## 22. Document Versioning

- A tenant may resubmit after a `REJECTED` status (§8) — each submission is its own row in `document_submissions` (§17), linked to the same `checklist_item_id`, so history is preserved rather than overwritten.
- The checklist item's "current" state (§9) always reflects the most recent submission, but prior submissions remain queryable for audit — this directly supports the `REJECTED → REQUESTED → RECEIVED` re-entry flow (§8) without losing the record of what was originally wrong.
- No in-place file mutation — a "new version" is always a new `document_submissions` row with its own `file_reference`, never an overwrite of existing stored content.

---

## 23. Error Handling

- **Per-item isolation:** one checklist item's processing failure (bad file, storage error) must not block other items in the same checklist or other tenants' checklists — same principle as every prior phase (Phase 1 §19, Phase 2 §25, Phase 3 §22).
- **Storage failure on submission receipt:** if the storage abstraction (§15) fails to persist an incoming file, the submission should not be marked `RECEIVED` — it should be retried (bounded, mirroring Phase 2 §17's retry pattern) and, if ultimately unrecoverable, logged as a critical error requiring manual follow-up (the tenant should not be told "received" if the file didn't actually persist).
- **Ambiguous submission correlation** (§10 — can't tell which checklist item a file is for): defaults to `UNDER_REVIEW`-pending-human-clarification rather than guessing, consistent with Phase 3 §19's "bias toward asking, not guessing" principle.
- No error is silently swallowed; every failure has a log entry and is counted in whatever run-summary mechanism the periodic sweep (§12) produces, mirroring Phase 1 §21/§19.

---

## 24. Duplicate Handling

- Duplicate submissions for the same checklist item (tenant sends the same file twice, or resends after a network glitch) are detected via the `checksum` field (§17) — an exact-duplicate resubmission should not create a redundant `document_review_actions` review cycle; it can be recognized and acknowledged without re-triggering a full review, though it should still be logged (not silently discarded) for traceability.
- Duplicate *reminder* sends are prevented by the same DB-level uniqueness/idempotency pattern established in every prior phase (Phase 1 §17, Phase 2 §16, Phase 3 §23/§24) — applied here as a unique constraint on `(checklist_item_id, reminder_sequence_number)` or equivalent, ensuring the periodic sweep (§12) can never double-send a document reminder.
- Duplicate checklist creation for the same renewal (e.g. the approval trigger fires twice) must be prevented via a unique constraint on `renewal_document_checklists.lease_id` (or `renewal_id`, whichever the upstream trigger identifies by) so re-processing an approval event does not create two parallel checklists for the same renewal.

---

## 25. Integration with Phase 3

- Phase 4's entry trigger is, per the prerequisite note at the top of this document, whatever event/status represents "renewal approved/initiated" — downstream of Phase 3's `PENDING_MANAGER_REVIEW` status. Phase 4 does not re-derive tenant intent or re-notify about renewal intent; it assumes Phase 3's classification and manager-notification work is already complete and trustworthy by the time it begins.
- Phase 4 reuses identifiers already established by Phase 3 (and Phase 1/2 before it): `lease_id`, `tenant_id`, `property_id`, and the manager identity resolved in Phase 3 §15 (for reviewer assignment, §19) — no re-resolution of these from scratch.
- If Phase 3's `NEGOTIATE` intent (with `condition_text`, §20 of Phase 3 spec) is what a manager is ultimately approving, Phase 4's checklist-building step (§7) should be able to reflect any condition-driven document adjustments if the business requires it (e.g. an amended-terms addendum document) — this is flagged as a possible configuration extension point (§6), not built as a special case here, since the exact business rule for "conditional renewal → extra documents" is not specified in the available inputs.

---

## 26. Integration with Phase 5

- Phase 4 hands off to Phase 5 (Human Escalation, per the master workflow's phase list) under two conditions: (a) a checklist item reaches `EXPIRED` (§8, §13) with no resolution, or (b) a checklist stalls in a way the business considers actionable (e.g. repeated `REJECTED` cycles without eventual `APPROVED`) — both are raised as a structured hand-off signal, mirroring the `renewal_response_events`/hand-off-table pattern established in Phase 2 §23 and reused conceptually in Phase 3, rather than inventing a new hand-off shape.
- On full checklist completion (`COMPLETE`, §8), Phase 4 similarly emits a structured "renewal documents complete" signal — this is the natural end of Workflow #4's document-tracking responsibility; whatever process finalizes the lease (execution, filing, etc.) is out of scope for both Phase 4 and Phase 5 as described, and is flagged as an open question for the master SDD, consistent with how Phase 3 flagged the approval-capture gap.

---

## 27. LangGraph State

- Consistent with Phase 3's precedent (the first phase to meaningfully populate `rent_renewal/state.py`), Phase 4 extends the same state module with a document-tracking slice, rather than introducing a separate state file/module:

```
DocumentTrackingState:
  lease_id
  tenant_id
  property_id
  checklist_id
  checklist_items                  (list of item states: type, status, expires_at)
  pending_submission_correlation   (set when an inbound file's target item is ambiguous, §10/§23)
  reviewer_id                      (resolved manager/reviewer, reused from Phase 3 §15)
```

- As with Phase 1–3, deterministic logic (status transitions, reminder eligibility, checklist completion) runs outside LLM control; any LLM involvement (optional lightweight submission-type classification, §11) is narrowly scoped and advisory only, never state-setting on its own.

---

## 28. Nodes

Extending `rent_renewal/graph.py`/`nodes.py` alongside Phase 3's nodes (§9 of Phase 3 spec), following the same node-authoring convention already used in `maintenance/nodes/` and `faq/nodes/` — `VERIFY AGAINST SOURCE`:

| Node (proposed) | Responsibility | LLM involved? |
|---|---|---|
| `build_checklist_node` | Deterministically build §7's checklist from §6 configuration on the approval trigger | No |
| `request_documents_node` | Send document requests via Phase 2's Notification Service | No |
| `intake_submission_node` | Correlate an inbound file to a checklist item (§10) | Optional, advisory-only (§11) |
| `mechanical_check_node` | `RECEIVED → UNDER_REVIEW` structural checks (§11) | Optional, advisory-only |
| `human_review_handoff_node` | Present submission to reviewer, mirrors `maintenance/nodes/human_approval.py` pattern | No |
| `checklist_completion_node` | Detect `COMPLETE`, emit hand-off signal (§26) | No |

---

## 29. Services

- **Document Checklist Service** — owns checklist creation/state derivation (§7, §8). Mirrors the "Lease Expiry Tracking Service" (Phase 1 §27) and "Renewal Reminder Service" (Phase 2 §24-adjacent) architectural role: an orchestration layer with no direct DB access of its own, delegating to the repository (§30).
- **Document Reminder Service** — owns §12/§13, structurally mirrors Phase 2's reminder-sweep service, reusing the same scheduler hook.
- **Storage Service** — the abstraction from §15, isolated so it can be swapped/mocked independently.
- **Review Service** — owns the human-review-boundary enforcement (§11, §19): the only code path permitted to write `APPROVED`/`REJECTED`.

---

## 30. Repository Layer

- **NEW COMPONENT:** `rent_renewal/document_tracking/repository.py` — all persistence for the six tables in §16, following the same access pattern already established in `database/rent_models.py` (SQLAlchemy / raw SQL / other — `VERIFY AGAINST SOURCE`, match existing convention rather than introducing a second ORM style, exactly as required in Phase 1 §28).
- No direct SQL scattered across the services in §29 — everything routes through this repository, consistent with every prior phase's separation of concerns.

---

## 31. Tests

- **Unit tests:** checklist-building from configuration (correct items for a given requirement set); status-transition validity (e.g. `RECEIVED → UNDER_REVIEW` allowed, `PENDING → APPROVED` not allowed without passing through intermediate states); reminder eligibility logic (interval/count bounds); `EXPIRED` transition timing.
- **Integration tests:** full flow from approval trigger → checklist created → documents requested → submission received → mechanical check → human review → `APPROVED` → checklist `COMPLETE` → hand-off signal emitted; duplicate submission via checksum recognized without duplicate review cycle; duplicate checklist-creation prevented via unique constraint; storage failure handled without falsely marking `RECEIVED`; reminder sweep does not duplicate-send; `EXPIRED` item correctly raises Phase 5 hand-off signal.
- Placed under `langgraph_agent/tests/` alongside the Phase 1–3 tests, consistent with the "don't add a fourth scattered test location" principle established in Phase 1 §29/§31.

## 32. Edge Cases

- Tenant submits a document before it was ever formally `REQUESTED` (e.g. proactively uploads their ID) — should still be correlated and accepted if a matching checklist item exists in `PENDING`, transitioning it directly toward `RECEIVED` rather than requiring the request step to have fired first; this must not be treated as an error.
- Checklist has zero mandatory items outstanding at creation time (e.g. a renewal type that needs no new documents) — checklist should be immediately derivable as `COMPLETE`, not stuck waiting for a request that will never be sent.
- Tenant submits a document for a lease that has since become inactive (edge case mirroring Phase 2 §7 stop-condition 4) — checklist processing for that item should halt and flag for manual review rather than proceeding as if the renewal were still live.
- A reviewer rejects a document, tenant resubmits, but the resubmission arrives after the item's `expires_at` deadline already passed and it auto-transitioned to `EXPIRED` — the late submission should still be captured (not discarded) but flagged as a late-arrival exception for manual reconciliation with whatever Phase 5 escalation already fired, rather than silently reopening the item as if nothing happened.
- Two different checklist items (e.g. "Tenant Identification" and "Renewal Agreement") both outstanding, and a single inbound submission is ambiguous about which it satisfies (§10, §23) — must not silently guess; routed to `UNDER_REVIEW`/manual correlation.

---

## 33. Acceptance Criteria (Given/When/Then)

```
Scenario: Checklist is built deterministically on renewal approval
  Given a renewal-approved trigger for a lease
   And a configured requirement set of [Renewal Agreement, Tenant Identification, Required Disclosure, Signature]
  When the checklist-building step runs
  Then a renewal_document_checklists row is created
   And exactly four renewal_document_checklist_items rows are created, one per configured requirement, each PENDING

Scenario: Document request and submission
  Given a checklist item in PENDING status
  When the request step runs
  Then the item transitions to REQUESTED
   And a tenant-facing message is sent via the existing Notification Service
  When the tenant submits a matching file
  Then the item transitions to RECEIVED
   And a document_submissions row is created with correct file metadata

Scenario: Human review boundary is enforced
  Given a checklist item in UNDER_REVIEW status
  When no human reviewer action has occurred
  Then the item's status remains UNDER_REVIEW
   And no automated process transitions it to APPROVED or REJECTED

Scenario: Missing document triggers bounded reminders then expiry
  Given a checklist item in REQUESTED status with no submission
   And min_interval_between_reminders and max_reminder_count configured
  When the periodic sweep runs repeatedly without a tenant submission
  Then reminders are sent up to max_reminder_count, respecting the minimum interval
   And after max_reminder_count is reached (or the deadline passes, whichever the configuration defines) the item transitions to EXPIRED
   And a hand-off signal for Phase 5 is created

Scenario: Checklist completion hand-off
  Given all mandatory checklist items for a renewal reach APPROVED
  When the checklist-completion check runs
  Then the checklist's derived status is COMPLETE
   And a structured hand-off signal is emitted for the next step

Scenario: Duplicate submission does not trigger duplicate review
  Given a checklist item already has a RECEIVED submission
  When the tenant sends the exact same file again (matching checksum)
  Then no duplicate document_review_actions cycle is triggered
   And the duplicate is logged for traceability
```

---

## 34. Definition of Done

- [ ] All `VERIFY AGAINST SOURCE` items resolved, especially: whether `input_channels/*` support inbound file attachments (the largest technical gap identified), existing DB/ORM conventions, existing secrets management pattern, and the `human_approval.py` review-capture mechanism to mirror.
- [ ] File storage abstraction (§15) implemented and confirmed to store only metadata/references in Postgres, not raw bytes.
- [ ] Document requirements are configurable without a code change (§6).
- [ ] Checklist creation is idempotent per renewal (unique constraint verified, §24).
- [ ] Status lifecycle (§8) implemented as a deterministic transition table; `APPROVED`/`REJECTED` are reachable only via the human-review code path (§11, §19), verified by test.
- [ ] Reminder cadence for missing documents is configurable, bounded, and stops on submission (§13), mirroring Phase 2's anti-spam guarantee.
- [ ] `EXPIRED` items correctly raise a Phase 5 hand-off signal; `COMPLETE` checklists correctly raise their own hand-off signal (§26).
- [ ] Full audit trail (`document_review_actions`, submission history) is append-only and queryable (§21, §22).
- [ ] Privacy/security review completed for sensitive document types (Tenant Identification) per §18/§20.
- [ ] All tests in §31 pass, including the edge cases in §32.
- [ ] `docs/architecture.md` updated (or flagged for the team) to reflect Phase 4's new tables/nodes, the file-storage dependency, and the still-open "where is approval actually captured" question carried from Phase 3.

---

## 35. Implementation Sequence

1. Confirm/resolve the two prerequisite gaps: (a) where exactly the "renewal approved/initiated" trigger comes from (Phase 3 open dependency), and (b) whether `input_channels/*` support inbound file attachments today (§10) — both block meaningful implementation if unresolved.
2. Confirm remaining `VERIFY AGAINST SOURCE` items (DB/ORM conventions, secrets pattern, `human_approval.py` mechanics).
3. Choose and implement the storage abstraction (§15) — smallest possible interface, testable in isolation.
4. Write additive migrations for the six tables in §16.
5. Implement the Document Checklist Service (§7, §29) and unit-test checklist-building against configuration.
6. Implement document request flow, reusing Phase 2's Notification Service and template pattern (§10).
7. Implement submission intake + correlation + mechanical checks (§10, §11), with the human-review boundary enforced from day one (no shortcut path to `APPROVED`/`REJECTED`).
8. Implement the Document Reminder Service (§12, §13), reusing Phase 1/2's scheduler mechanism.
9. Implement duplicate handling (§24) and versioning (§22).
10. Wire the LangGraph nodes (§28) into `rent_renewal/graph.py`/`nodes.py`/`state.py`, alongside Phase 3's nodes.
11. Implement audit trail (§21) and confirm privacy/security controls (§18–§20).
12. Run full test suite (§31–§32), confirm Definition of Done (§34), and document the checklist-completion hand-off contract for whatever process finalizes the lease, alongside the Phase 3→4 approval-capture question, for the project owner's attention.