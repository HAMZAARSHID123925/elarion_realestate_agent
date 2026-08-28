# Phase 2 — Database Unification

## 1. Purpose

The purpose of Phase 2 is to establish a unified and consistent database access architecture for the Rent Reminder Workflow backend.

Phase 1 identified the current database connections, access points, models, repositories, and duplicated database logic.

Phase 2 uses those findings to reduce database fragmentation and establish a clear source of truth for application data.

The objective is not to redesign the entire data model unnecessarily. The objective is to make database access predictable, consistent, testable, and ready for live data integration in Phase 3.

---

# 2. Phase Objective

The primary objectives of this phase are:

1. Establish one clearly defined database access strategy.
2. Identify and remove confirmed duplicate database access paths.
3. Standardize database connection/session management.
4. Establish clear ownership of database operations.
5. Ensure services do not bypass the intended data-access layer.
6. Align existing models/entities with the approved database design.
7. Remove conflicting or obsolete database implementations where confirmed.
8. Ensure database operations can be tested independently.
9. Establish transaction and error-handling boundaries.
10. Prepare the database layer for Phase 3 live-data wiring.

---

# 3. Scope

## In Scope

Phase 2 covers:

* Database connection management
* Database session/client management
* Existing database access points
* Existing models/entities
* Repository/data-access patterns
* Database configuration
* Duplicate database implementations
* Service-to-database boundaries
* Transaction boundaries
* Database error handling
* Database testing
* Data-access consistency
* Source-of-truth definition

## Out of Scope

The following are not primary objectives of Phase 2:

* Live production data integration
* New API development
* Reminder scheduling
* Background job implementation
* Provider integrations
* Alerting infrastructure
* Major business-logic changes
* Production deployment
* Unrelated schema redesign

These concerns belong to later phases.

---

# 4. Preconditions

Phase 2 should begin only after Phase 1 has established a reliable understanding of the current database implementation.

The following should be available:

* Current database access map
* Current database configuration
* Existing models/entities
* Existing repositories/data-access functions
* Existing database initialization logic
* Existing tests
* Known database-related technical debt

If any database behavior cannot be confirmed from the codebase, it must be documented as unresolved rather than assumed.

---

# 5. Database Unification Principle

The backend must have a clear database source of truth.

The intended logical flow is:

```text
Workflow / API / Service
          ↓
   Service Layer
          ↓
 Data Access / Repository
          ↓
 Database Session / Client
          ↓
       Database
```

Application components should not create arbitrary database connections or bypass the established data-access boundary.

The exact implementation technology must follow the existing project architecture and confirmed technology choices.

---

# 6. Step 1 — Inventory Current Database Implementations

Before changing the database layer, inspect every existing database implementation.

### Tasks

Identify:

* Database initialization modules
* Connection creation
* Session/client creation
* Models/entities
* Repository classes/functions
* Direct queries
* Raw SQL usage
* Service-level database access
* Workflow-level database access
* API-level database access
* Test database configuration
* Development database configuration
* Any duplicated database clients
* Any legacy database implementations

### Deliverable

Create a database implementation map similar to:

```text
Database Configuration
        ↓
Database Initialization
        ↓
Session / Client
        ↓
Repository / Data Access
        ↓
Services
        ↓
Workflow / API
```

The actual project structure must be based on the codebase rather than assumptions.

---

# 7. Step 2 — Define the Database Source of Truth

A single authoritative database configuration and access path must be established.

### Tasks

* Identify the database that should serve as the application source of truth.
* Identify obsolete or duplicate database instances.
* Identify configuration values pointing to different databases.
* Identify code that reads from one database while another component writes to another.
* Identify development/test database differences.

### Rule

There must not be multiple competing application data sources unless explicitly required by the architecture.

If multiple databases are intentionally required, their responsibilities must be explicitly documented.

---

# 8. Step 3 — Standardize Database Configuration

Database configuration must be centralized.

### Tasks

* Identify the database connection configuration.
* Remove confirmed duplicate configuration definitions.
* Standardize configuration naming.
* Ensure secrets are provided through the approved configuration mechanism.
* Prevent hard-coded credentials.
* Ensure database configuration can differ between environments without changing application code.
* Document required database configuration.

### Expected Result

Application components should obtain database configuration through the established configuration layer rather than defining their own connection settings.

---

# 9. Step 4 — Standardize Connection and Session Management

Database connections and sessions must have predictable lifecycle management.

### Tasks

* Identify where database connections are created.
* Identify where sessions/clients are created.
* Identify how sessions are closed.
* Identify connection cleanup behavior.
* Identify connection pooling behavior if applicable.
* Remove unnecessary connection creation.
* Ensure services do not independently initialize competing database clients.

### Expected Logical Flow

