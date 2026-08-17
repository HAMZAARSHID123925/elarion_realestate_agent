# 03 — Database Wiring

## 1. Document Purpose

This document defines how the database is connected to the Rent Reminder Workflow backend, how application components access persistent data, and how the target architecture should maintain a reliable single source of truth.

This document focuses specifically on database wiring and persistence responsibilities.

It defines:

- Current database access.
- Target database access.
- Database source of truth.
- Core business entities.
- Repository/data-access boundaries.
- Service-to-database communication.
- Workflow state persistence.
- Reminder persistence.
- Payment state persistence.
- Transaction boundaries.
- Idempotency.
- Concurrency.
- Migration strategy.
- Database error handling.
- Database security.
- Database testing requirements.
- Database unification strategy.

This document should be read together with:

- `00_SDD_Master.md`
- `01_Current_System_Architecture.md`
- `02_Target_Backend_Architecture.md`
- `04_API_And_Service_Layer.md`
- `05_Event_And_Pipeline_Architecture.md`
- `06_WorkflowRunner_Architecture.md`
- `09_Background_Jobs_And_Scheduling.md`
- `12_Backend_Testing_Strategy.md`

---

# 2. Database Responsibilities

The database is the persistent source of truth for the business state required by the Rent Reminder Workflow.

The database is responsible for persisting information that must survive:

- Application restarts.
- Worker restarts.
- Workflow retries.
- Scheduler executions.
- API requests.
- Provider failures.
- Temporary infrastructure failures.

The database should contain authoritative business state rather than relying on temporary in-memory state.

## 2.1 Primary Responsibilities

The database is responsible for persistent state related to:

- Tenants.
- Properties.
- Leases.
- Rent/payment information.
- Reminder state.
- Workflow state.
- Reminder history.
- Workflow execution information where required.
- Provider delivery information where required.
- Manual intervention/hold state.
- Audit information where required.

## 2.2 What Should Not Be Treated as the Primary Source of Truth

The following should not independently maintain authoritative business state:

- In-memory Python objects.
- Temporary workflow state.
- Background worker memory.
- Scheduler memory.
- Provider response objects.
- API request state.
- Cached data.

Caching may be used for performance, but cached information must not replace the authoritative database state.

---

# 3. Current Database Architecture

The current database implementation must be treated as the source of truth for understanding the existing system.

The exact implementation should be verified against the repository before making implementation changes.

The current architecture should be documented according to the actual repository implementation, including:

| Area | Current State |
|---|---|
| Database technology | Verify from repository |
| Database connection | Verify from repository |
| ORM / data-access technology | Verify from repository |
| Database models | Verify from repository |
| Repository layer | Verify from repository |
| Direct database queries | Verify from repository |
| Database initialization | Verify from repository |
| Seed data | Verify from repository |
| Migration system | Verify from repository |
| Test database | Verify from repository |

### Current-State Rule

Documentation must never assume that a database component exists simply because the target architecture requires it.

If an implementation cannot be verified from the repository, it must be marked as:

> Not verified from repository.

---

# 4. Current Database Sources and Potential Duplication

A major architectural concern is the possibility of multiple sources containing overlapping business state.

Potential sources include:

- Primary application database.
- Workflow-specific database.
- Local SQLite database.
- Temporary/in-memory state.
- Mock database.
- Hardcoded development data.
- Separate provider state.
- Duplicate models.

The target architecture must eliminate conflicting sources of truth.

## 4.1 Database Source Analysis

| Source | Purpose | Authoritative? | Target Action |
|---|---|---:|---|
| Primary application database | Business data | Yes | Maintain |
| Workflow state | Workflow execution | Yes where persisted | Centralize |
| In-memory state | Temporary execution | No | Do not use as source of truth |
| Provider response | Delivery information | No | Persist relevant result |
| Mock/test database | Testing | No | Keep isolated to tests |

The exact sources must be validated against the repository.

---

# 5. Database Source of Truth

The target backend must maintain one authoritative source of truth for business state.

The following states must have a clear authoritative owner:

| Business State | Source of Truth |
|---|---|
| Tenant information | Database |
| Property information | Database |
| Lease information | Database |
| Payment status | Database |
| Reminder history | Database |
| Workflow state | Database |
| Manual hold | Database |
| Escalation state | Database |

External providers may provide information about communication delivery, but provider responses should not independently become the application's business source of truth.

---

# 6. Target Database Architecture

The target architecture separates business logic from database-specific implementation.

