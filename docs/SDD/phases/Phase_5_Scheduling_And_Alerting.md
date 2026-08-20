# Phase 5 — Scheduling and Alerting

## 1. Purpose

The purpose of Phase 5 is to introduce reliable background execution, scheduling, reminder processing, retry handling, and operational alerting for the Rent Reminder Workflow.

Phases 1–4 established the stabilized backend, unified database architecture, live data wiring, and API layer.

Phase 5 builds on those foundations to allow the Rent Reminder Workflow to execute automatically according to the approved business and scheduling rules.

The scheduling layer must trigger the existing workflow architecture rather than implementing a second version of the workflow.

---

# 2. Phase Objective

The primary objectives of this phase are:

1. Establish reliable background job execution.
2. Schedule Rent Reminder Workflow executions according to approved rules.
3. Identify records that require workflow processing.
4. Trigger the existing WorkflowRunner.
5. Prevent duplicate workflow executions.
6. Support retry behavior for recoverable failures.
7. Track job execution state.
8. Handle failed jobs safely.
9. Establish operational alerting for important failures.
10. Provide sufficient observability for scheduled executions.
11. Ensure scheduled processing works with live database state.
12. Prepare the system for production hardening in Phase 6.

---

# 3. Scope

## In Scope

Phase 5 covers:

* Background job execution
* Scheduling
* Rent reminder job
* Workflow triggering
* Job state
* Retry handling
* Failure handling
* Duplicate execution prevention
* Job execution tracking
* Operational alerts
* Scheduling observability
* Background-job testing
* Scheduler integration with existing services and WorkflowRunner

## Out of Scope

The following are not primary objectives of Phase 5:

* Database architecture redesign
* New API architecture
* Major workflow redesign
* New business rules
* Provider architecture redesign
* Production infrastructure redesign
* Full security hardening
* Disaster recovery architecture

These belong to previous architecture decisions or Phase 6.

---

# 4. Preconditions

Phase 5 must begin only after:

* Phase 1 stabilization is complete.
* Phase 2 database unification is complete.
* Phase 3 live data wiring is complete.
* Phase 4 API layer is complete.
* Workflow execution is stable.
* Live database data is available through the approved service/data-access architecture.
* WorkflowRunner can execute the Rent Reminder Workflow.
* Provider boundaries are established.

The scheduler must use these existing components rather than creating independent implementations.

---

# 5. Scheduling Architecture Principle

The scheduler is responsible for deciding **when** work should execute.

The WorkflowRunner is responsible for deciding **how the workflow executes**.

The service layer is responsible for business operations.

The database layer is responsible for persistence.

The provider layer is responsible for external integrations.

The logical architecture is:

```text id="7axw4s"
Scheduler
    ↓
Background Job
    ↓
Identify Eligible Records
    ↓
Service Layer
    ↓
WorkflowRunner
    ↓
Rent Reminder Workflow
    ↓
Provider / External Action
    ↓
Persist Result
```

The scheduler must not contain the actual rent reminder business logic.

---

# 6. Step 1 — Identify Scheduling Requirements

Before implementing the scheduler, identify the exact scheduling behavior required by the Rent Reminder Workflow.

### Determine

* When a rental record becomes eligible for processing.
* How frequently the workflow should evaluate eligible records.
* How reminder intervals are determined.
* What conditions make a record eligible.
* What conditions make a record ineligible.
* When processing should stop.
* When human intervention is required.
* What happens after successful payment.
* What happens after a failed reminder attempt.

The exact business rules must come from the approved workflow specification.

Do not invent new reminder policies during scheduling implementation.

---

# 7. Step 2 — Define Job Types

Background processing should use clearly defined job responsibilities.

The primary job for this workflow may conceptually be:

```text id="ebn5fb"
Rent Reminder Evaluation Job
```

Its responsibility is to:

1. Find records requiring evaluation.
2. Validate eligibility.
3. Trigger the appropriate workflow.
4. Record the execution result.
5. Continue processing other eligible records safely.

Additional jobs should only be introduced when a real requirement exists.

Avoid creating a separate background job for every small operation.

---

# 8. Step 3 — Define Scheduler Responsibilities

The scheduler should perform scheduling duties only.

