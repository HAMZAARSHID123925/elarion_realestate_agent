# Software Design Document — Rent Reminder Workflow

> **Document Path:** `docs/SDD/00_SDD_Master.md`
> **Version:** 1.0
> **Status:** Active
> **Audience:** Developers, AI Coding Agents, Reviewers, Future Maintainers

---

## 1. Document Purpose

This document is the **Master Software Design Document (SDD)** for the Rent Reminder Workflow backend. It serves as the single entry point and high-level reference for all backend architectural decisions, component relationships, implementation phases, and engineering principles.

This master document does **not** contain detailed implementation specifications. All detailed technical decisions are documented in the linked child SDD files referenced in [Section 10](#10-sdd-document-map). Readers should use this document to understand the overall system, locate the correct SDD for a given concern, and understand the principles that govern implementation.

This document is also intended as the authoritative orientation resource for AI coding agents operating on this codebase. See [Section 15](#15-ai-coding-agent-guidelines) for agent-specific rules.

---

## 2. System Overview

The Rent Reminder Workflow backend is an automated system that manages the full lifecycle of rent reminders for tenants on an Elarion real estate platform.

**Problem Being Solved:**
Property managers need a reliable, automated mechanism to remind tenants of upcoming and overdue rent payments, escalate when reminders go unanswered, respond intelligently to tenant replies, and stop the workflow immediately when payment is confirmed — all without manual intervention at each step.

**Main Workflow:**
The system monitors lease and payment state, triggers timed reminders, processes tenant responses, classifies intent, escalates to human managers when required, and terminates the reminder cycle upon payment confirmation or manual hold.

**Actors / Interactors:**
- Tenants (receive reminders, send responses)
- Property Managers (receive escalations, intervene manually)
- Scheduler / Background Jobs (trigger reminder events)
- External Communication Providers (SMS, WhatsApp, Email, etc.)
- LangGraph Workflow Engine (agentic intent classification and routing)

**Backend Responsibilities:**
- Lease and payment state tracking
- Reminder scheduling and dispatch
- Tenant response processing and intent routing
- Escalation logic and human-in-the-loop handoff
- Workflow execution and state management
- Provider-agnostic communication dispatch
- Observability and error handling

**Out of Scope for Backend:**
- Frontend / Dashboard UI
- Payment gateway processing
- Unrelated property management features (maintenance, listings, etc.)

---

## 3. System Goals

1. **Reliable Rent Reminder Automation** — Reminders must be dispatched at the correct times without manual triggering.
2. **Correct Rent and Payment State Tracking** — The system must accurately reflect whether rent is due, overdue, or paid.
3. **Deterministic Workflow Execution** — Given the same state, the workflow must produce the same output.
4. **Clean Backend Service Boundaries** — Each layer must have a well-defined responsibility with no cross-layer leakage.
5. **Provider Abstraction** — Communication providers (SMS, email, etc.) must be swappable without changing business logic.
6. **Failure Isolation** — Failures in external providers or sub-components must not collapse the entire workflow.
7. **Observability** — All significant workflow events, state transitions, and errors must be logged and traceable.
8. **Testability** — All layers must be independently testable with minimal real-infrastructure dependencies.
9. **Safe Human Escalation** — Escalation to property managers must be reliable, auditable, and reversible via manual hold.
10. **Maintainability** — The codebase and documentation must allow future developers and agents to understand and extend the system safely.

---

## 4. Non-Goals

The following are explicitly **outside the scope** of this backend:

- Frontend or dashboard implementation (UI/UX is a separate concern)
- Direct payment gateway integration or financial transaction processing
- Tenant onboarding or lease creation workflows (separate domain)
- Unrelated property management features (maintenance requests, listings, inspections)
- Provider-specific business logic embedded in the core domain layer
- Real-time chat or live support infrastructure

> ⚠️ If any of the above are found to have partial implementation in the repository, they should be treated as incidental and not expanded without explicit architectural review.

---

## 5. Current State vs Target State

> **Note:** Items marked *"Not verified from repository"* could not be confirmed from available repository context and must be validated before implementation begins.

| Area | Current State | Target State |
|---|---|---|
| **Database** | Not verified from repository | Unified PostgreSQL schema with clean table boundaries for tenants, leases, payments, workflow state, and escalation |
| **Services** | Not verified from repository | Clearly separated service classes per domain concern (ReminderService, PaymentService, EscalationService, etc.) |
| **API** | Not verified from repository | FastAPI-based REST API with versioned endpoints, input validation, and standardized error responses |
| **Workflow Execution** | Not verified from repository | WorkflowRunner executing deterministic, state-managed reminder lifecycle steps |
| **Event Pipeline** | Not verified from repository | Event-driven pipeline routing internal domain events to appropriate handlers |
| **LangGraph** | Not verified from repository | LangGraph integrated for agentic tenant response classification and intent-based routing |
| **Providers** | Not verified from repository | Provider abstraction layer with pluggable SMS/WhatsApp/Email adapters |
| **Scheduling** | Not verified from repository | Celery-based background job scheduler triggering reminder events on a defined cadence |
| **Error Handling** | Not verified from repository | Centralized error handling with retry logic, dead-letter queuing, and structured error reporting |
| **Logging** | Not verified from repository | Structured logging across all layers with workflow correlation IDs |
| **Testing** | Not verified from repository | Unit + integration test coverage across service, workflow, and provider layers |

---

## 6. High-Level Backend Architecture

The following describes the **conceptual target architecture** at a high level. Detailed specifications for each layer are in the corresponding child SDD files.

```
External Trigger (Scheduler / Tenant Response / API Call)
    ↓
API / Input Layer
    ↓
Service Layer
    ↓
Domain / Business Logic
    ↓
WorkflowRunner / Event Pipeline
    ↓
LangGraph (for agentic intent classification)
    ↓
Repository / Database Layer
    ↓
Provider / Integration Layer (SMS, WhatsApp, Email, etc.)
    ↓
External Communication (Tenant / Manager)
```

**Layer Responsibilities:**

| Layer | Responsibility |
|---|---|
| API / Input Layer | Accept external requests, validate inputs, route to services |
| Service Layer | Orchestrate business operations, enforce rules, coordinate components |
| Domain / Business Logic | Pure business rules: reminder eligibility, payment state, escalation criteria |
| WorkflowRunner | Execute multi-step reminder lifecycle with state checkpointing |
| Event Pipeline | Route internal domain events to appropriate handlers asynchronously |
| LangGraph | Classify tenant response intent, route to correct workflow branch |
| Repository Layer | Abstract all database access behind interface contracts |
| Provider Layer | Abstract all external communication behind swappable adapters |
| Background Jobs | Celery tasks for scheduled triggers and async processing |

---

## 7. Major Architectural Components

| Component | Responsibility | Depends On | Detailed SDD |
|---|---|---|---|
| **Database / Schema** | Persist tenants, leases, payments, workflow state, escalation records | PostgreSQL | [03_Database_Wiring.md](./03_Database_Wiring.md) |
| **API Layer** | Expose REST endpoints for external triggers and manager actions | Service Layer | [04_API_And_Service_Layer.md](./04_API_And_Service_Layer.md) |
| **Service Layer** | Business operation orchestration | Domain Logic, Repositories, Providers | [04_API_And_Service_Layer.md](./04_API_And_Service_Layer.md) |
| **Event Pipeline** | Async internal event routing | Service Layer, WorkflowRunner | [05_Event_And_Pipeline_Architecture.md](./05_Event_And_Pipeline_Architecture.md) |
| **WorkflowRunner** | Deterministic reminder lifecycle execution | Domain Logic, Event Pipeline, DB | [06_WorkflowRunner_Architecture.md](./06_WorkflowRunner_Architecture.md) |
| **LangGraph Integration** | Agentic intent classification of tenant responses | WorkflowRunner, Service Layer | [07_LangGraph_Integration.md](./07_LangGraph_Integration.md) |
| **Provider Layer** | Pluggable communication adapters (SMS, WhatsApp, Email) | External APIs | [08_Integration_And_Provider_Layer.md](./08_Integration_And_Provider_Layer.md) |
| **Background Jobs / Scheduler** | Celery tasks for timed reminder triggers | WorkflowRunner, Service Layer | [09_Background_Jobs_And_Scheduling.md](./09_Background_Jobs_And_Scheduling.md) |
| **Security / Error Handling** | Auth, input validation, retry logic, failure isolation | All layers | [10_Security_And_Error_Handling.md](./10_Security_And_Error_Handling.md) |
| **Observability / Logging** | Structured logs, correlation IDs, monitoring | All layers | [11_Observability_And_Logging.md](./11_Observability_And_Logging.md) |
| **Testing Infrastructure** | Unit, integration, and workflow-level test coverage | All layers | [12_Backend_Testing_Strategy.md](./12_Backend_Testing_Strategy.md) |

---

## 8. Core Rent Reminder Workflow

The following describes the **high-level business workflow** managed by the backend. Exact implementation mechanics (state machines, graph nodes, database fields) are in the detailed SDDs.

```
Tenant / Lease Record
    ↓
Rent Due Date Approached
    ↓
[~Day 30] Normal Rent Reminder Dispatched
    ↓
Payment Check
    ├── PAID → Workflow Terminates ✓
    └── UNPAID ↓
[~Day 35] Urgent Reminder Dispatched
    ↓
Payment Check
    ├── PAID → Workflow Terminates ✓
    └── UNPAID ↓
[Day 36+] Human / Manager Escalation
    ↓
Property Manager Notified
    ↓
Manual Intervention / Hold
    ├── Manual Hold Enabled → Workflow Paused
    └── Resolved → Workflow Terminates ✓
```

**Key Workflow Behaviors:**

| Behavior | Description |
|---|---|
| **Reminder Timing** | ~Day 30 (normal), ~Day 35 (urgent). Exact thresholds defined in WorkflowRunner SDD. |
| **Escalation** | Day 36+ triggers manager escalation if rent remains unpaid and no manual hold is active. |
| **Manual Hold** | Property managers can pause the workflow via API. Hold state is persisted in the database. |
| **Payment State** | Payment confirmation (via webhook or manual update) immediately terminates the reminder workflow. |
| **Tenant Responses** | Tenant replies are classified by LangGraph for intent (paid, disputing, requesting extension, etc.) and routed accordingly. |
| **Workflow Termination** | Workflow stops on: payment confirmed, manual resolution, or explicit manager close. |

---

## 9. Data Flow Overview

```
[Scheduled Trigger / Webhook / API Call]
    ↓
API or Event Input Layer
    ↓
Service Layer validates and routes
    ↓
Domain Logic evaluates rent/payment state
    ↓
WorkflowRunner determines next workflow step
    ↓
Repository Layer reads/writes workflow + payment state
    ↓
Provider Layer dispatches communication to tenant/manager
    ↓
Tenant responds (SMS/WhatsApp/Email reply)
    ↓
Response received via provider webhook
    ↓
LangGraph classifies intent
    ↓
WorkflowRunner routes based on intent
    ↓
State updated in database
    ↓
Workflow continues or terminates
```

---

## 10. SDD Document Map

### Core Architecture Documents

| # | Document | Purpose |
|---|---|---|
| 00 | [00_SDD_Master.md](./00_SDD_Master.md) | Master index, system overview, principles, and navigation |
| 01 | [01_Current_System_Architecture.md](./01_Current_System_Architecture.md) | Documented snapshot of the current backend state |
| 02 | [02_Target_Backend_Architecture.md](./02_Target_Backend_Architecture.md) | Full specification of the target backend architecture |
| 03 | [03_Database_Wiring.md](./03_Database_Wiring.md) | Database schema, table relationships, migration strategy |
| 04 | [04_API_And_Service_Layer.md](./04_API_And_Service_Layer.md) | API endpoint design and service layer contracts |
| 05 | [05_Event_And_Pipeline_Architecture.md](./05_Event_And_Pipeline_Architecture.md) | Internal event system and async pipeline design |
| 06 | [06_WorkflowRunner_Architecture.md](./06_WorkflowRunner_Architecture.md) | Workflow execution engine, state management, step logic |
| 07 | [07_LangGraph_Integration.md](./07_LangGraph_Integration.md) | LangGraph graph design, nodes, edges, intent classification |
| 08 | [08_Integration_And_Provider_Layer.md](./08_Integration_And_Provider_Layer.md) | External provider adapters, abstraction contracts |
| 09 | [09_Background_Jobs_And_Scheduling.md](./09_Background_Jobs_And_Scheduling.md) | Celery task design, scheduler configuration, job reliability |
| 10 | [10_Security_And_Error_Handling.md](./10_Security_And_Error_Handling.md) | Auth, input validation, retry logic, failure isolation |
| 11 | [11_Observability_And_Logging.md](./11_Observability_And_Logging.md) | Structured logging, correlation IDs, monitoring hooks |
| 12 | [12_Backend_Testing_Strategy.md](./12_Backend_Testing_Strategy.md) | Unit, integration, and workflow test strategy |

### Implementation Phase Documents

| Phase | Document | Purpose |
|---|---|---|
| Phase 1 | [Phase_1_Stabilization.md](./phases/Phase_1_Stabilization.md) | Stabilize existing code, resolve inconsistencies, establish baseline |
| Phase 2 | [Phase_2_Database_Unification.md](./phases/Phase_2_Database_Unification.md) | Unify and clean the database schema |
| Phase 3 | [Phase_3_Live_Data_Wiring.md](./phases/Phase_3_Live_Data_Wiring.md) | Wire live data sources into workflow execution |
| Phase 4 | [Phase_4_API_Layer.md](./phases/Phase_4_API_Layer.md) | Build and harden the API layer |
| Phase 5 | [Phase_5_Scheduling_And_Alerting.md](./phases/Phase_5_Scheduling_And_Alerting.md) | Implement scheduling and alerting infrastructure |
| Phase 6 | [Phase_6_Hardening.md](./phases/Phase_6_Hardening.md) | Harden for production: security, observability, resilience |

---

## 11. Implementation Phase Map

| Phase | Name | Main Objective | Related SDDs |
|---|---|---|---|
| **Phase 1** | Stabilization | Audit and stabilize the existing codebase. Resolve inconsistencies. Establish a verified baseline before any new development. | 01, 02 |
| **Phase 2** | Database Unification | Consolidate and clean up the database schema. Ensure all tables, relationships, and migrations reflect the target data model. | 03 |
| **Phase 3** | Live Data Wiring | Connect workflow execution to live database state. Ensure payment state, lease records, and tenant data flow correctly into the WorkflowRunner. | 03, 05, 06 |
| **Phase 4** | API Layer | Build and expose the API layer. Define and implement all endpoints needed for external triggers, manager actions, and webhook ingestion. | 04 |
| **Phase 5** | Scheduling and Alerting | Implement Celery-based job scheduling for reminder triggers. Wire alerting for escalation and failure conditions. | 09, 08 |
| **Phase 6** | Hardening | Production readiness: security hardening, comprehensive error handling, structured logging, observability, and full test coverage. | 10, 11, 12 |

---

## 12. Architectural Principles

### 12.1 Single Source of Truth
Every piece of data or state has exactly one authoritative location. Payment state lives in the database. Workflow state lives in the WorkflowRunner's state store. No duplication of state across layers.

### 12.2 Separation of Concerns
Each layer owns a clearly bounded set of responsibilities. The API layer does not contain business logic. The service layer does not contain SQL. The domain layer does not know about providers.

### 12.3 Provider Abstraction
All external communication (SMS, WhatsApp, Email) is routed through a provider abstraction layer. Business logic never depends on a specific provider's API. Providers are swappable via configuration.

### 12.4 Deterministic Workflow Execution
Given the same input state, the WorkflowRunner must always produce the same output. No non-deterministic behavior in the core workflow path (e.g., no random branching, no uncontrolled side effects).

### 12.5 Idempotency
Reminder dispatch, state transitions, and event handling must be idempotent where possible. Re-delivering an event or retrying a job must not produce duplicate reminders or corrupt state.

### 12.6 Failure Isolation
Failures in one component (e.g., a provider being down) must not cascade into failures in unrelated components. Circuit breakers, retries, and dead-letter handling must be applied at appropriate integration points.

### 12.7 Observability
Every significant event — workflow step execution, reminder dispatch, payment state change, escalation trigger, error — must produce a structured log entry with a workflow correlation ID enabling full trace reconstruction.

### 12.8 Testability
All service, domain, workflow, and provider components must be independently testable. External dependencies (providers, database) must be injectable or mockable in tests.

### 12.9 Explicit State Management
Workflow and payment state must always be explicitly persisted in the database. No state is inferred from side effects. State transitions are atomic and auditable.

### 12.10 Human Escalation Safety
Escalation to property managers must be reliable, auditable, and safely reversible. Manual holds must be honored immediately. No automated action may override a manual hold.

---

## 13. Dependency Direction

Dependencies must always flow **downward**. Upper layers depend on lower layers. Lower layers must never import from upper layers.

```
API Layer
    ↓
Service Layer
    ↓
Domain / Business Logic
    ↓
WorkflowRunner / Event Pipeline
    ↓
Repository Layer (DB Abstraction)
    ↓
Infrastructure (PostgreSQL, Celery, Redis)

Provider Layer (injected into Service Layer via abstraction)
LangGraph (invoked by WorkflowRunner via adapter)
```

**Rules:**
- The Domain / Business Logic layer must have **zero** knowledge of API framework details, provider SDKs, or database drivers.
- Providers are injected into the service layer via interface contracts — the service layer calls an abstraction, not a concrete SDK.
- LangGraph is invoked through an adapter or integration boundary, not directly embedded in business logic.
- Infrastructure (database connections, Celery config) is wired at the application composition root and injected downward.

---

## 14. Source of Truth Rules

When there is a conflict between documentation and actual implementation, the following priority order applies. Future developers and AI coding agents **must** respect this hierarchy:

| Priority | Source | Notes |
|---|---|---|
| **1** | Actual working code | The implementation is ground truth |
| **2** | Database / schema definitions | Migrations and schema files define the data contract |
| **3** | Existing tests | Tests encode verified expected behavior |
| **4** | Existing configuration | Config files define runtime behavior |
| **5** | Detailed SDD documents (01–12) | Design intent for each subsystem |
| **6** | This Master SDD | High-level architectural intent |
| **7** | General assumptions | Last resort — must be explicitly flagged |

> ⚠️ **Critical Rule:** If documentation conflicts with verified implementation, the conflict must be **explicitly identified and resolved**. Do not silently invent behavior to paper over contradictions. Raise the conflict as an open question before proceeding.

---

## 15. AI Coding Agent Guidelines

This SDD and its child documents are designed to be consumed by AI coding agents (Claude Code, Cursor, Windsurf). The following rules are **mandatory** for all agent operations on this codebase:

1. **Read the relevant SDD before modifying any subsystem.** Do not proceed based on memory or training data alone.
2. **Inspect the current code before implementing.** Verify the actual state of the file or module before writing or editing.
3. **Do not invent missing APIs, services, or database tables.** If something does not exist and is needed, flag it as a gap.
4. **Do not duplicate business logic.** If equivalent logic exists elsewhere, use or extend it — do not create a parallel implementation.
5. **Do not bypass service or repository layer boundaries.** API code does not call the database directly. Services do not call provider SDKs directly.
6. **Follow existing naming conventions.** Match the casing, naming patterns, and module structure already present in the codebase.
7. **Update tests when behavior changes.** No behavior change is complete without corresponding test updates.
8. **Update the relevant SDD when architecture changes.** Documentation drift is a defect.
9. **Never silently change architectural decisions.** Surface conflicts and get explicit approval before deviating from the SDD.
10. **Ask for clarification when requirements conflict.** Do not guess. Surface the conflict with a specific question.

---

## 16. Architecture Decision Boundaries

To prevent duplicate or conflicting documentation, each architectural concern is owned by exactly one SDD document:

| Concern | Owning Document |
|---|---|
| Current system state and gaps | [01_Current_System_Architecture.md](./01_Current_System_Architecture.md) |
| Full target architecture spec | [02_Target_Backend_Architecture.md](./02_Target_Backend_Architecture.md) |
| Database schema and migrations | [03_Database_Wiring.md](./03_Database_Wiring.md) |
| API endpoints and service contracts | [04_API_And_Service_Layer.md](./04_API_And_Service_Layer.md) |
| Async event pipeline design | [05_Event_And_Pipeline_Architecture.md](./05_Event_And_Pipeline_Architecture.md) |
| WorkflowRunner and step logic | [06_WorkflowRunner_Architecture.md](./06_WorkflowRunner_Architecture.md) |
| LangGraph graph design and intent routing | [07_LangGraph_Integration.md](./07_LangGraph_Integration.md) |
| External provider adapters | [08_Integration_And_Provider_Layer.md](./08_Integration_And_Provider_Layer.md) |
| Celery tasks and job scheduling | [09_Background_Jobs_And_Scheduling.md](./09_Background_Jobs_And_Scheduling.md) |
| Auth, validation, error handling, retries | [10_Security_And_Error_Handling.md](./10_Security_And_Error_Handling.md) |
| Logging, correlation IDs, monitoring | [11_Observability_And_Logging.md](./11_Observability_And_Logging.md) |
| Test strategy and coverage | [12_Backend_Testing_Strategy.md](./12_Backend_Testing_Strategy.md) |

> Any decision that spans multiple concerns must be documented in **both** relevant SDDs with a cross-reference, and the primary decision authority must be explicitly stated.

---

## 17. Change Management

When architectural or implementation changes are required, follow this process:

1. **Identify the affected component** — determine which layer and which SDD owns the concern.
2. **Inspect the relevant SDD** — read the current documented design before proposing changes.
3. **Inspect the current code** — verify the actual state of the implementation.
4. **Update the design** — document the change in the relevant SDD before implementing.
5. **Implement the code change** — follow the updated design.
6. **Update tests** — add or update tests to cover the changed behavior.
7. **Update the affected SDD** — reflect the final implemented state in the documentation.
8. **Validate integration** — confirm that no adjacent components were broken by the change.
9. **Record significant decisions** — if the change represents an architectural decision, document the rationale in the relevant SDD under an "Architectural Decisions" or "ADR" section.

---

## 18. Open Questions / Unverified Areas

The following areas could **not** be verified from the available repository context at the time this document was authored:

| Area | Status |
|---|---|
| Current database schema and existing tables | Not verified from repository |
| Current service layer structure and existing service classes | Not verified from repository |
| Existing API endpoints and their contracts | Not verified from repository |
| Current WorkflowRunner implementation (if any) | Not verified from repository |
| LangGraph graph definition and current node structure | Not verified from repository |
| Currently integrated communication providers | Not verified from repository |
| Existing Celery task definitions | Not verified from repository |
| Current test coverage and test framework setup | Not verified from repository |
| Existing logging configuration and tooling | Not verified from repository |

> ⚠️ All child SDD documents (01–12) must resolve these open questions by inspecting the actual repository before documenting the current state. Do not carry forward assumptions from this list into implementation.

---

## 19. Final Architecture Summary

The **Rent Reminder Workflow backend** is an automated, event-driven system that manages the complete lifecycle of rent reminders — from initial reminder dispatch through escalation to property managers — for tenants on the Elarion real estate platform.

**How the major components connect:**
The scheduler triggers reminder events via Celery background jobs. These events enter the system through the service layer, which invokes the WorkflowRunner to determine the correct next step based on current rent and payment state. The WorkflowRunner persists all state transitions in PostgreSQL via the repository layer, and dispatches communications through the provider abstraction layer. Tenant responses re-enter the system via provider webhooks, are classified by LangGraph for intent, and are routed back into the WorkflowRunner for appropriate handling — payment confirmation, hold, escalation, or continuation.

**How this SDD is organized:**
This master document provides system-level orientation. Each of the 12 child SDD documents owns a specific architectural concern. Six phase documents define the incremental implementation roadmap.

**How future developers and AI agents should use this documentation:**
1. Start here to understand the system and locate the relevant SDD for your concern.
2. Read the specific child SDD before modifying any subsystem.
3. Inspect the actual code to verify current state before implementing.
4. Follow the principles in Section 12, the dependency rules in Section 13, and the source of truth hierarchy in Section 14.
5. Update the relevant SDD after any architectural change.

---

*This document is the living entry point for the Rent Reminder Workflow SDD. It must be kept current as the system evolves.*