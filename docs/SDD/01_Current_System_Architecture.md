# 01 — Current System Architecture

## 1. Document Purpose

This document describes the CURRENT architecture of the Rent Reminder Workflow backend.

The purpose of this document is to create an accurate snapshot of how the system currently works before further architectural changes are introduced.

This document focuses on the existing implementation and should not be treated as the target architecture.

The target architecture is documented separately in:

- `02_Target_Backend_Architecture.md`

Database-specific architecture is documented in:

- `03_Database_Wiring.md`

API and service architecture is documented in:

- `04_API_And_Service_Layer.md`

---

# 2. System Overview

The Rent Reminder Workflow is a backend automation system designed to identify rent-related conditions, determine whether a reminder action is required, execute the appropriate workflow, and communicate with external providers when necessary.

At a high level, the current system can be represented as:

```text
Input / Trigger
      ↓
Backend Processing
      ↓
Business / Workflow Logic
      ↓
Database / Data Source
      ↓
Reminder Decision
      ↓
Communication / External Provider

The exact implementation of each component must be verified against the current repository.

This document intentionally describes the system as it exists rather than describing the desired future state.

3. Architecture Documentation Principles

The following principles apply to this document:

CURRENT implementation must be distinguished from TARGET architecture.
Repository code is the primary source of truth.
Existing documentation is secondary to actual implementation.
Unverified components must not be presented as implemented.
Planned architecture must not be presented as current architecture.
Existing technical debt and inconsistencies should be documented.
Architectural gaps should be explicitly identified.

When a component cannot be verified from the repository, use:

Not verified from repository.

4. Current High-Level Architecture

The current architecture should be understood as a set of cooperating layers.

The exact boundaries between these components depend on the current repository implementation.

5. Current Repository Structure

The current repository structure must be treated as the primary reference for understanding component ownership.

The following conceptual structure describes the expected architectural responsibilities:

Project Root
│
├── Application / Backend
│
├── Database
│
├── Services
│
├── Workflows
│
├── Integrations / Providers
│
├── Configuration
│
├── Tests
│
└── Documentation

The exact directory names and files must be verified against the repository.

5.1 Repository Mapping
Component	Current Location	Responsibility	Status
Application entry point	Verify from repository	Starts backend/application	Not verified
API layer	Verify from repository	Handles incoming requests	Not verified
Services	Verify from repository	Business operations	Not verified
Workflow logic	Verify from repository	Rent reminder processing	Not verified
Database layer	Verify from repository	Persistent data access	Not verified
Integrations	Verify from repository	External providers	Not verified
Background jobs	Verify from repository	Scheduled processing	Not verified
Tests	Verify from repository	Validation	Not verified
Configuration	Verify from repository	Runtime configuration	Not verified

This table should be updated when the actual repository is inspected.

6. Current Application Entry Points

The system may have multiple entry points depending on how it is currently implemented.

Potential entry points include:

HTTP API.
Background worker.
Scheduler.
CLI.
Webhook.
Workflow runner.
External event handler.

The actual entry points must be identified from the repository.

6.1 Entry Point Responsibilities

An entry point should primarily:

Receive a trigger.
Validate the input.
Pass the request/event to the appropriate application component.
Return or record the result.

The entry point should not contain the complete business workflow.

7. Current Request / Execution Flow

A typical current rent reminder execution can be represented conceptually as:

The diagram represents the logical execution pattern and must be aligned with the actual implementation.

8. Current Data Flow

The current data flow can be summarized as:

Trigger
  ↓
Application
  ↓
Workflow / Business Logic
  ↓
Data Source
  ↓
Rent / Payment Evaluation
  ↓
Reminder Decision
  ↓
External Provider
  ↓
Result
  ↓
Persistence

The actual data path should be verified against the repository.

9. Current Database Architecture

The current database architecture is responsible for providing the data required by the rent reminder workflow.

Relevant business data may include:

Tenant information.
Property information.
Lease information.
Rent information.
Payment status.
Reminder information.
Workflow information.

The exact entities, database technology, ORM, repositories, and connection mechanisms must be verified from the repository.

For detailed database architecture, refer to:

03_Database_Wiring.md

10. Current Business Logic Layer

The business logic layer determines what should happen based on the available business state.

Typical responsibilities include:

Determining whether rent is due.
Determining whether payment has been received.
Determining whether a reminder should be sent.
Determining whether a workflow should continue.
Determining whether escalation is required.
Determining whether human intervention is required.

Business logic should ultimately be separated from:

HTTP handling.
Database-specific queries.
Provider-specific implementation.

The current degree of separation must be verified from the repository.

11. Current Rent Reminder Workflow

The core workflow is conceptually responsible for:

Identify Relevant Lease
        ↓
Check Rent / Payment State
        ↓
Determine Reminder Eligibility
        ↓
Check Existing Reminder State
        ↓
Send Reminder If Required
        ↓
Persist Result
        ↓
Wait / Retry / Escalate

A simplified lifecycle can be represented as:

RENT DUE
   ↓
CHECK PAYMENT
   ↓
┌───────────────┐
│ Payment Made? │
└───────┬───────┘
    YES │ NO
        │
        ↓
   STOP REMINDERS
        │
        └───────────────┐
                        ↓
                 CHECK REMINDER
                        ↓
                 SEND REMINDER
                        ↓
                 WAIT / RETRY
                        ↓
                 ESCALATE IF NEEDED

The exact state machine must be verified against the implemented workflow.

12. Current Workflow State

Workflow state may currently exist in one or more forms:

Database state.
In-memory state.
Workflow framework state.
Application state.
External state.

The authoritative workflow state must be identified from the actual implementation.

Potential workflow states include:

Pending.
Due.
Reminder required.
Reminder sent.
Waiting for payment.
Payment received.
Escalation required.
Human intervention.
Completed.
Failed.

These represent logical states and must not be assumed to be exact implementation values.

13. Current Reminder Processing

The current reminder process is responsible for determining whether a tenant should receive a rent reminder.

Conceptually:

Lease / Rent Data
       ↓
Payment Check
       ↓
Reminder Eligibility
       ↓
Existing Reminder Check
       ↓
Reminder Action

The system should avoid sending reminders when:

Payment has already been confirmed.
The workflow is complete.
A manual hold is active.
A reminder has already been processed for the applicable period.

The actual implementation of these protections must be verified.

14. Current External Provider Integration

The reminder workflow may communicate with external services/providers.

Potential provider responsibilities include:

Sending tenant notifications.
Returning delivery status.
Providing external message IDs.
Returning provider errors.
Supporting retries.

The provider should not be considered the authoritative source of business state.

The application's database should maintain the relevant business state.

Detailed provider architecture belongs in:

08_Integration_And_Provider_Layer.md

15. Current API Layer

If an HTTP API exists, its primary responsibility is to expose controlled application functionality.

Typical responsibilities include:

Request validation.
Authentication where applicable.
Calling application services.
Returning responses.
Reporting errors.

The API should not directly contain complex workflow logic.

The exact API implementation must be verified from the repository.

Detailed API architecture belongs in:

04_API_And_Service_Layer.md

16. Current Service Layer

Application services provide an intermediate layer between external entry points and business operations.

Typical responsibilities include:

Coordinating application operations.
Calling repositories.
Calling workflow components.
Managing business operations.
Handling application-level errors.

The exact service structure must be verified from the repository.

17. Current Workflow / Orchestration Layer

The workflow/orchestration layer is responsible for coordinating multiple operations.

A logical workflow may contain:

Load Data
   ↓
Validate State
   ↓
Evaluate Conditions
   ↓
Perform Action
   ↓
Persist Result
   ↓
Determine Next State

If a workflow framework such as LangGraph is currently used, its exact role should be documented based on the repository.

Detailed LangGraph integration belongs in:

07_LangGraph_Integration.md

18. Current Background Processing

The rent reminder workflow may require background execution because reminder processing should not depend entirely on interactive API requests.

Potential background mechanisms include:

Scheduled jobs.
Workers.
Task queues.
Cron jobs.
Workflow runners.

The actual implementation must be verified.

Conceptually:

Scheduler
    ↓
Find Relevant Rent Records
    ↓
Evaluate Workflow
    ↓
Execute Reminder
    ↓
Persist Result

Detailed scheduling architecture belongs in:

09_Background_Jobs_And_Scheduling.md

19. Current Configuration

The system's runtime configuration may include:

Database configuration.
Provider credentials.
API configuration.
Application environment.
Logging configuration.
Scheduler configuration.

Sensitive values must be loaded through secure configuration mechanisms.

Secrets must not be documented directly in this SDD.

20. Current Error Handling

Current error handling should be identified from the repository.

Potential error categories include:

Invalid input.
Database failure.
Workflow failure.
Provider failure.
Configuration failure.
Timeout.
External API failure.

The current system should be assessed for:

Retry behavior.
Exception handling.
Error propagation.
Logging.
Recovery behavior.

Detailed target error-handling architecture belongs in:

10_Security_And_Error_Handling.md

21. Current Logging and Observability

The current system may produce logs for:

Application startup.
Requests.
Workflow execution.
Database operations.
Provider calls.
Errors.
Scheduler activity.

The actual logging mechanism and structure must be verified.

The system should eventually provide sufficient information to answer:

Which workflow executed?
Which lease was processed?
What decision was made?
Was a reminder sent?
Which provider was used?
Did an error occur?
What happened after the error?

Detailed observability architecture belongs in:

11_Observability_And_Logging.md

22. Current Testing Architecture

Testing should be evaluated according to the actual repository.

Potential test categories include:

Unit tests.
Integration tests.
API tests.
Database tests.
Workflow tests.
Provider tests.
Scheduler tests.

The current repository should be inspected to determine which are actually implemented.

Detailed testing architecture belongs in:

12_Backend_Testing_Strategy.md

23. Current Security Boundaries

Security concerns in the current architecture include:

API authentication.
Authorization.
Database credentials.
Provider credentials.
Environment variables.
Sensitive tenant data.
External API access.
Logging of sensitive information.

The actual implementation must be verified.

Security architecture is documented separately in:

10_Security_And_Error_Handling.md

24. Current Architecture Diagram

The current system can be represented at a high level as:

This is a logical representation.

Exact implementation boundaries must be updated when the repository is inspected.

25. Current Architecture Strengths

The existing architecture should be evaluated based on the actual implementation.

Potential strengths to verify include:

Separation of workflow logic.
Existing service boundaries.
Existing database abstraction.
Existing provider abstraction.
Existing tests.
Existing scheduling mechanism.
Existing error handling.
Existing persistence.

Only verified strengths should be presented as implemented strengths.

26. Current Architecture Weaknesses / Technical Debt

The current system should be evaluated for architectural weaknesses such as:

Area	Potential Issue	Impact
Database	Multiple sources of truth	Inconsistent data
Workflow	In-memory state	State loss
Reminder	Missing idempotency	Duplicate messages
Services	Direct database access	Tight coupling
Providers	Provider-specific business logic	Difficult replacement
Scheduling	No execution protection	Duplicate processing
Errors	Weak retry classification	Unreliable workflows
Testing	Missing integration coverage	Hidden failures
Observability	Insufficient workflow tracing	Difficult debugging

These are areas for investigation rather than claims that every issue currently exists.

27. Current Architecture Risks

Important risks to evaluate include:

27.1 Multiple Sources of Truth

If multiple databases or data stores contain overlapping business state, workflow decisions may become inconsistent.

27.2 Duplicate Reminder Execution

If multiple workers process the same lease without idempotency protection, duplicate reminders may be sent.

27.3 Lost Workflow State

If important workflow state exists only in memory, it can be lost after application or worker restart.

27.4 Provider Failure

External communication providers may fail independently of the database.

The system must distinguish provider failure from business-state failure.

27.5 Database Failure

Database availability directly affects workflow reliability.

27.6 Weak Observability

Without sufficient workflow-level logging, diagnosing failed reminders becomes difficult.

28. Current-to-Target Transition

The current architecture serves as the baseline for the target architecture.

The transition should generally follow:

CURRENT SYSTEM
      ↓
Stabilize Existing Components
      ↓
Unify Database
      ↓
Wire Live Data
      ↓
Establish API / Service Boundaries
      ↓
Standardize Event / Pipeline Flow
      ↓
Improve Workflow Runner
      ↓
Integrate Providers
      ↓
Add Scheduling / Alerting
      ↓
Harden Security / Errors / Observability
      ↓
TARGET SYSTEM

The detailed target architecture is defined in:

02_Target_Backend_Architecture.md

29. Relationship With Implementation Phases

The current architecture provides the baseline for all implementation phases.

Phase 1 — Stabilization

Document and stabilize the existing system.

Primary goals:

Understand current behavior.
Identify broken components.
Identify duplicated state.
Establish reliable baseline behavior.
Phase 2 — Database Unification

Establish one authoritative source of business state.

Phase 3 — Live Data Wiring

Connect workflows and services to real authoritative data.

Phase 4 — API Layer

Create clean application/API boundaries.

Phase 5 — Scheduling and Alerting

Make automated execution reliable.

Phase 6 — Hardening

Strengthen:

Security.
Error handling.
Idempotency.
Concurrency.
Observability.
Testing.
30. Current Architecture Verification Checklist

Before treating this document as an exact repository snapshot, verify:

 Repository structure inspected.
 Application entry points identified.
 API entry points identified.
 Database technology verified.
 Database connections verified.
 Database models verified.
 Repository/data-access layer verified.
 Service layer verified.
 Workflow implementation verified.
 Reminder logic verified.
 Provider integrations verified.
 Background jobs verified.
 Configuration verified.
 Error handling verified.
 Logging verified.
 Tests verified.
 Security boundaries verified.
 Duplicate data sources identified.
 Current workflow state identified.
 Current persistence behavior identified.

Any item that cannot be verified should remain explicitly marked as:

Not verified from repository.

31. Current Architecture Summary

The Rent Reminder Workflow is fundamentally composed of:

Trigger
   ↓
Application
   ↓
Business / Workflow Logic
   ↓
Data Access
   ↓
Database
   ↓
Reminder Decision
   ↓
External Provider
   ↓
Result Persistence

The most important architectural principle for the next phases is to establish a clear separation between:

API / Trigger
      ↓
Application Services
      ↓
Workflow / Business Logic
      ↓
Repository / Data Access
      ↓
Authoritative Database

The current architecture document serves as the baseline against which all target architecture changes should be evaluated.

32. Document Status

Document: 01_Current_System_Architecture.md

Architecture Type: Current-State Architecture

Purpose: Baseline documentation of the existing Rent Reminder Workflow backend.

Source of Truth Priority:

Actual repository implementation.
Database/schema implementation.
Tests.
Configuration.
Existing documentation.

Important: Any component marked as "Not verified from repository" must be verified before being treated as an implementation fact.