### Scheduler Responsibilities

* Trigger jobs at configured times/intervals.
* Start background execution.
* Prevent unsupported concurrent execution where required.
* Report scheduler failures.
* Provide execution visibility.

### Scheduler Must Not

* Query business data directly when the architecture requires service access.
* Contain rent reminder rules.
* Send provider messages directly.
* Modify database records directly.
* Implement workflow state transitions.

The scheduler should invoke the appropriate job/service boundary.

---

# 9. Step 4 — Define Job Execution Flow

The background job should follow a predictable execution flow.

```text id="c5v7ax"
Scheduled Trigger
       ↓
Create Job Execution Context
       ↓
Find Eligible Records
       ↓
For Each Eligible Record
       ↓
Validate Current State
       ↓
Trigger WorkflowRunner
       ↓
Process Result
       ↓
Persist State
       ↓
Record Execution Outcome
```

A failure for one record should not automatically prevent processing of all unrelated eligible records unless the architecture explicitly requires fail-fast behavior.

---

# 10. Step 5 — Identify Eligible Records

The job must identify which records require processing using the unified database architecture.

Target flow:

```text id="bdt5gq"
Scheduled Job
      ↓
Service
      ↓
Data Access
      ↓
Eligible Records
```

### Eligibility Must Be Based On

Confirmed application state such as:

* Rent status
* Payment status
* Relevant dates
* Reminder state
* Workflow state
* Previous processing state

The exact eligibility conditions must match the approved business rules.

The scheduler must not independently recreate these rules.

---

# 11. Step 6 — Revalidate Before Processing

A record identified as eligible during initial discovery may change before its workflow is executed.

Therefore, the system should revalidate important state before performing the workflow action.

Conceptually:

```text id="p6g5a7"
Find Eligible Record
       ↓
Read Current State
       ↓
Still Eligible?
   ↙          ↘
 Yes          No
  ↓            ↓
Process      Skip
```

This reduces the risk of processing stale state.

---

# 12. Step 7 — Trigger WorkflowRunner

The background job must trigger the established WorkflowRunner.

Target architecture:

```text id="s5w1z8"
Background Job
      ↓
Workflow Service
      ↓
WorkflowRunner
      ↓
LangGraph / Workflow
```

The job must not call individual workflow nodes directly.

Workflow orchestration remains centralized in the WorkflowRunner architecture defined in:

`06_WorkflowRunner_Architecture.md`

---

# 13. Step 8 — Job Execution Identity

Each meaningful background execution should have enough context to identify what happened.

Where supported by the existing architecture, execution records/logs should provide information such as:

* Job type
* Execution identifier
* Record identifier
* Start time
* Completion time
* Outcome
* Failure reason
* Retry information

Identifiers must not expose sensitive information unnecessarily.

---

# 14. Step 9 — Prevent Duplicate Execution

Scheduled systems can accidentally execute the same work more than once.

Phase 5 must establish appropriate protection against duplicate processing.

### Potential Protection Mechanisms

Depending on the existing architecture:

* Persistent workflow state
* Execution identifiers
* State checks
* Unique constraints
* Job locks
* Scheduler-level concurrency controls
* Idempotent workflow operations

The implementation must use the mechanism appropriate to the actual infrastructure.

Do not introduce multiple overlapping locking mechanisms without a demonstrated need.

---

# 15. Step 10 — Idempotent Reminder Processing

A reminder operation must be safe against repeated execution.

Conceptually:

```text id="8h9j26"
Scheduled Execution
       ↓
Check Current State
       ↓
Already Processed?
   ↙          ↘
 Yes          No
  ↓            ↓
Skip         Execute
               ↓
          Persist Result
```

The exact idempotency strategy must follow the persistence and workflow architecture.

The goal is to prevent accidental duplicate reminders or incorrect state transitions.

---

# 16. Step 11 — Retry Strategy

Not every failure should be retried.

Failures should be classified before retrying.

### Potential Recoverable Failures

Examples:

* Temporary provider failure
* Temporary database connectivity failure
* Temporary network failure
* Transient infrastructure failure

### Potential Non-Recoverable Failures

Examples:

* Invalid data
* Missing required record
* Invalid configuration
* Permanent provider rejection
* Business-rule rejection

