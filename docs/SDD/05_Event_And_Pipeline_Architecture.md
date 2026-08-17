# 05 — Event and Pipeline Architecture

## 1. Document Purpose

This document defines the event-driven and pipeline architecture for the Rent Reminder Workflow backend.

The purpose is to establish how external triggers, internal events, scheduled executions, workflow processing, database state, and external providers interact.

This document focuses on:

- Event sources.
- Event ingestion.
- Event normalization.
- Event validation.
- Event routing.
- Pipeline stages.
- Workflow triggering.
- Event persistence.
- Idempotency.
- Retry behavior.
- Failure handling.
- Dead-letter handling.
- Event ordering.
- Concurrency.
- Observability.
- Integration with the Workflow Runner.

Related documents:

- `00_SDD_Master.md`
- `01_Current_System_Architecture.md`
- `02_Target_Backend_Architecture.md`
- `03_Database_Wiring.md`
- `04_API_And_Service_Layer.md`
- `06_WorkflowRunner_Architecture.md`
- `07_LangGraph_Integration.md`
- `08_Integration_And_Provider_Layer.md`
- `09_Background_Jobs_And_Scheduling.md`
- `10_Security_And_Error_Handling.md`
- `11_Observability_And_Logging.md`
- `12_Backend_Testing_Strategy.md`

---

# 2. Architectural Goal

The target event architecture should allow different input channels to enter the same internal processing pipeline.

