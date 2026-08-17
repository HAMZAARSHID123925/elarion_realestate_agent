# Phase 3 — Live Data Wiring

## 1. Purpose

The purpose of Phase 3 is to connect the stabilized backend and unified database layer to the live application data flow required by the Rent Reminder Workflow.

Phase 2 established a unified database source of truth and a consistent data-access boundary.

Phase 3 builds on that foundation by ensuring that workflow execution uses current application data instead of isolated, duplicated, mock, or manually supplied data paths.

The objective is to establish a reliable flow from persistent application data into the Rent Reminder Workflow and back into the database when workflow state changes.

---

# 2. Phase Objective

The primary objectives of this phase are:

1. Connect workflow execution to the unified database layer.
2. Replace confirmed temporary or mock data paths where applicable.
3. Ensure the workflow reads current tenant/property/rent-related state.
4. Ensure workflow decisions are based on persisted application data.
5. Persist relevant workflow state changes back to the database.
6. Establish consistent data flow between services, workflow components, and persistence.
7. Prevent stale or duplicated application state from becoming the workflow source of truth.
8. Validate the complete read-process-write data flow.
9. Prepare the backend for API integration in Phase 4.
10. Establish the data foundation required for scheduling in Phase 5.

---

# 3. Scope

## In Scope

Phase 3 covers:

* Live database reads
* Live database writes
* Service-to-database integration
* Workflow-to-service integration
* Rent-related data retrieval
* Tenant/property data retrieval where required
* Reminder state retrieval
* Payment state retrieval
* Workflow state persistence
* Data freshness
* Data validation before workflow execution
* Replacement of confirmed mock/static data
* Integration testing of live data flow

## Out of Scope

The following are not primary objectives of Phase 3:

* New public API design
* Background scheduling implementation
* Reminder scheduling engine
* Alerting infrastructure
* New provider integrations
* Production deployment
* Major workflow redesign
* Production security hardening

These belong to later phases.

---

# 4. Preconditions

Phase 3 must begin only after Phase 2 has established the unified database architecture.

The following should already exist:

* Unified database source of truth
* Centralized database configuration
* Consistent database session/client management
* Approved data-access boundary
* Authoritative persistence models/entities
* Database tests
* Stabilized services
* Stable workflow initialization

If the current project still contains multiple competing database access paths, Phase 3 should not introduce live wiring on top of them.

---

# 5. Live Data Principle

The Rent Reminder Workflow must use the application's authoritative persistent state.

The intended logical flow is:

```text
Unified Database
       ↓
Data Access Layer
       ↓
Service Layer
       ↓
WorkflowRunner
       ↓
Rent Reminder Workflow
       ↓
Decision
       ↓
Service Layer
       ↓
Data Access Layer
       ↓
Unified Database
```

The database remains the source of truth for persisted business state.

The workflow should not maintain an independent permanent copy of database state.

---

# 6. Step 1 — Identify Required Live Data

Before wiring the workflow, identify exactly which data the Rent Reminder Workflow requires.

### Required Data Categories

The exact fields must come from the confirmed project schema.

Typical categories may include:

```text
Tenant
Property
Lease / Rental Agreement
Rent Status
Rent Due Date
Payment Status
Reminder State
Workflow State
Relevant Timestamps
```

Do not introduce fields merely because they appear useful.

Only fields required by the existing workflow and confirmed application model should be wired.

---

# 7. Step 2 — Map Data Dependencies

Create a dependency map between workflow decisions and persistent data.

Example:

```text
Workflow Decision
      ↓
Required Data
      ↓
Data Access Function
      ↓
Database Entity
```

For the Rent Reminder Workflow, the logical relationship may be:

```text
Rent Reminder Workflow
        ↓
Identify Relevant Rental Record
        ↓
Read Rent / Payment State
        ↓
Evaluate Reminder Condition
        ↓
Determine Next Workflow Action
```

The exact condition must follow the approved business rules rather than being invented during implementation.