The retry strategy must distinguish between recoverable and non-recoverable failures.

---

# 17. Step 12 — Retry Policy

Where retries are appropriate, define:

* Maximum retry attempts
* Retry delay
* Backoff strategy
* Retryable error categories
* Non-retryable error categories
* Final failure behavior

Conceptually:

```text id="hcb0gk"
Job Failure
    ↓
Classify Error
    ↓
Retryable?
  ↙       ↘
Yes       No
 ↓         ↓
Retry    Final Failure
 ↓
Max Attempts?
 ↙       ↘
No       Yes
 ↓         ↓
Retry    Alert / Escalate
```

Exact retry values must be based on actual operational requirements.

They should not be invented merely to complete the design.

---

# 18. Step 13 — Backoff Strategy

Repeated failures should not cause aggressive repeated execution.

Where retries are implemented, an appropriate delay/backoff mechanism should be used.

Conceptually:

```text id="o7kwbq"
Attempt 1
   ↓
Delay
   ↓
Attempt 2
   ↓
Longer Delay
   ↓
Attempt 3
```

The exact backoff algorithm and limits must follow the selected scheduling/job infrastructure.

---

# 19. Step 14 — Failure Isolation

A failure affecting one record should be isolated from unrelated records where possible.

Example:

```text id="1uhf3r"
Job
 ├── Record A → Success
 ├── Record B → Temporary Failure → Retry
 ├── Record C → Success
 └── Record D → Invalid Data → Skip / Escalate
```

The job should not unnecessarily fail the entire batch because one independent record failed.

Where transactions or shared resources require batch-level failure, that behavior must be explicitly documented.

---

# 20. Step 15 — Persist Execution Results

Background processing should persist relevant state through the unified data-access architecture.

Possible persisted information may include:

* Workflow state
* Reminder state
* Processing timestamp
* Execution outcome
* Retry state
* Failure state

Only fields confirmed by the existing database architecture should be added or modified.

The scheduler itself must not directly perform database operations outside the established service/data-access boundary.

---

# 21. Step 16 — Alerting Requirements

Phase 5 introduces operational alerting for important background-processing failures.

Alerts should focus on conditions that require attention rather than every normal workflow event.

Potential alert conditions include:

* Repeated job failures
* Scheduler failure
* Persistent provider failure
* Database availability failure
* Retry exhaustion
* Workflow execution failure
* Unusual processing backlog
* Human-intervention condition where explicitly required

The exact alert conditions must follow operational requirements.

---

# 22. Step 17 — Alert Severity

Alerts should have meaningful severity levels.

Conceptually:

```text id="7x0rwl"
Informational
      ↓
Warning
      ↓
Critical
```

### Informational

Used for operational events that do not require immediate intervention.

### Warning

Used for conditions that may require investigation.

### Critical

Used for conditions that can prevent the workflow from operating correctly or require immediate human attention.

The exact severity model should remain consistent with the project's observability architecture.

---

# 23. Step 18 — Human Intervention

The Rent Reminder Workflow may eventually reach a state where automated processing should stop and human intervention is required.

The scheduler must not continuously retry such a state.

Conceptually:

```text id="aqy7ae"
Workflow
   ↓
Automated Processing
   ↓
Escalation Condition
   ↓
Human Intervention Required
   ↓
Stop Automatic Reminder Cycle
```

The exact escalation condition must come from the approved workflow business rules.

---

# 24. Step 19 — Scheduling Configuration

Scheduling configuration must be centralized.

Configuration may include:

* Job enable/disable state
* Schedule definition
* Retry configuration
* Maximum attempts
* Backoff settings
* Concurrency limits
* Alert thresholds

Configuration must not be hard-coded inside individual job implementations.

Environment-specific configuration should be handled through the approved configuration architecture.

---

# 25. Step 20 — Concurrency Control

The scheduler must prevent unsafe concurrent processing.

Potential concurrency problems include:

```text id="3f9d8g"
Scheduler A
    ↓
Record X
    ↓
Workflow Execution

Scheduler B
    ↓
Record X
    ↓
Workflow Execution
```

Both executions may attempt to process the same record.

The implementation should establish an appropriate concurrency strategy based on the actual execution infrastructure.