```text
WhatsApp
Email
Web
API
Scheduler
Webhook
Internal Event
     │
     ▼
Event Ingestion
     │
     ▼
Event Normalization
     │
     ▼
Event Validation
     │
     ▼
Idempotency / Deduplication
     │
     ▼
Event Routing
     │
     ▼
Application Service
     │
     ▼
Workflow Runner
     │
     ▼
Business Logic
     │
     ├──────────────► Database
     │
     └──────────────► Provider Layer

The key architectural principle is:

Different input channels may have different external interfaces, but they should converge into a common internal event model and processing pipeline.

3. Event Architecture Principles

The architecture should follow these principles:

Every external trigger should be normalized before business processing.
Business logic should not depend directly on a specific input channel.
Events should carry enough metadata for tracing and idempotency.
Event processing should be safe to retry.
Duplicate events must not create duplicate business actions.
Database state remains authoritative for business state.
External providers should remain behind provider abstractions.
Long-running processing should be handled asynchronously.
Failed events should be observable and recoverable.
Event contracts should be versioned where necessary.
Event processing should be deterministic.
Critical business operations should have business-level idempotency.
4. Event Sources

Potential event sources include:

Source	Example Event	Processing
API	workflow.run.requested	Immediate / Async
Scheduler	rent.reminder.check.requested	Background
WhatsApp	tenant.message.received	Async
Email	tenant.email.received	Async
Web	tenant.request.created	Immediate / Async
Payment Provider	payment.received	Async
Messaging Provider	message.delivery.updated	Async
Internal Workflow	workflow.step.completed	Internal
Manual Admin	workflow.hold.requested	Controlled

The actual event sources should be limited to the integrations required by the application.

5. Event Categories

Events should be categorized into logical groups.

5.1 Command Events

A command requests that the system perform an operation.

Examples:

rent.reminder.check.requested
workflow.run.requested
reminder.send.requested
payment.record.requested
5.2 Domain Events

A domain event describes something that has happened.

Examples:

payment.received
reminder.created
reminder.sent
workflow.completed
workflow.failed
5.3 Integration Events

Integration events represent external provider activity.

Examples:

provider.message.sent
provider.message.delivered
provider.message.failed
provider.webhook.received
6. Unified Event Pipeline
7. Event Ingestion Layer

The Event Ingestion Layer is responsible for receiving events from external and internal sources.

Responsibilities:

Receive event.
Capture source.
Capture timestamp.
Capture external event ID.
Preserve raw payload where appropriate.
Attach correlation metadata.
Pass event to normalization.

The ingestion layer should not contain business logic.

8. Channel-Specific Adapters

Each external channel should have an adapter responsible for converting channel-specific input into the internal event model.

Example:

WhatsApp Webhook
      ↓
WhatsApp Adapter
      ↓
Internal Event

Email Webhook
      ↓
Email Adapter
      ↓
Internal Event

API Request
      ↓
API Adapter
      ↓
Internal Event

Scheduler
      ↓
Scheduler Adapter
      ↓
Internal Event

This prevents the business layer from having to understand every external provider format.

9. Event Normalization

All incoming events should be converted into a common internal representation.

Example:

{
  "event_id": "unique-event-id",
  "event_type": "tenant.message.received",
  "event_version": "1",
  "source": "whatsapp",
  "occurred_at": "2026-08-15T12:00:00Z",
  "received_at": "2026-08-15T12:00:02Z",
  "correlation_id": "correlation-id",
  "causation_id": null,
  "tenant_id": "tenant-id",
  "property_id": "property-id",
  "lease_id": "lease-id",
  "payload": {},
  "metadata": {}
}

The exact schema should be implemented according to project requirements.

10. Event Envelope

The event envelope should provide common metadata independent of event type.

Recommended fields:

Field	Purpose
event_id	Unique event identifier
event_type	Event category/type
event_version	Contract version
source	Origin of event
occurred_at	Original event timestamp
received_at	System ingestion timestamp
correlation_id	Trace across operations
causation_id	Event that caused this event
tenant_id	Tenant reference where applicable
property_id	Property reference where applicable
lease_id	Lease reference where applicable
payload	Event-specific data
metadata	Additional technical metadata

Not every event requires every business identifier.

11. Event Validation

Validation should happen before routing.

Validation should check:

Event structure.
Required fields.
Event type.
Event version.
Identifier format.
Timestamp format.
Payload schema.
Source authenticity where applicable.

Invalid events should not reach business logic.

Incoming Event
      ↓
Schema Validation
      ↓
Valid?
 ┌────┴────┐
YES       NO
 ↓         ↓
Route    Reject / Record Error
12. Event Deduplication

Event processing must be idempotent.

Duplicate events can occur because of:

Webhook retries.
Network failures.
Scheduler retries.
Worker restarts.
Queue redelivery.
Client retries.

The system should maintain a persistent mechanism to identify already-processed events.

Event
 ↓
Check event_id
 ↓
Already processed?
 ├── YES → Return / Ignore duplicate
 └── NO
      ↓
   Process
      ↓
   Record processed state
13. Event-Level and Business-Level Idempotency

Idempotency must exist at two levels.

Event-Level Idempotency

Prevents the same event from being processed multiple times.

event_id
   ↓
Event Processing Record
Business-Level Idempotency

Prevents duplicate business effects even when different events represent the same operation.

Example:

Reminder already sent
for Lease X + Billing Period Y
        ↓
Do not send another reminder

Both protections may be required.

14. Event Routing

After validation and deduplication, events should be routed according to event type.

Routing should remain deterministic and observable.

15. Rent Reminder Event Flow

The core rent reminder pipeline should be:

Scheduler
   ↓
rent.reminder.check.requested
   ↓
Event Ingestion
   ↓
Validation
   ↓
Idempotency
   ↓
Event Router
   ↓
Reminder Service
   ↓
Load Relevant Leases
   ↓
Evaluate Payment State
   ↓
Evaluate Reminder State
   ↓
Workflow Runner
   ↓
Reminder Decision
   ↓
Provider
   ↓
Persist Result
16. Payment Event Flow

When payment is received, the system should be able to stop or modify the reminder workflow.

17. Provider Webhook Flow

External providers may send asynchronous updates.

Example:

Provider
   ↓
Webhook
   ↓
Provider Adapter
   ↓
Normalized Event
   ↓
Validation
   ↓
Idempotency
   ↓
Event Router
   ↓
Application Service
   ↓
Database / Workflow

The provider payload should not be passed directly into business logic.

18. Event Persistence

Event persistence may be required for:

Auditability.
Debugging.
Replay.
Idempotency.
Failure recovery.
Observability.

A conceptual event record may contain:

event_id
event_type
event_version
source
occurred_at
received_at
correlation_id
causation_id
processing_status
attempt_count
processed_at
error_code
error_message

Raw payload storage should follow data-retention and privacy requirements.

19. Event Processing States

An event may move through:

RECEIVED
   ↓
VALIDATED
   ↓
QUEUED
   ↓
PROCESSING
   ↓
COMPLETED

Failure path:

PROCESSING
   ↓
FAILED
   ↓
RETRYING
   ↓
COMPLETED

Permanent failure:

FAILED
   ↓
MAX RETRIES
   ↓
DEAD_LETTERED

The exact state names may be adapted to the implementation.

20. Retry Strategy

Retryable failures should be retried automatically where safe.

Potential retryable failures:

Temporary database outage.
Network timeout.
Provider temporary failure.
Queue infrastructure failure.
Rate limiting.

Non-retryable failures may include:

Invalid event schema.
Missing required business data.
Unauthorized request.
Unsupported event type.
Permanent validation failure.

Conceptual backoff:

Attempt 1
   ↓
Short Delay
   ↓
Attempt 2
   ↓
Longer Delay
   ↓
Attempt 3
   ↓
Longer Delay
   ↓
Dead Letter

Retry counts and delays should be configurable.

21. Dead Letter Handling

Events that cannot be successfully processed after allowed retries should enter a dead-letter mechanism.

Failed Event
     ↓
Retry Limit Reached
     ↓
Dead Letter Queue / Store
     ↓
Alert
     ↓
Manual Investigation
     ↓
Replay / Resolve / Discard

Dead-lettered events should retain enough metadata for investigation.

22. Event Ordering

Not every event requires strict global ordering.

Ordering should be defined only where business correctness requires it.

Example:

payment.received

should not be processed after a reminder action if doing so would incorrectly send a reminder.

Ordering may therefore be required per:

Tenant.
Lease.
Workflow.
Payment account.

The architecture should avoid attempting to guarantee unnecessary global ordering.

23. Concurrency Control

Concurrent events may target the same lease.

Example:

Worker A → Reminder Check
Worker B → Payment Update

The system must protect critical state transitions.

Possible mechanisms:

Database transactions.
Row-level locking.
Optimistic concurrency.
Unique constraints.
Idempotency keys.
Workflow execution locks.

The exact mechanism is defined in the database and workflow architecture.

24. Pipeline Boundaries

The pipeline should have explicit boundaries:

1. Ingestion
2. Normalization
3. Validation
4. Idempotency
5. Routing
6. Application Service
7. Workflow Execution
8. Persistence
9. Provider Communication
10. Result Processing
11. Observability

Each boundary should have a clear responsibility.

25. Synchronous vs Asynchronous Processing

Not every event requires asynchronous execution.

Synchronous

Suitable for:

Simple API validation.
Read-only operations.
Lightweight state checks.
Asynchronous

Suitable for:

Reminder delivery.
Provider communication.
Long-running workflows.
Batch rent checks.
External webhook processing.
Retryable operations.

The target architecture should avoid blocking API requests for long-running work.

26. Event Queue / Broker

If event volume or reliability requirements justify it, a queue or message broker may be used.

Conceptually:

Producer
   ↓
Event Queue
   ↓
Worker
   ↓
Application Service

The choice of technology should be based on:

Expected volume.
Delivery guarantees.
Operational complexity.
Retry requirements.
Existing infrastructure.

A message broker should not be introduced solely for architectural appearance if simpler mechanisms satisfy current requirements.

27. Pipeline and Workflow Runner

The event pipeline should trigger the Workflow Runner rather than implementing workflow logic itself.

Preferred separation:

Event Pipeline
      ↓
Identify What Happened
      ↓
Route Event
      ↓
Workflow Runner
      ↓
Determine What To Do

The pipeline answers:

Where should this event go?

The workflow answers:

What should the system do?

28. Pipeline and LangGraph

If LangGraph is used, it should operate inside the workflow/application layer rather than becoming the event ingestion layer.

Preferred architecture:

Event
 ↓
Event Pipeline
 ↓
Application Service
 ↓
Workflow Runner
 ↓
LangGraph Workflow
 ↓
Business Decision

LangGraph should not be responsible for:

HTTP request handling.
Provider webhook parsing.
Raw database connection management.
Event queue infrastructure.

Detailed LangGraph architecture belongs in:

07_LangGraph_Integration.md

29. Pipeline and Database

The database remains the authoritative source for business state.

The event pipeline should not become a second source of truth.

Correct architecture:

Event
 ↓
Application Service
 ↓
Database State
 ↓
Business Decision

Event storage is for event processing, audit, and recovery; it should not replace core domain persistence.

30. Event Correlation

Every meaningful event-processing chain should have a correlation ID.

Example:

correlation_id = abc-123

The same correlation ID should appear in:

Incoming Event
   ↓
Application Service
   ↓
Workflow
   ↓
Database Logs
   ↓
Provider Call
   ↓
Provider Result

This enables end-to-end troubleshooting.

31. Causation Tracking

Where events generate additional events, a causation ID should identify the event that caused the new event.

Example:

payment.received
      ↓
workflow.re-evaluation.requested

The second event can contain:

causation_id = payment.received.event_id

This creates an event chain that can be reconstructed later.

32. Event Versioning

Event contracts should support versioning.

Example:

tenant.message.received.v1
tenant.message.received.v2

or:

{
  "event_type": "tenant.message.received",
  "event_version": "2"
}

Versioning is important when external integrations or multiple consumers depend on an event contract.

33. Security

Events may contain sensitive business or tenant information.

Security requirements include:

Authenticate external webhooks.
Validate webhook signatures where supported.
Do not trust external IDs without validation.
Avoid storing unnecessary sensitive payloads.
Encrypt sensitive data at rest where required.
Restrict event-store access.
Do not log secrets.
Do not expose raw provider payloads through public APIs.

Detailed security architecture belongs in:

10_Security_And_Error_Handling.md

34. Event Payload Privacy

Event payloads should contain only information required for processing.

Prefer:

{
  "tenant_id": "tenant-id",
  "lease_id": "lease-id",
  "event_type": "payment.received"
}

over duplicating large amounts of tenant or financial information into every event.

When additional information is required, retrieve authoritative state from the database.

35. Observability

Every event should be observable through:

Event ID.
Event type.
Source.
Correlation ID.
Processing status.
Attempt count.
Processing duration.
Error category.

Useful metrics include:

events_received_total
events_processed_total
events_failed_total
events_retried_total
events_dead_lettered_total
event_processing_duration
workflow_trigger_count
provider_failure_count

Detailed observability belongs in:

11_Observability_And_Logging.md

36. Event Pipeline Testing

Testing should cover:

Ingestion Tests
Valid event.
Invalid event.
Missing fields.
Invalid source.
Normalization Tests
WhatsApp payload conversion.
Email payload conversion.
API event conversion.
Scheduler event conversion.
Routing Tests
Correct event type.
Unknown event type.
Correct service invocation.
Idempotency Tests
Duplicate event.
Replayed event.
Concurrent duplicate processing.
Failure Tests
Database failure.
Provider failure.
Timeout.
Retry exhaustion.
Dead-letter behavior.
37. End-to-End Rent Reminder Example
38. Failure Scenarios
Scenario 1 — Invalid Event
Event
 ↓
Validation Failure
 ↓
Reject
 ↓
Record Failure
 ↓
Alert if required
Scenario 2 — Duplicate Event
Event
 ↓
Idempotency Check
 ↓
Already Processed
 ↓
Ignore / Return Existing Result
Scenario 3 — Database Failure
Event
 ↓
Service
 ↓
Database Failure
 ↓
Retry
 ↓
Success / Dead Letter
Scenario 4 — Provider Failure
Workflow
 ↓
Provider
 ↓
Temporary Failure
 ↓
Retry
 ↓
Success
Scenario 5 — Permanent Provider Failure
Workflow
 ↓
Provider
 ↓
Permanent Failure
 ↓
Record Failed State
 ↓
Alert / Human Intervention
39. Architecture Rules

The event pipeline must follow these rules:

External formats must be normalized.
Business logic must not depend on provider-specific payloads.
Events must have unique identifiers.
Event processing must be idempotent.
Critical business actions must also be idempotent.
Events must be traceable.
Retryable and non-retryable failures must be distinguished.
Failed events must be recoverable where appropriate.
The database remains authoritative for business state.
The pipeline should not contain complex business decisions.
Workflow decisions belong to the workflow/application layer.
Provider communication belongs to the provider layer.
Long-running processing should be asynchronous.
Event contracts should be versioned when necessary.
Sensitive payload data must be minimized.
Event handlers should be independently testable.
Duplicate processing must never create unintended duplicate business effects.
40. Current vs Target Pipeline
Area	Current State	Target State
Input channels	Verify repository	Multiple adapters
Event model	Verify repository	Unified event envelope
Normalization	Verify repository	Dedicated normalization
Validation	Verify repository	Schema validation
Idempotency	Verify repository	Persistent event/business idempotency
Routing	Verify repository	Deterministic event router
Workflow trigger	Verify repository	Workflow Runner
Retries	Verify repository	Configurable retry strategy
Dead letters	Verify repository	Recoverable failed-event store
Observability	Verify repository	Correlation + metrics
Event versioning	Verify repository	Versioned contracts
41. Implementation Phases
Phase 1 — Stabilization

Identify current triggers, integrations, and pipeline behavior.

Goals:

Identify every current input channel.
Identify existing event-like structures.
Identify webhook handlers.
Identify scheduler triggers.
Identify direct workflow invocations.
Identify duplicate processing risks.
Phase 2 — Database Unification

Ensure event-driven processing reads authoritative business state.

Phase 3 — Live Data Wiring

Connect normalized events to real application services.

Phase 4 — API Layer

Allow API requests to enter the same internal application architecture where appropriate.

Phase 5 — Scheduling and Alerting

Connect schedulers to the event pipeline and ensure safe repeated execution.

Phase 6 — Hardening

Add:

Strong idempotency.
Retry controls.
Dead-letter handling.
Concurrency protection.
Security.
Observability.
Replay mechanisms.
Testing.
42. Final Architecture
                  ┌─────────────────┐
                  │ WhatsApp        │
                  ├─────────────────┤
                  │ Email           │
                  ├─────────────────┤
                  │ Web             │
                  ├─────────────────┤
                  │ API             │
                  ├─────────────────┤
                  │ Scheduler       │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │ Event Ingestion │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │ Normalization   │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │ Validation      │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │ Idempotency     │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │ Event Router    │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │ App Service     │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │ Workflow Runner │
                  └───────┬─┬───────┘
                          ↓ ↓
                  ┌────────┐ ┌──────────────┐
                  │Database│ │Provider Layer│
                  └────────┘ └──────┬───────┘
                                    ↓
                              External Provider

The fundamental principle is:

All external triggers should converge into a controlled internal event pipeline, while business decisions remain inside application/workflow components and authoritative business state remains in the database.

43. Document Status

Document: 05_Event_And_Pipeline_Architecture.md

Architecture Type: Event and Pipeline Architecture

Primary Purpose: Define how triggers and events enter, move through, and exit the Rent Reminder Workflow backend.

Related Documents:

00_SDD_Master.md
01_Current_System_Architecture.md
02_Target_Backend_Architecture.md
03_Database_Wiring.md
04_API_And_Service_Layer.md
06_WorkflowRunner_Architecture.md
07_LangGraph_Integration.md
08_Integration_And_Provider_Layer.md
09_Background_Jobs_And_Scheduling.md
10_Security_And_Error_Handling.md
11_Observability_And_Logging.md
12_Backend_Testing_Strategy.md