---

# 8. Step 3 — Wire Live Reads

Workflow execution must obtain current data through the unified service/data-access architecture.

### Target Flow

```text
Workflow
   ↓
Service
   ↓
Data Access
   ↓
Database
   ↓
Current Record
   ↓
Service
   ↓
Workflow State
```

### Tasks

* Identify existing mock/static data.
* Identify hard-coded rental records.
* Identify manually supplied workflow inputs that should come from persistence.
* Replace confirmed temporary data sources.
* Ensure required records are queried through the approved data-access boundary.
* Validate returned records before workflow processing.

### Important Rule

The workflow must not directly create an independent database connection to obtain live data.

---

# 9. Step 4 — Validate Retrieved Data

Live data must be validated before it enters workflow decision logic.

### Validation Areas

Where applicable:

* Record existence
* Required identifiers
* Tenant/property relationship
* Rent-related values
* Payment status
* Relevant dates
* Current workflow state
* Data consistency

### Expected Flow

```text
Database Record
      ↓
Data Validation
      ↓
Valid?
  ↙       ↘
Yes       No
 ↓         ↓
Workflow   Controlled Error
```

Invalid or incomplete data must not silently produce an incorrect reminder decision.

---

# 10. Step 5 — Wire Live Workflow Inputs

After data retrieval and validation, the workflow must receive the data through its defined state/input mechanism.

### Tasks

* Identify the workflow entry point.
* Identify required workflow state fields.
* Map service results into workflow state.
* Avoid duplicating database models unnecessarily inside workflow state.
* Ensure workflow state contains only the information required for execution.
* Maintain clear separation between persistence models and workflow state.

### Logical Flow

```text
Persistent Data
      ↓
Service Result
      ↓
Workflow Input / State
      ↓
Workflow Nodes
```

The exact state structure must follow the existing LangGraph and WorkflowRunner architecture.

---

# 11. Step 6 — Connect Rent Reminder Decision Logic

The workflow must evaluate the reminder conditions using live data.

The conceptual flow is:

```text
Load Current Rental State
          ↓
Evaluate Rent Condition
          ↓
Payment State?
     ↙          ↘
Paid           Not Paid
 ↓                ↓
Complete       Reminder Decision
                  ↓
             Required Action
```

The exact business rules must follow the approved Rent Reminder Workflow specification.

No new reminder policy should be introduced merely as part of data wiring.

---

# 12. Step 7 — Persist Workflow State Changes

When workflow execution changes persistent business state, those changes must be written through the unified database layer.

Examples may include:

* Reminder status
* Workflow status
* Payment-related state
* Last processed timestamp
* Relevant execution state

Only fields confirmed by the existing data model should be modified.

### Target Flow

```text
Workflow Decision
       ↓
Service
       ↓
Data Access
       ↓
Database Update
```

Workflow nodes should not bypass the established persistence boundary unless explicitly required by the architecture.

---

# 13. Step 8 — Ensure Read-After-Write Consistency

After a workflow state change is persisted, the system must be able to retrieve the updated state correctly.

### Example Flow

```text
Read Current State
       ↓
Process Workflow
       ↓
Update State
       ↓
Persist
       ↓
Read Updated State
       ↓
Verify
```

This is particularly important for reminder workflows because later executions may depend on the state produced by earlier executions.

The implementation must prevent a previous workflow execution from being incorrectly repeated because the state update was not persisted.

---

# 14. Step 9 — Remove Confirmed Mock or Static Data

Any mock/static data identified during Phase 1 or Phase 2 should be reviewed.

### Tasks

Identify:

* Hard-coded tenant data
* Hard-coded property data
* Hard-coded rent records
* Mock payment states
* Static reminder states
* Temporary workflow inputs
* Test-only data accidentally used by runtime code

### Rules

Not all mock data should be removed.

Test fixtures and isolated test data must remain where required.

The objective is to remove mock/static data from the **runtime production data path**, not from tests.