Potential mechanisms include:

* Job locks
* Database-level constraints
* State transitions
* Distributed locks
* Queue semantics
* Scheduler concurrency configuration

Only mechanisms supported by the actual architecture should be implemented.

---

# 26. Step 21 — Scheduling Time and Timezone Handling

Scheduling must use explicit timezone behavior.

### Requirements

* Define the authoritative timezone for scheduled business operations.
* Avoid implicit local-machine timezone assumptions.
* Store timestamps consistently according to the database architecture.
* Convert timestamps appropriately when presenting them to users or operators.
* Ensure daylight-saving behavior is considered where applicable.

The actual timezone must come from the application's confirmed business requirements.

Do not assume a timezone without project-level confirmation.

---

# 27. Step 22 — Missed Job Handling

The system should define what happens if a scheduled job does not execute.

Possible causes include:

* Application downtime
* Scheduler failure
* Deployment
* Infrastructure failure
* Temporary database outage

The system should determine whether the next execution:

```text id="5v4k7p"
Processes Only Current Eligibility
```

or:

```text id="5i9yjp"
Attempts to Recover Missed Work
```

The correct behavior depends on the business rules and scheduler capabilities.

It must be explicitly documented before implementation.

---

# 28. Step 23 — Job Observability

Background execution must integrate with:

`11_Observability_And_Logging.md`

Relevant telemetry should provide visibility into:

* Job started
* Job completed
* Job failed
* Number of eligible records
* Number processed
* Number skipped
* Number retried
* Number permanently failed
* Execution duration
* Scheduler failures

Metrics and logs should avoid exposing sensitive tenant/payment information.

---

# 29. Step 24 — Provider Integration Boundary

Reminder delivery must continue to use the provider architecture defined in:

`08_Integration_And_Provider_Layer.md`

Target flow:

```text id="f0lzz8"
Scheduler
    ↓
Background Job
    ↓
WorkflowRunner
    ↓
Workflow Decision
    ↓
Provider Layer
    ↓
External Channel
```

The scheduler must not directly call WhatsApp, email, SMS, or other providers.

The workflow/provider architecture remains responsible for external delivery.

---

# 30. Step 25 — Scheduling Tests

Phase 5 requires dedicated background-job and scheduling tests.

## Scheduler Tests

Verify:

* Job is triggered according to configuration.
* Disabled jobs do not execute.
* Invalid configuration fails safely.
* Scheduler failures are visible.

## Eligibility Tests

Verify:

* Eligible records are selected.
* Ineligible records are skipped.
* Current state is revalidated.

## Workflow Trigger Tests

Verify:

```text id="x8r3is"
Scheduler
   ↓
Job
   ↓
WorkflowRunner
```

works correctly.

## Retry Tests

Verify:

* Retryable failure retries.
* Non-retryable failure does not retry.
* Maximum attempts are respected.
* Final failure is recorded.

## Idempotency Tests

Verify repeated execution does not produce unintended duplicate state changes.

## Concurrency Tests

Verify simultaneous execution cannot incorrectly process the same work.

## Failure Isolation Tests

Verify one failed record does not incorrectly stop unrelated records.

## Alerting Tests

Verify critical operational conditions produce the expected alert behavior.

---

# 31. Step 26 — End-to-End Scheduling Validation

The complete automated flow must be validated.

```text id="0d6m83"
Scheduler
    ↓
Background Job
    ↓
Live Database
    ↓
Eligibility Check
    ↓
WorkflowRunner
    ↓
Rent Reminder Workflow
    ↓
Provider Layer
    ↓
Result
    ↓
Database State
    ↓
Observability / Alerting
```

This validation should use controlled test data and test providers where appropriate.

---

# 32. Phase 5 Deliverables

## Code

* Scheduler configuration
* Background job implementation
* Rent reminder processing job
* Eligibility evaluation through services
* WorkflowRunner integration
* Retry handling
* Failure isolation
* Duplicate execution protection
* Execution-state handling
* Operational alerting
* Scheduling observability
* Background-job tests

## Documentation

* Scheduling configuration
* Job responsibilities
* Retry policy
* Failure categories
* Concurrency strategy
* Timezone behavior
* Missed-job behavior
* Alert conditions
* Human-intervention behavior