```text
Application
    ↓
Database Configuration
    ↓
Database Initialization
    ↓
Managed Connection / Session
    ↓
Data Access Layer
```

The exact connection/session mechanism depends on the confirmed project technology.

---

# 10. Step 5 — Establish Data Access Boundary

Database operations should have a clear ownership boundary.

### Recommended Boundary

```text
API / Workflow
      ↓
Service
      ↓
Repository / Data Access
      ↓
Database
```

### Tasks

* Identify services directly executing database queries.
* Identify workflows directly accessing the database.
* Identify API handlers directly accessing the database.
* Move database operations into the approved data-access boundary where appropriate.
* Keep business rules in the service/workflow layer.
* Keep persistence logic in the data-access layer.

### Important Rule

Do not blindly create repositories for every function.

A repository/data-access abstraction should exist where it provides a meaningful boundary between application logic and persistence.

---

# 11. Step 6 — Unify Models and Entities

The database model must have one authoritative representation within the backend.

### Tasks

* Identify duplicate models representing the same database entity.
* Identify inconsistent field names.
* Identify inconsistent types.
* Identify unused models.
* Identify models that do not match the actual database structure.
* Identify conflicting representations between services.

### Expected Result

Each important persisted entity should have a clear and authoritative representation.

Any intentionally different representation, such as an API response model or workflow state object, must remain conceptually separate from the persistence model.

---

# 12. Step 7 — Standardize CRUD and Query Operations

Database operations should follow a consistent pattern.

### Operations

Where applicable:

```text
Create
Read
Update
Delete
Query
Existence Check
State Update
```

### Tasks

* Identify duplicated CRUD operations.
* Identify repeated query logic.
* Consolidate confirmed duplicates.
* Standardize query responsibilities.
* Prevent business rules from being hidden inside low-level persistence functions.
* Ensure query functions return predictable results.

### Important Rule

Do not combine unrelated business logic into the database layer merely to reduce the number of files or functions.

---

# 13. Step 8 — Define Transaction Boundaries

Database changes must have clear transaction ownership.

### Tasks

Identify operations that require atomicity.

Examples may include:

```text
Read State
    ↓
Validate State
    ↓
Update State
```

or:

```text
Create Record
    ↓
Create Related Record
```

Where multiple database operations must succeed or fail together, the transaction boundary must be explicit.

### Rules

* Avoid unnecessary long-running transactions.
* Avoid committing from multiple unrelated layers for one logical operation.
* Keep transaction ownership predictable.
* Roll back failed transactions appropriately.

The exact transaction mechanism must follow the database technology used by the project.

---

# 14. Step 9 — Handle Database Errors Consistently

Database failures must be handled according to the error architecture defined in:

`10_Security_And_Error_Handling.md`

### Identify

* Connection failures
* Timeout failures
* Query failures
* Constraint violations
* Missing records
* Transaction failures
* Initialization failures
* Configuration failures

### Expected Flow

```text
Database Error
      ↓
Data Access Layer
      ↓
Appropriate Error Representation
      ↓
Service / Workflow
      ↓
Logging / Response
```

Database implementation details should not unnecessarily leak through API responses or workflow-level error messages.

---

# 15. Step 10 — Remove Confirmed Duplicate Implementations

After the unified database architecture is established, remove only implementations confirmed to be obsolete.

### Candidates

* Duplicate database clients
* Duplicate session factories
* Duplicate repositories
* Duplicate model definitions
* Legacy database initialization
* Unused query modules
* Obsolete configuration

### Safety Rule

Do not delete a database implementation merely because it looks unused.

Before removal:

1. Search for references.
2. Verify runtime usage.
3. Verify test usage.
4. Confirm replacement behavior.
5. Run regression tests.

---

# 16. Step 11 — Update Services and Workflow Integration

Existing services and workflow components must use the unified database layer.

### Tasks

* Identify services using old database access paths.
* Replace confirmed obsolete access paths.
* Ensure workflow nodes use the approved service/data-access boundary.
* Remove direct database access from workflow components where the architecture requires service-level access.
* Verify database state changes remain correct.

### Target Flow

```text
Workflow Node
     ↓
Service
     ↓
Repository / Data Access
     ↓
Unified Database
```

The exact boundary should follow the architecture established in the main SDD.

---

# 17. Step 12 — Database Testing

The unified database layer must be independently testable.

### Test Areas

#### Connection Tests

Verify:

* Configuration is valid.
* Database initialization works.
* Connection/session lifecycle works.

#### Data Access Tests

Verify:

* Create operations
* Read operations
* Update operations
* Delete operations
* Queries
* Missing records
* Invalid input

#### Transaction Tests

Verify:

* Successful transaction
* Rollback behavior
* Partial failure behavior

#### Service Integration Tests