---

# 15. Step 10 — Handle Missing Data

The live workflow must define behavior for missing records.

Examples include:

```text
Tenant Not Found
Property Not Found
Rental Record Not Found
Payment State Missing
Required Workflow State Missing
```

### Expected Behavior

```text
Missing Data
     ↓
Controlled Failure
     ↓
Structured Error
     ↓
Logging
     ↓
Workflow Stops or Follows Defined Recovery Path
```

The system must not assume that a record exists merely because the workflow expects it.

---

# 16. Step 11 — Handle Stale Data

Live data can change between workflow executions.

### Tasks

* Identify fields that can change between executions.
* Ensure workflow execution reads current persistent state.
* Avoid relying on stale cached values unless caching is explicitly part of the architecture.
* Validate important state before performing irreversible actions.
* Ensure repeated workflow execution does not operate on outdated state.

### Principle

For business-critical decisions, persistent state should be re-read according to the established data-access and workflow execution model.

---

# 17. Step 12 — Establish Idempotent State Updates

Live data wiring must not cause duplicate state changes when the same workflow execution is repeated.

### Examples

A repeated execution should not unintentionally:

* Create duplicate reminder records
* Reset already completed states
* Reapply the same state transition incorrectly
* Produce duplicate side effects

The exact idempotency strategy must follow the workflow and persistence architecture.

Where necessary, the implementation should use:

* Existing unique identifiers
* Existing state checks
* Existing workflow execution identifiers
* Existing persistence constraints

Do not invent a new idempotency mechanism without confirming that the existing architecture requires it.

---

# 18. Step 13 — Separate Data Retrieval from Side Effects

Reading live data and performing external side effects should remain logically separate.

The preferred conceptual flow is:

```text
Read Current State
       ↓
Validate
       ↓
Evaluate Workflow
       ↓
Determine Action
       ↓
Persist Internal State
       ↓
External Side Effect
```

External side effects may include reminder delivery or provider operations.

The provider layer defined in:

`08_Integration_And_Provider_Layer.md`

must remain the boundary for external integrations.

Phase 3 should wire the data required by those operations without turning the database layer into a provider layer.

---

# 19. Step 14 — Workflow Data Flow Validation

The complete live data path must be tested.

### Required Flow

```text
Database
   ↓
Data Access
   ↓
Service
   ↓
WorkflowRunner
   ↓
LangGraph / Workflow
   ↓
Decision
   ↓
Service
   ↓
Data Access
   ↓
Database
```

Each boundary must be validated independently and as part of the complete flow.

---

# 20. Step 15 — Integration Testing

Phase 3 requires integration tests covering live data behavior.

## Database → Service

Verify:

* Correct records are retrieved.
* Missing records are handled.
* Invalid data is handled.
* Current state is returned.

## Service → Workflow

Verify:

* Correct data reaches workflow state.
* Required fields are available.
* Invalid state is rejected appropriately.

## Workflow → Service

Verify:

* Workflow decisions produce the expected service operation.
* State changes are passed correctly.

## Service → Database

Verify:

* State updates are persisted.
* Failed writes are handled.
* Transactions behave correctly.

## End-to-End Data Flow

Verify:

```text
Persisted State
      ↓
Workflow Execution
      ↓
Decision
      ↓
Persisted State Change
```

---

# 21. Step 16 — Regression Validation

Live data wiring must not break the stabilized backend.

Validate:

* Application startup
* Configuration
* Database initialization
* Existing services
* Existing workflow behavior
* Database tests
* Service tests
* Workflow tests
* Error handling
* Logging

Any regression must be resolved before Phase 3 is considered complete.

---

# 22. Observability Requirements

Live data wiring must remain observable.

Relevant events should provide enough information to understand:

* Workflow execution started
* Required data was retrieved
* Data validation succeeded/failed
* Workflow decision occurred
* State update was attempted
* State update succeeded/failed