## Validation

* Scheduled execution works.
* Eligible records are processed.
* Ineligible records are skipped.
* WorkflowRunner is triggered correctly.
* Duplicate processing is prevented.
* Retry behavior works as defined.
* Permanent failures are handled.
* Alerts are generated for required conditions.
* Job execution is observable.
* End-to-end scheduling tests pass.

---

# 33. Phase 5 Exit Criteria

Phase 5 is complete only when all applicable criteria are satisfied:

* [ ] Scheduler is configured through the approved configuration architecture.
* [ ] Background job execution is working.
* [ ] Rent Reminder Workflow can be triggered automatically.
* [ ] Eligibility is determined from live application state.
* [ ] Current state is revalidated before processing where required.
* [ ] Workflow execution uses the existing WorkflowRunner.
* [ ] Scheduler does not contain business logic.
* [ ] Database access remains inside the unified data-access architecture.
* [ ] Duplicate processing is prevented.
* [ ] Idempotent behavior is validated.
* [ ] Retryable and non-retryable failures are distinguished.
* [ ] Retry limits are enforced.
* [ ] Failed jobs are recorded and observable.
* [ ] Failure isolation works as intended.
* [ ] Required operational alerts are implemented.
* [ ] Human-intervention states are handled according to business rules.
* [ ] Timezone behavior is explicitly defined.
* [ ] Missed-job behavior is explicitly defined.
* [ ] Scheduling and background-job tests pass.
* [ ] End-to-end scheduling validation passes.
* [ ] Phase 6 prerequisites are satisfied.

---

# 34. Phase 5 Risks

| Risk                                   | Impact      | Mitigation                                                 |
| -------------------------------------- | ----------- | ---------------------------------------------------------- |
| Duplicate reminders                    | Critical    | Enforce idempotency and concurrency controls               |
| Scheduler runs stale data              | High        | Revalidate current state before processing                 |
| One failed record stops all processing | High        | Isolate independent record failures                        |
| Infinite retry loop                    | Critical    | Define retry limits and failure states                     |
| Temporary failure treated as permanent | Medium      | Classify errors before retrying                            |
| Permanent failure repeatedly retried   | High        | Maintain non-retryable error classification                |
| Scheduler contains business logic      | High        | Keep business rules inside services/workflow               |
| Provider called directly by scheduler  | High        | Use provider abstraction through workflow                  |
| Incorrect timezone behavior            | High        | Define explicit timezone policy                            |
| Missed jobs silently ignored           | Medium/High | Define and monitor missed-job behavior                     |
| Excessive operational alerts           | Medium      | Alert only on actionable conditions                        |
| Background jobs lack observability     | High        | Integrate logs and metrics with observability architecture |
| Concurrent workers process same record | Critical    | Implement appropriate concurrency protection               |

---

# 35. Dependencies on Other SDD Documents

Phase 5 must remain aligned with:

* `00_SDD_Master.md`
* `02_Target_Backend_Architecture.md`
* `03_Database_Wiring.md`
* `04_API_And_Service_Layer.md`
* `05_Event_And_Pipeline_Architecture.md`
* `06_WorkflowRunner_Architecture.md`
* `07_LangGraph_Integration.md`
* `08_Integration_And_Provider_Layer.md`
* `09_Background_Jobs_And_Scheduling.md`
* `10_Security_And_Error_Handling.md`
* `11_Observability_And_Logging.md`
* `12_Backend_Testing_Strategy.md`
* `phases/Phase_1_Stabilization.md`
* `phases/Phase_2_Database_Unification.md`
* `phases/Phase_3_Live_Data_Wiring.md`
* `phases/Phase_4_API_Layer.md`

Phase 5 must use the services, workflow, database, API, provider, observability, and scheduling architecture already established in the SDD.

It must not create an independent workflow execution path.

---

# 36. Transition to Phase 6

After Phase 5 has passed its exit criteria, implementation can proceed to:

**Phase 6 — Hardening**

Phase 6 will focus on production readiness, security hardening, reliability, resilience, performance validation, operational safeguards, and final system validation.

The objective is to make the complete backend reliable enough for controlled production operation.
