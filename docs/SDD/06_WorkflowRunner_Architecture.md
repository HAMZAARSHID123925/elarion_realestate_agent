# 06 — Workflow Runner Architecture

## 1. Document Purpose

This document defines the architecture of the Workflow Runner for the Rent Reminder Workflow backend.

The Workflow Runner is responsible for executing business workflows in a controlled, reliable, observable, and resumable manner.

It sits between the event/application layer and the actual workflow execution logic.

The Workflow Runner should provide a consistent execution framework for workflows such as:

- Rent Reminder Workflow
- Payment Follow-up Workflow
- Arrears Workflow
- Tenant Support Workflow
- Maintenance Workflow
- Notification Workflow
- Human Intervention Workflow

The Workflow Runner should not contain the business rules of every workflow.

Instead, it provides the infrastructure required to execute workflows safely.

---

# 2. Architectural Goal

The Workflow Runner should provide a standardized execution mechanism:

```text
Event
   ↓
Application Service
   ↓
Workflow Runner
   ↓
Load Workflow
   ↓
Create / Resume Execution
   ↓
Execute Workflow
   ↓
Persist State
   ↓
Execute Actions
   ↓
Update State
   ↓
Complete / Pause / Retry / Fail

The core principle is:

The Workflow Runner controls workflow execution, while individual workflows contain the business logic.

3. Workflow Runner Responsibilities

The Workflow Runner is responsible for:

Starting workflows.
Resuming workflows.
Identifying workflow type.
Loading workflow state.
Creating execution context.
Managing workflow status.
Persisting workflow state.
Handling retries.
Handling failures.
Supporting pause/resume.
Preventing duplicate execution.
Managing execution IDs.
Providing correlation IDs.
Enforcing execution boundaries.
Calling workflow implementations.
Recording execution results.
Supporting observability.

The Workflow Runner should not be responsible for:

Direct HTTP request handling.
Provider-specific webhook parsing.
Raw database queries scattered throughout workflow logic.
Sending provider messages directly.
Implementing every business rule itself.
4. Workflow Runner Position in Architecture

The Workflow Runner sits between the application/event layer and workflow implementations.

5. Workflow Runner vs Workflow

These two concepts must remain separate.

Workflow Runner

Responsible for:

How to execute?
When to execute?
What state exists?
What happens on failure?
Can it retry?
Can it resume?
Is it already running?
Workflow

Responsible for:

What business decision should be made?
What conditions should be evaluated?
What action should happen?
What should happen next?

Example:

Workflow Runner
      ↓
Rent Reminder Workflow
      ↓
Check rent status
      ↓
Check reminder history
      ↓
Determine reminder requirement
      ↓
Send reminder / Stop / Escalate
6. Workflow Definition

Every workflow should have a unique identifier.

Example:

rent_reminder
maintenance_request
tenant_support
arrears_followup
payment_followup

A workflow definition should conceptually contain:

workflow_id
workflow_name
workflow_version
entrypoint
state_schema
supported_events
configuration

Example:

{
  "workflow_id": "rent_reminder",
  "workflow_version": "1",
  "entrypoint": "RentReminderWorkflow",
  "supported_events": [
    "rent.reminder.check.requested",
    "payment.received"
  ]
}
7. Workflow Registry

The Workflow Registry maps workflow IDs to workflow implementations.

Conceptually:

Workflow ID
     ↓
Workflow Registry
     ↓
Workflow Implementation

Example:

rent_reminder
      ↓
RentReminderWorkflow

maintenance_request
      ↓
MaintenanceWorkflow

tenant_support
      ↓
TenantSupportWorkflow

The registry should prevent the application from importing and manually selecting workflow implementations throughout the codebase.

8. Workflow Execution

Every workflow execution should have a unique execution ID.

Example:

workflow_id:
rent_reminder

execution_id:
wf-exec-123456

The execution ID allows the system to track:

Current state.
Start time.
End time.
Status.
Retry count.
Errors.
Actions.
Correlation ID.
9. Workflow Execution Lifecycle

A workflow execution may follow:

CREATED
   ↓
QUEUED
   ↓
RUNNING
   ↓
WAITING
   ↓
RUNNING
   ↓
COMPLETED

Failure path:

RUNNING
   ↓
FAILED
   ↓
RETRYING
   ↓
RUNNING

Permanent failure:

FAILED
   ↓
MAX RETRIES
   ↓
FAILED_PERMANENTLY

Human intervention:

RUNNING
   ↓
WAITING_HUMAN
   ↓
RESUMED
   ↓
RUNNING
10. Workflow States

Recommended workflow execution states:

State	Meaning
CREATED	Execution record created
QUEUED	Waiting for worker
RUNNING	Currently executing
WAITING	Waiting for external event/time
WAITING_HUMAN	Human action required
RETRYING	Waiting for retry
COMPLETED	Successfully completed
FAILED	Execution failed
CANCELLED	Execution manually cancelled
FAILED_PERMANENTLY	No more retries

Exact state names may be adjusted during implementation.

11. Workflow Execution Context

Each execution should receive a controlled execution context.

Conceptual structure:

{
  "execution_id": "wf-exec-123",
  "workflow_id": "rent_reminder",
  "workflow_version": "1",
  "correlation_id": "corr-123",
  "tenant_id": "tenant-123",
  "property_id": "property-123",
  "lease_id": "lease-123",
  "trigger_event_id": "event-123",
  "state": {},
  "metadata": {}
}

The context should not contain unnecessary data.

Large or authoritative business data should be loaded from the database.

12. Workflow State

Workflow state represents the current execution state.

Example:

{
  "rent_due": true,
  "days_overdue": 5,
  "last_reminder_sent": "2026-08-10",
  "reminder_count": 2,
  "payment_received": false,
  "human_intervention_required": false
}

Workflow state should be:

Serializable.
Persistable.
Version-aware.
Recoverable.
Validated.
13. State Ownership

The Workflow Runner owns execution metadata.

The workflow owns workflow-specific state.

The database owns authoritative business state.

Therefore:

Workflow Runner
    ↓
Execution Metadata

Workflow
    ↓
Workflow State

Database
    ↓
Business State

Example:

Workflow State:
"reminder_count": 2

Database Business State:
"rent_payment_status": "unpaid"

The workflow must not treat temporary workflow state as the authoritative source for payment status.

14. Workflow Execution Flow
15. Starting a Workflow

A workflow may be started by:

API request.
Scheduler.
Event.
Internal service.
Another workflow.
Manual admin action.

Example:

rent.reminder.check.requested
        ↓
Application Service
        ↓
Workflow Runner
        ↓
start(
    workflow_id="rent_reminder"
)

The Workflow Runner should validate whether a new execution is allowed.

16. Workflow Resume

A workflow may need to stop and continue later.

Examples:

Waiting for payment.
Waiting for tenant response.
Waiting for provider callback.
Waiting for human approval.
Waiting for scheduled retry.

Resume flow:

Persist WAITING State
       ↓
External Event / Scheduler
       ↓
Find Execution
       ↓
Load State
       ↓
Resume Workflow
17. Workflow Pause

A workflow may intentionally pause.

Example:

Rent Reminder
      ↓
Tenant disputes rent
      ↓
WAITING_HUMAN
      ↓
Property Manager Reviews
      ↓
Resume Workflow

Pause must persist state before execution ends.

18. Workflow Cancellation

A workflow may be cancelled because:

Rent was paid.
Lease ended.
Property was removed.
Admin cancelled the workflow.
Business condition is no longer valid.

Cancellation should be explicit.

Example:

Active Workflow
      ↓
Payment Received
      ↓
Cancellation Condition
      ↓
CANCELLED / COMPLETED

The exact semantic should depend on whether the workflow successfully reached its business outcome or was explicitly terminated.

19. Workflow Idempotency

Starting the same workflow multiple times should not create duplicate business actions.

Example:

Scheduler Run #1
      ↓
rent_reminder / lease_123

Scheduler Run #2
      ↓
rent_reminder / lease_123

The Runner should detect whether an equivalent active execution already exists.

Possible idempotency key:

workflow_id + lease_id + billing_period

Example:

rent_reminder:
lease_123:
2026-08
20. Execution Locking

Concurrent workers must not execute the same workflow state simultaneously unless explicitly supported.

Example:

Worker A
   ↓
Workflow Execution 123

Worker B
   ↓
Workflow Execution 123

Only one worker should hold the execution lock at a time.

Possible mechanisms:

Database row locking.
Distributed locks.
Optimistic concurrency.
Execution version numbers.

The selected mechanism should align with the database architecture.

21. Workflow Versioning

Workflow implementations may change over time.

Example:

rent_reminder v1
rent_reminder v2

Existing executions should not unexpectedly switch to incompatible logic.

Recommended model:

Execution
    ↓
workflow_id = rent_reminder
workflow_version = 1

New executions may use:

workflow_version = 2

Existing executions should continue using a compatible version unless explicitly migrated.

22. Workflow Steps

A workflow may contain multiple logical steps.

Example:

1. Load Lease
       ↓
2. Check Payment
       ↓
3. Evaluate Reminder
       ↓
4. Determine Action
       ↓
5. Send Notification
       ↓
6. Persist Result
       ↓
7. Complete

Each step should have a clear responsibility.

23. Step Execution

The Runner should be able to identify the current step.

Example:

{
  "current_step": "check_payment",
  "completed_steps": [
    "load_lease"
  ]
}

This allows recovery after worker interruption.

24. Step Idempotency

Individual workflow steps should also be safe to retry.

Example:

send_reminder

If the worker crashes after the provider accepts the message but before the database update, retrying could send a duplicate reminder.

Therefore the action should use:

Idempotency key.
Provider idempotency mechanism where available.
Database uniqueness constraints.
Outbox/action state.
25. Workflow Action Model

Actions should be explicit.

Example:

SEND_REMINDER
RECORD_PAYMENT
CREATE_TICKET
REQUEST_HUMAN_REVIEW
SEND_ESCALATION
COMPLETE_WORKFLOW

An action may contain:

{
  "action_type": "SEND_REMINDER",
  "action_id": "action-123",
  "execution_id": "wf-exec-123",
  "idempotency_key": "lease-123-reminder-2026-08",
  "payload": {}
}
26. Action Execution

Preferred flow:

Workflow Decision
      ↓
Create Action
      ↓
Persist Action Intent
      ↓
Execute Provider / Service
      ↓
Persist Result

This is safer than:

Call Provider
      ↓
Hope Database Update Succeeds

The exact implementation should be coordinated with the provider and transaction architecture.

27. Rent Reminder Workflow

The Rent Reminder Workflow should conceptually work as follows:

28. Rent Reminder Business Rules

The exact business rules belong to the Rent Reminder Workflow implementation.

Example rules may include:

If rent is paid:
    Stop reminder workflow.

If rent is overdue:
    Evaluate reminder schedule.

If reminder interval has elapsed:
    Send reminder.

If maximum reminders reached:
    Escalate.

If human intervention required:
    Pause workflow.

If payment received:
    Stop or complete workflow.

The Workflow Runner should execute these rules but should not hard-code them into the generic runner.

29. Workflow Inputs

Workflow inputs may include:

Tenant ID.
Property ID.
Lease ID.
Trigger event ID.
Trigger source.
Billing period.
Workflow configuration.
Existing workflow state.

Example:

{
  "tenant_id": "tenant-123",
  "property_id": "property-123",
  "lease_id": "lease-123",
  "billing_period": "2026-08",
  "trigger_event_id": "event-123"
}
30. Workflow Outputs

A workflow execution should produce a structured result.

Example:

{
  "status": "WAITING",
  "execution_id": "wf-exec-123",
  "current_step": "next_reminder_check",
  "actions": [],
  "next_run_at": "2026-08-20T09:00:00Z"
}

Possible outcomes:

COMPLETED
WAITING
WAITING_HUMAN
RETRY
FAILED
CANCELLED
31. Error Handling

Errors should be classified.

Retryable

Examples:

Temporary database outage.
Provider timeout.
Temporary provider failure.
Network failure.
Non-Retryable

Examples:

Invalid workflow state.
Missing required entity.
Unsupported workflow version.
Invalid configuration.
Business Stop

Examples:

Payment received.
Lease terminated.
Tenant no longer active.

Business stop is not necessarily an error.

32. Workflow Retry

Retry metadata should include:

attempt_count
last_attempt_at
next_retry_at
error_code
error_message

Example:

Attempt 1
   ↓
Provider Timeout
   ↓
Retry in 30 seconds

Attempt 2
   ↓
Provider Timeout
   ↓
Retry in 2 minutes

Attempt 3
   ↓
Success

Retry policy should be configurable.

33. Workflow Timeout

Workflows should have execution time limits.

Examples:

Step Timeout
Workflow Timeout
Provider Timeout
Human Waiting Timeout

A workflow waiting for a human should not consume an active worker indefinitely.

Instead:

RUNNING
   ↓
Persist State
   ↓
WAITING_HUMAN
   ↓
Worker Released
34. Workflow Scheduling

The Runner may schedule future execution.

Example:

Reminder Sent
     ↓
Persist next_run_at
     ↓
Scheduler
     ↓
Resume Workflow

The Workflow Runner should not depend on an in-memory timer for long-term scheduling.

Persistent scheduling state should be stored.

35. Workflow and Background Jobs

Background jobs should trigger workflow execution rather than duplicate workflow logic.

Preferred:

Scheduler
   ↓
Job
   ↓
Event
   ↓
Workflow Runner
   ↓
Workflow

Avoid:

Scheduler
   ↓
Huge Business Logic Function

This keeps execution consistent across API, event, and scheduled triggers.

36. Workflow and Database

The Workflow Runner should use repository/service abstractions rather than directly scattering SQL throughout workflow implementations.

Preferred:

Workflow
   ↓
Application Service / Repository
   ↓
Database

This preserves separation of concerns.

37. Workflow Transactions

Transactions should be used where state consistency requires them.

Example:

Create Reminder Action
+
Update Workflow State

These related database operations may require a transaction.

However, external provider calls should generally not remain inside a long-running database transaction.

Preferred:

Transaction
   ↓
Persist Intent
   ↓
Commit
   ↓
External Provider
   ↓
Persist Result
38. Outbox Pattern

For critical external actions, an outbox mechanism may be used.

Conceptually:

Database Transaction
      ↓
Workflow State
+
Outbox Action
      ↓
Commit
      ↓
Worker
      ↓
Provider
      ↓
Result

This reduces the risk of losing an external action between database state changes and provider communication.

The exact use of an outbox should be determined by implementation requirements.

39. Human-in-the-Loop

Some workflows require human intervention.

Example:

Rent Reminder
      ↓
Tenant disputes charge
      ↓
Workflow pauses
      ↓
WAITING_HUMAN
      ↓
Property Manager
      ↓
Approve / Reject / Modify
      ↓
Workflow Resumes

The Runner should persist:

Reason for human intervention.
Current workflow state.
Required action.
Requested timestamp.
Human decision.
Decision timestamp.
40. Workflow Observability

Each execution should be traceable using:

Execution ID.
Workflow ID.
Workflow version.
Correlation ID.
Trigger event ID.
Tenant ID where applicable.
Lease ID where applicable.
Current step.
Attempt count.
Status.

Useful metrics:

workflow_started_total
workflow_completed_total
workflow_failed_total
workflow_retried_total
workflow_cancelled_total
workflow_waiting_total
workflow_human_intervention_total
workflow_execution_duration
workflow_step_duration
41. Workflow Logging

Logs should include:

workflow_id
execution_id
workflow_version
step
correlation_id
event_id
status
duration
error_code

Avoid logging:

API keys.
Passwords.
Provider secrets.
Unnecessary tenant-sensitive information.
42. Workflow Testing Strategy

Testing should cover:

Runner Tests
Start workflow.
Resume workflow.
Pause workflow.
Cancel workflow.
Duplicate start.
Concurrent execution.
Retry.
Failure.
Timeout.
Workflow Tests
Business rules.
State transitions.
Expected actions.
Payment conditions.
Reminder conditions.
Escalation.
Integration Tests
Database persistence.
Provider integration.
Scheduler integration.
Event pipeline integration.
43. Rent Reminder Example — Full Execution
Scheduler
    ↓
rent.reminder.check.requested
    ↓
Event Pipeline
    ↓
Application Service
    ↓
Workflow Runner
    ↓
Check Existing Execution
    ↓
Create / Resume Execution
    ↓
Load Lease
    ↓
Check Payment
    ↓
Rent Paid?
   ├── YES → Complete / Stop
   │
   └── NO
        ↓
     Calculate Overdue Days
        ↓
     Check Reminder History
        ↓
     Reminder Required?
       ├── NO → WAITING
       │
       └── YES
            ↓
        Create Action
            ↓
        Send Reminder
            ↓
        Save Result
            ↓
        Schedule Next Check
44. Failure Recovery Example

Suppose the provider succeeds but the worker crashes before updating the workflow.

The system should recover through idempotency.

Workflow
   ↓
Create Action ID
   ↓
Provider Call
   ↓
Provider Success
   ↓
Worker Crashes

On retry:

Load Action ID
      ↓
Check Existing Result
      ↓
Already Completed?
      ↓
YES
      ↓
Do Not Send Duplicate
      ↓
Update Workflow State

This is a critical reliability requirement.

45. Architecture Rules

The Workflow Runner must follow these rules:

The Runner manages execution, not business rules.
Every execution must have a unique execution ID.
Every execution must be traceable.
Workflow state must be persistable.
Workflows must support safe retries.
Critical actions must be idempotent.
Concurrent execution must be controlled.
Long-running workflows must not occupy workers unnecessarily.
Waiting states must be persistent.
Human intervention must be represented explicitly.
Workflow versions must be tracked.
Database state remains authoritative for business state.
Provider calls should remain behind the provider layer.
Workflow implementations should not depend directly on HTTP handlers.
Scheduler jobs should trigger workflows rather than duplicate business logic.
Errors must be classified as retryable, permanent, or business-stop conditions.
Workflow execution history should be observable.
Sensitive data must not be unnecessarily stored in workflow state.
46. Current vs Target Workflow Runner
Area	Current State	Target State
Workflow execution	Verify repository	Central Workflow Runner
Workflow registry	Verify repository	Dedicated registry
Execution state	Verify repository	Persistent execution state
Idempotency	Verify repository	Execution + action idempotency
Retry	Verify repository	Configurable retry policy
Resume	Verify repository	Persistent resume support
Pause	Verify repository	Explicit waiting states
Human intervention	Verify repository	WAITING_HUMAN
Versioning	Verify repository	Versioned workflows
Scheduling	Verify repository	Persistent next-run state
Observability	Verify repository	Execution-level tracing
Failure recovery	Verify repository	Retry + recovery mechanism
47. Implementation Phases
Phase 1 — Stabilization

Identify:

Existing workflow code.
Existing workflow triggers.
Existing state handling.
Existing scheduler logic.
Existing retry mechanisms.
Existing provider actions.

Do not rewrite working business logic unnecessarily.

Phase 2 — Database Unification

Ensure workflow execution state and business state have clear ownership.

Goals:

Centralize execution persistence.
Remove duplicate state sources.
Add required constraints.
Define workflow execution records.
Phase 3 — Live Data Wiring

Connect the Workflow Runner to:

Real repositories.
Real services.
Real provider abstractions.
Real event triggers.
Phase 4 — API Layer

Expose controlled workflow operations where required.

Examples:

POST /workflows/{workflow_id}/run
GET /workflow-executions/{execution_id}
POST /workflow-executions/{execution_id}/resume
POST /workflow-executions/{execution_id}/cancel

Exact routes should be finalized in:

04_API_And_Service_Layer.md

Phase 5 — Scheduling and Alerting

Add:

Persistent next-run scheduling.
Retry scheduling.
Workflow timeout monitoring.
Failure alerts.
Human intervention alerts.
Phase 6 — Hardening

Add:

Concurrency control.
Strong idempotency.
Workflow versioning.
Recovery mechanisms.
Outbox where necessary.
Comprehensive testing.
Security controls.
Observability.
48. Recommended Component Structure

Conceptually:

backend/
│
├── workflows/
│   ├── registry.py
│   ├── runner.py
│   ├── context.py
│   ├── state.py
│   ├── execution.py
│   │
│   ├── rent_reminder/
│   │   ├── workflow.py
│   │   ├── state.py
│   │   ├── steps.py
│   │   └── rules.py
│   │
│   ├── maintenance/
│   │   ├── workflow.py
│   │   ├── state.py
│   │   └── steps.py
│   │
│   └── tenant_support/
│       ├── workflow.py
│       ├── state.py
│       └── steps.py

The exact project folder structure should follow the existing repository architecture.

49. Final Workflow Runner Architecture
50. Final Architectural Principle

The Workflow Runner should act as the execution engine of the backend, not as the business logic itself.

The final responsibility boundary should be:

Event Pipeline
      ↓
"What triggered the workflow?"
      ↓
Application Service
      ↓
"Which workflow should run?"
      ↓
Workflow Runner
      ↓
"How should the workflow be executed safely?"
      ↓
Workflow
      ↓
"What business decision should be made?"
      ↓
Services / Repositories / Providers
      ↓
"How is the decision executed?"

The central principle is:

The Workflow Runner provides reliable execution infrastructure, while individual workflows own business behavior and the database remains the authoritative source of business state.

51. Document Status

Document: 06_WorkflowRunner_Architecture.md

Architecture Type: Workflow Execution Architecture

Primary Purpose: Define the architecture, lifecycle, state management, reliability, and execution model of backend workflows.

Related Documents:

00_SDD_Master.md
01_Current_System_Architecture.md
02_Target_Backend_Architecture.md
03_Database_Wiring.md
04_API_And_Service_Layer.md
05_Event_And_Pipeline_Architecture.md
07_LangGraph_Integration.md
08_Integration_And_Provider_Layer.md
09_Background_Jobs_And_Scheduling.md
10_Security_And_Error_Handling.md
11_Observability_And_Logging.md
12_Backend_Testing_Strategy.md

Status: Architecture Definition