Sensitive tenant or payment information must not be unnecessarily exposed in logs.

Observability must follow:

`11_Observability_And_Logging.md`

---

# 23. Security Considerations

Live data wiring introduces direct access to application data and therefore must follow the security rules defined in:

`10_Security_And_Error_Handling.md`

### Requirements

* Do not log sensitive data unnecessarily.
* Do not expose database credentials.
* Do not expose internal database errors directly to external callers.
* Validate data before processing.
* Restrict access to required data only.
* Keep provider credentials outside application source code.
* Preserve existing authorization boundaries where applicable.

Phase 6 will provide additional production hardening.

---

# 24. Phase 3 Deliverables

## Code

* Live database reads connected to required workflow data
* Live database writes connected to required state changes
* Services connected to unified data access
* Workflow connected to live service data
* Runtime mock/static data removed where confirmed obsolete
* Data validation implemented
* Missing-data handling implemented
* State persistence implemented
* Required idempotency protections implemented
* Integration tests added

## Documentation

* Live data flow documented
* Workflow data dependencies documented
* Runtime mock data identified and removed/documented
* Data validation rules documented
* Known live-data limitations documented

## Validation

* Workflow can read current persistent data.
* Workflow decisions use current data.
* Relevant workflow state changes are persisted.
* Repeated execution does not unintentionally corrupt state.
* Missing data is handled safely.
* Database and workflow integration tests pass.
* Existing regression tests pass.

---

# 25. Phase 3 Exit Criteria

Phase 3 is complete only when all applicable criteria are satisfied:

* [ ] Workflow reads required runtime data from the unified database path.
* [ ] Runtime mock/static data has been removed where confirmed obsolete.
* [ ] Required live data dependencies are documented.
* [ ] Retrieved data is validated before workflow processing.
* [ ] Workflow state receives the correct live data.
* [ ] Workflow decisions use persisted application state.
* [ ] Required workflow state changes are persisted.
* [ ] Database writes use the unified data-access architecture.
* [ ] Missing data has controlled handling.
* [ ] Stale-state risks have been addressed.
* [ ] Required idempotency protections are in place.
* [ ] Database → service → workflow → database flow has been integration tested.
* [ ] Relevant logs provide sufficient execution visibility.
* [ ] Sensitive data is not unnecessarily exposed.
* [ ] Regression tests pass.
* [ ] Phase 4 prerequisites are satisfied.

---

# 26. Phase 3 Risks

| Risk                                                        | Impact   | Mitigation                                                            |
| ----------------------------------------------------------- | -------- | --------------------------------------------------------------------- |
| Workflow continues using stale/mock runtime data            | High     | Trace all runtime data sources                                        |
| Incorrect data mapping                                      | Critical | Validate each workflow input against the persistence model            |
| State changes are not persisted                             | Critical | Add read-after-write integration tests                                |
| Duplicate workflow execution causes duplicate state changes | High     | Establish appropriate idempotency checks                              |
| Missing records cause incorrect decisions                   | High     | Implement explicit missing-data handling                              |
| Workflow bypasses service/data-access layer                 | High     | Enforce the approved architecture                                     |
| Sensitive data appears in logs                              | High     | Apply observability and security rules                                |
| Live wiring breaks existing workflow behavior               | High     | Run regression tests                                                  |
| Business rules are changed during integration               | High     | Keep business-rule changes outside Phase 3 unless explicitly required |

---

# 27. Dependencies on Other SDD Documents

Phase 3 must remain aligned with:

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

Phase 3 must use the database architecture established in Phase 2 and must not introduce an independent persistence path.

---

# 28. Transition to Phase 4

After Phase 3 has passed its exit criteria, implementation can proceed to:

**Phase 4 — API Layer**

Phase 4 will expose the stabilized services and workflow capabilities through the approved backend API architecture.

The API layer must consume the services and unified data-access layer established in Phases 2 and 3 rather than implementing independent business or database logic.