The preferred logical flow is:

```text
API / Scheduler / Event
        ↓
Application Service
        ↓
Domain / Workflow Logic
        ↓
Repository Interface
        ↓
Repository Implementation
        ↓
Database

This separation provides:

Clear ownership.
Easier testing.
Easier database replacement.
Reduced coupling.
Better transaction management.
Cleaner business logic.
6.1 Database Access Rule

Application and workflow code should not scatter raw database queries throughout the codebase.

Database-specific operations should be concentrated within the data-access/repository boundary.

7. Core Data Entities

The Rent Reminder Workflow logically depends on several business entities.

The exact implementation status of each entity must be verified against the repository.

7.1 Tenant

Represents the tenant receiving rent-related communication.

Potential responsibilities:

Tenant identity.
Contact information.
Lease association.
Communication preferences where applicable.
Tenant status.
7.2 Property

Represents a managed property.

Potential responsibilities:

Property identity.
Property information.
Ownership/management association where applicable.
Active/inactive state.
7.3 Lease

Represents the relationship between a tenant and a property.

Potential responsibilities:

Tenant association.
Property association.
Rent amount.
Rent frequency.
Lease start date.
Lease end date.
Rent due information.
Lease status.
7.4 Payment

Represents rent/payment state.

Potential responsibilities:

Lease association.
Payment period.
Amount.
Payment status.
Payment timestamp.
Payment reference where applicable.
7.5 Reminder

Represents an automated reminder action.

Potential responsibilities:

Lease association.
Workflow association.
Reminder type.
Attempt timestamp.
Delivery status.
Retry information.
Provider information.
7.6 Workflow

Represents the state of a rent reminder workflow.

Potential responsibilities:

Lease association.
Current state.
Workflow start time.
Last action.
Next action.
Completion state.
Failure state.
Escalation state.
7.7 Workflow Event / Execution

Represents workflow execution information where persistent tracking is required.

Potential responsibilities:

Workflow association.
Event type.
Execution timestamp.
Processing status.
Error information.
Idempotency information.
7.8 Provider Delivery

Represents the result of an external communication attempt.

Potential responsibilities:

Reminder association.
Provider.
External message/reference ID.
Delivery status.
Provider response.
Failure information.
7.9 Manual Hold

Represents an administrative pause on automatic workflow execution.

Potential responsibilities:

Lease/workflow association.
Hold state.
Reason.
Created timestamp.
Released timestamp.
Operator information where applicable.
8. Entity Relationship Model

The following represents the logical target relationship between the major business entities.

This diagram represents the target logical architecture and does not claim that every entity is already implemented.

9. Current vs Target Data Model
Entity / Concern	Current State	Target State	Required Action
Tenant	Existing implementation must be verified	Authoritative tenant record	Preserve/unify
Property	Existing implementation must be verified	Authoritative property record	Preserve/unify
Lease	Existing implementation must be verified	Central lease record	Preserve/unify
Payment	Existing implementation must be verified	Authoritative payment state	Centralize
Reminder	Existing implementation must be verified	Persistent reminder history	Add/unify if missing
Workflow	Existing implementation must be verified	Persistent workflow state	Add/unify if missing
Workflow Event	Existing implementation must be verified	Traceable execution history where required	Add if required
Provider Delivery	Existing implementation must be verified	Persist relevant delivery result	Add if required
Manual Hold	Existing implementation must be verified	Persistent workflow pause state	Add if required
10. Database Connection Architecture

The database connection should be managed through a centralized application-level mechanism.

The target architecture should avoid creating independent database connections throughout individual workflow nodes or services.

Conceptually:

Application Startup
        ↓
Database Configuration
        ↓
Database Engine / Connection Manager
        ↓
Session / Transaction
        ↓
Repository
10.1 Connection Responsibilities

The database infrastructure should manage:

Connection configuration.
Session lifecycle.
Transaction lifecycle.
Connection reuse/pooling where applicable.
Database error handling.
Environment-specific configuration.
10.2 Configuration

Database credentials and connection information must be provided through secure configuration mechanisms such as environment variables or a managed secrets system.

Credentials must never be hardcoded into source code.

11. Repository / Data Access Architecture

The repository layer provides the boundary between business logic and persistence.

Conceptually:

TenantService
      ↓
TenantRepository
      ↓
Database
LeaseService
      ↓
LeaseRepository
      ↓
Database
PaymentService
      ↓
PaymentRepository
      ↓
Database
ReminderService
      ↓
ReminderRepository
      ↓
Database
WorkflowService
      ↓
WorkflowRepository
      ↓
Database
11.1 Repository Responsibilities

Repositories should own:

Database queries.
Persistence operations.
Entity retrieval.
Entity updates.
Entity creation.
Database-specific query logic.
Transaction participation.

Repositories should not own:

Business decisions.
Communication provider logic.
Workflow orchestration.
API request handling.
12. Service → Database Wiring

The target flow should be:

API / Scheduler
      ↓
Application Service
      ↓
Business / Workflow Logic
      ↓
Repository
      ↓
Database

For the rent reminder workflow:

Rent Reminder Service
        ↓
Lease Repository
Payment Repository
Reminder Repository
Workflow Repository
        ↓
Database
12.1 Read Flow

Example:

Scheduler
    ↓
Rent Reminder Service
    ↓
Lease Repository
    ↓
Database
    ↓
Lease / Payment State
12.2 Write Flow

Example:

Reminder Service
    ↓
Reminder Repository
    ↓
Database
    ↓
Reminder Record
12.3 State Update Flow

Example:

Payment Confirmed
    ↓
Payment Service
    ↓
Payment Repository
    ↓
Database
    ↓
Workflow State Re-evaluated
13. Workflow State Persistence

Workflow state must be persistent.

The workflow must not rely solely on in-memory state because background workers, API processes, and application instances can restart.

The system should be able to determine:

Which tenant is being processed.
Which lease is being processed.
Which rent period is active.
Current workflow state.
Last reminder.
Last reminder timestamp.
Next required action.
Payment status.
Manual hold status.
Escalation status.
Completion status.
Failure status.
13.1 Example Workflow Lifecycle
PENDING
   ↓
DUE
   ↓
REMINDER_REQUIRED
   ↓
REMINDER_SENT
   ↓
WAITING_FOR_PAYMENT
   ↓
PAYMENT_RECEIVED
   ↓
COMPLETED

Alternative escalation path:

REMINDER_SENT
   ↓
PAYMENT_NOT_RECEIVED
   ↓
ESCALATION_REQUIRED
   ↓
HUMAN_INTERVENTION

The exact workflow states should be aligned with the implementation defined in the workflow SDDs.

14. Reminder Persistence

Every automated reminder action should be traceable.

The system should be able to answer:

Which tenant received the reminder?
Which lease generated it?
Which workflow generated it?
When was it attempted?
What type of reminder was it?
Which provider was used?
Was delivery successful?
Was it retried?
Did the provider return an external message ID?
Did an error occur?

Conceptual flow:

Workflow
    ↓
Reminder Created
    ↓
Provider Called
    ↓
Provider Result
    ↓
Reminder Delivery Updated

Persisting reminder history is important for:

Auditing.
Debugging.
Retry control.
Duplicate prevention.
Customer support.
Operational visibility.
15. Payment State

Payment state is one of the most important pieces of business state.

The reminder system must never continue sending automatic reminders after the applicable rent has been confirmed as paid.

Target flow:

Payment Confirmed
        ↓
Payment State Updated
        ↓
Workflow Re-evaluated
        ↓
Future Reminder Cancelled / Disabled
        ↓
Workflow Completed

The database payment state must be authoritative.

A temporary provider response, cached value, or in-memory flag must not override the authoritative payment state.

16. Manual Hold Persistence

Administrative intervention must be persistable.

Target behavior:

Manual Hold = ON
        ↓
Workflow Paused
        ↓
Automatic Reminder Disabled

When released:

Manual Hold = OFF
        ↓
Workflow Can Resume

A manual hold should survive:

Application restart.
Worker restart.
Scheduler restart.

The workflow runner should check the persisted hold state before performing automatic actions.

17. Transaction Boundaries

Transactions should protect operations where multiple database changes must remain consistent.

Examples include:

Payment Processing
Update Payment
+
Update Workflow State
=
Atomic Operation
Reminder Creation
Create Reminder
+
Update Workflow State
=
Atomic Operation
Escalation
Update Workflow State
+
Create Escalation / Event Record
=
Atomic Operation

Transactions should be kept as small as reasonably possible.

External provider calls should generally not remain inside long-running database transactions.

18. Idempotency and Database Constraints

Idempotency is critical because the system may receive:

Duplicate scheduler executions.
Duplicate events.
Worker retries.
Provider retries.
Duplicate webhook notifications.
Application restarts.

The same logical reminder must not be sent multiple times simply because a worker was retried.

18.1 Idempotency Strategy

The target system should use a combination of:

Persistent workflow state.
State checks.
Idempotency keys.
Unique constraints where appropriate.
Atomic database operations.
Provider reference IDs where available.

Conceptually:

Scheduler
   ↓
Check Workflow State
   ↓
Check Reminder Idempotency
   ↓
Create / Claim Reminder
   ↓
Send Provider Message
   ↓
Persist Result

The database should prevent multiple workers from successfully claiming the same logical action.

19. Database Concurrency

The system may eventually have multiple workers processing reminders concurrently.

Example:

Worker A ──┐
           ├── Same Lease
Worker B ──┘

Without concurrency protection:

Worker A → Send Reminder
Worker B → Send Reminder

This could produce duplicate communication.

The target architecture should use appropriate database-level protection such as:

Atomic state transitions.
Unique constraints.
Transaction isolation.
Row-level locking where appropriate.
Optimistic locking where appropriate.

The simplest reliable mechanism should be preferred.

20. Database Migrations

Database schema changes must be version-controlled.

The repository should use its established migration mechanism if one already exists.

Migration responsibilities include:

Creating new tables.
Altering existing tables.
Adding/removing fields.
Adding indexes.
Adding constraints.
Supporting controlled schema evolution.

Before production deployment:

Migration Created
      ↓
Migration Tested
      ↓
Migration Applied
      ↓
Application Validated

If the current repository does not contain a verified migration system, this should be addressed as part of the relevant implementation phase rather than silently assumed to exist.

21. Database Configuration

Database configuration must be environment-specific.

Typical configuration concerns include:

Database URL.
Credentials.
Host.
Port.
Database name.
Connection pool settings.
Development/test configuration.
Production configuration.

Sensitive configuration must be stored securely.

Never commit:

Passwords.
API keys.
Access tokens.
Private credentials.

Example configuration pattern:

Environment
    ↓
DATABASE_URL
    ↓
Database Configuration
    ↓
Application

Actual variable names must follow the repository's established configuration conventions.

22. Database Error Handling

Database errors should be classified before determining retry behavior.

22.1 Retryable Errors

Potentially retryable:

Temporary connection failure.
Network interruption.
Transient database unavailability.
Temporary concurrency conflict.
22.2 Non-Retryable Errors

Usually non-retryable without intervention:

Invalid schema.
Missing table.
Invalid query.
Data validation failure.
Permanent constraint violation.
Migration mismatch.
22.3 Error Flow
Database Error
      ↓
Classify Error
      ↓
Retryable?
   ↙       ↘
 YES       NO
 ↓          ↓
Retry      Fail Safely
 ↓          ↓
Backoff    Log / Alert

Database errors should not silently corrupt or advance workflow state.

23. Database Testing Strategy

Database testing should validate both persistence correctness and workflow correctness.

Required categories include:

23.1 Repository Tests

Validate:

Create.
Read.
Update.
Delete where applicable.
Query filtering.
State transitions.
23.2 Integration Tests

Validate:

Real database interaction.
Transaction behavior.
Repository integration.
Workflow persistence.
23.3 Constraint Tests

Validate:

Unique constraints.
Foreign-key relationships.
Required fields.
Idempotency constraints.
23.4 Workflow Persistence Tests

Validate:

Workflow State
      ↓
Database
      ↓
Application Restart
      ↓
Workflow State Recovered
23.5 Concurrency Tests

Where required, verify that two workers cannot successfully execute the same protected reminder action.

Detailed overall testing architecture belongs in:

12_Backend_Testing_Strategy.md

24. Database Security

The database layer must follow secure configuration and access principles.

Requirements include:

Credentials must not be hardcoded.
Secrets must not be committed.
Production connections should use secure transport where supported.
Database permissions should follow least privilege.
Sensitive data should be protected.
Logs should not expose sensitive database values.
Database access should be restricted to authorized application components.

Where tenant isolation is required, access controls must ensure that one tenant's data cannot be incorrectly exposed to another tenant or unauthorized user.

25. Target Database Wiring Diagram

The target database architecture is:

The important architectural principle is:

Business Logic
      ↓
Repository Boundary
      ↓
Authoritative Database
26. Database Unification Plan

This section aligns with:

phases/Phase_2_Database_Unification.md

The target transition is:

Current Database Sources
        ↓
Identify Authoritative Source
        ↓
Identify Duplicate State
        ↓
Consolidate Data
        ↓
Update Repository Layer
        ↓
Update Services
        ↓
Update Workflow Components
        ↓
Remove Duplicate State
        ↓
Validate Workflows
        ↓
Single Source of Truth
26.1 Unification Principles

Database unification must ensure:

No conflicting business state.
No duplicate authoritative records.
One clear persistence boundary.
Services use the unified data-access layer.
Workflow execution reads authoritative state.
Scheduler decisions use authoritative state.
Reminder history is persisted centrally.

The unification process should be performed incrementally and validated at every stage.

27. Database Wiring Rules

The following rules should govern the target implementation.

The database is the authoritative source of business state.
Services access persistent data through the repository/data-access layer.
Raw database queries should not be scattered throughout business logic.
Workflow state must be persistable.
Reminder actions must be traceable.
Payment state must remain authoritative.
Critical operations must be idempotent where required.
Transactions must protect critical state transitions.
Duplicate reminder execution must be prevented.
Database schema changes must be version-controlled.
Secrets must never be committed.
Database access must be testable.
Manual holds must survive application restarts.
Database failures must not silently advance workflow state.
External provider responses should be persisted when required for traceability.
Duplicate sources of truth must be eliminated.
28. Database Risks
Risk	Impact	Mitigation
Multiple sources of business state	Inconsistent workflow decisions	Establish one authoritative database
Missing workflow persistence	Workflow state lost after restart	Persist workflow state
Duplicate reminder execution	Tenant receives duplicate messages	Idempotency + database constraints
Concurrent workers	Duplicate processing	Atomic state transitions / locking
Direct database access from workflow nodes	Tight coupling	Repository boundary
Missing migrations	Schema inconsistency	Version-controlled migrations
Weak transaction boundaries	Partial state updates	Explicit transaction design
Provider/database mismatch	Incorrect reminder state	Persist and reconcile delivery results
In-memory workflow state	State lost on restart	Persist required state
Database connection failure	Workflow execution failure	Error classification and retry strategy
29. Open Questions / Unverified Areas

The following areas must be verified against the current repository before implementation:

Area	Question	Status
Database technology	Which database is currently authoritative?	Verify from repository
ORM	Which ORM/data-access library is currently used?	Verify from repository
Database duplication	Are multiple databases currently used?	Verify from repository
Repository layer	Does a repository abstraction already exist?	Verify from repository
Workflow persistence	Is workflow state currently persisted?	Verify from repository
Reminder history	Are reminder attempts currently persisted?	Verify from repository
Payment state	Where is payment state currently stored?	Verify from repository
Manual hold	Is manual hold currently persisted?	Verify from repository
Migration system	Is a migration framework currently configured?	Verify from repository
Concurrency	Is duplicate worker processing currently protected?	Verify from repository
Idempotency	Is reminder idempotency currently implemented?	Verify from repository

These items should be resolved during the corresponding implementation phases.

30. Relationship to Implementation Phases

This database architecture supports the following implementation phases:

Phase 1 — Stabilization

Establish the current database behavior and identify inconsistencies.

Phase 2 — Database Unification

Consolidate database sources and establish a single source of truth.

Phase 3 — Live Data Wiring

Connect the workflow and services to authoritative live database data.

Phase 4 — API Layer

Expose controlled database-backed functionality through the application service/API layer.

Phase 5 — Scheduling and Alerting

Allow scheduled workflows to safely query and update persistent state.

Phase 6 — Hardening

Strengthen:

Transactions.
Idempotency.
Concurrency.
Security.
Error handling.
Observability.
Testing.
31. Final Architecture Summary

The target database architecture can be summarized as:

                    ┌─────────────────────┐
                    │ API / Scheduler     │
                    │ / Events            │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Application         │
                    │ Services            │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Domain / Workflow   │
                    │ Logic               │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Repository /        │
                    │ Data Access Layer   │
                    └──────────┬──────────┘
                               │
                               ▼
                 ┌──────────────────────────┐
                 │ Authoritative Database   │
                 ├──────────────────────────┤
                 │ Tenant                   │
                 │ Property                 │
                 │ Lease                    │
                 │ Payment                  │
                 │ Reminder                 │
                 │ Workflow                 │
                 │ Delivery / Events        │
                 └──────────────────────────┘

The fundamental rule is:

The database owns persistent business state; services and workflows operate on that state through a controlled data-access boundary.

This architecture enables the Rent Reminder Workflow to survive retries, worker restarts, scheduler executions, and external provider failures while maintaining consistent business state.