Verify that services correctly interact with the unified database layer.

#### Workflow Integration Tests

Where applicable, verify that workflow operations correctly read and modify persistent state.

Testing must remain aligned with:

`12_Backend_Testing_Strategy.md`

---

# 18. Step 13 — Data Integrity Validation

After unification, verify that existing application data remains logically consistent.

### Validation Areas

* Entity relationships
* Required fields
* Unique constraints
* Foreign-key relationships where applicable
* Status/state fields
* Identifiers
* Timestamps
* Payment-related state
* Reminder-related state

The exact fields and relationships must come from the confirmed project schema.

No new fields should be invented solely for this phase.

---

# 19. Step 14 — Migration Safety

If the existing implementation requires schema or data migration, the migration must be treated as an explicit operation.

### Migration Requirements

Any migration should define:

* Current state
* Target state
* Migration steps
* Data transformation requirements
* Rollback strategy
* Validation strategy

### Important Rule

Do not perform destructive database changes without first establishing:

1. A verified backup or recovery strategy.
2. A tested migration path.
3. Data validation.
4. Rollback/recovery procedures.

If no schema migration is required, this section should remain documented as not applicable.

---

# 20. Phase 2 Deliverables

The following should exist before Phase 2 is considered complete.

## Code

* Unified database configuration
* Unified database initialization
* Consistent connection/session management
* Defined data-access boundary
* Consolidated confirmed duplicate implementations
* Consistent model/entity usage
* Updated services
* Updated workflow integration where required
* Database error handling
* Database tests

## Documentation

* Database source of truth
* Database access architecture
* Current-to-target database mapping
* Known database technical debt
* Migration documentation if required
* Deferred database issues

## Validation

* Application can initialize the unified database layer.
* Database operations execute through the approved access path.
* Critical services can access required data.
* Workflow components can access required persistent state where supported.
* Database tests pass.
* Regression tests pass.
* No known critical duplicate database path remains without documented justification.

---

# 21. Phase 2 Exit Criteria

Phase 2 is complete only when all applicable criteria are satisfied:

* [ ] A single authoritative application database source of truth is established.
* [ ] Database configuration is centralized.
* [ ] Database connection/session management is consistent.
* [ ] Current database access points have been reviewed.
* [ ] The approved data-access boundary is established.
* [ ] Critical services use the unified database access path.
* [ ] Workflow components use the correct service/data-access boundary.
* [ ] Duplicate database implementations have been removed or explicitly justified.
* [ ] Database models/entities have a clear authoritative representation.
* [ ] Transaction boundaries are defined where required.
* [ ] Database errors follow the established error-handling architecture.
* [ ] Database tests pass.
* [ ] Relevant regression tests pass.
* [ ] Data integrity has been validated.
* [ ] Required migration work has been completed and validated, or confirmed unnecessary.
* [ ] Phase 3 prerequisites are satisfied.

---

# 22. Phase 2 Risks

| Risk                                             | Impact   | Mitigation                                                  |
| ------------------------------------------------ | -------- | ----------------------------------------------------------- |
| Removing an active database implementation       | High     | Verify references and runtime usage before removal          |
| Data loss during migration                       | Critical | Use validated migration and recovery procedures             |
| Inconsistent models                              | High     | Establish one authoritative persistence representation      |
| Multiple databases remain active unintentionally | High     | Define a single source of truth                             |
| Services bypass the data-access layer            | Medium   | Review database access paths                                |
| Transaction boundaries remain unclear            | High     | Define transaction ownership explicitly                     |
| Database refactoring breaks workflow behavior    | High     | Run service and workflow regression tests                   |
| Over-engineering the repository layer            | Medium   | Create abstractions only where they provide a real boundary |

---

# 23. Dependencies on Other SDD Documents

Phase 2 must remain aligned with:

* `00_SDD_Master.md`
* `01_Current_System_Architecture.md`
* `02_Target_Backend_Architecture.md`
* `03_Database_Wiring.md`
* `04_API_And_Service_Layer.md`
* `05_Event_And_Pipeline_Architecture.md`
* `06_WorkflowRunner_Architecture.md`
* `07_LangGraph_Integration.md`
* `10_Security_And_Error_Handling.md`
* `11_Observability_And_Logging.md`
* `12_Backend_Testing_Strategy.md`
* `phases/Phase_1_Stabilization.md`

These documents define the architectural constraints and implementation context for database unification.

---

# 24. Transition to Phase 3

After Phase 2 has passed its exit criteria, implementation can proceed to:

**Phase 3 — Live Data Wiring**

Phase 3 will connect the stabilized application and unified database layer to the live data flow required by the Rent Reminder Workflow.

Phase 3 must build on the unified database access architecture established here rather than introducing another independent data-access path.
