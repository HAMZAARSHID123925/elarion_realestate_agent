# Phase 4 — API Layer

## 1. Purpose

The purpose of Phase 4 is to establish the backend API layer on top of the stabilized services, unified database architecture, and live data wiring completed in the previous phases.

Phase 1 stabilized the backend.

Phase 2 established the unified database access architecture.

Phase 3 connected the workflow to live application data.

Phase 4 exposes the required backend capabilities through a consistent API boundary.

The API layer must provide a clear interface for frontend applications, external clients, internal systems, and approved integration channels without duplicating business logic or database logic.

---

# 2. Phase Objective

The primary objectives of this phase are:

1. Establish the approved API architecture.
2. Define clear API boundaries.
3. Expose required backend capabilities through APIs.
4. Keep business logic inside services/workflows.
5. Keep database access inside the approved data-access layer.
6. Implement consistent request validation.
7. Implement consistent response structures.
8. Implement consistent API error handling.
9. Establish API-level authentication and authorization boundaries where required.
10. Provide health and operational endpoints where appropriate.
11. Integrate API requests with the existing WorkflowRunner and service layer.
12. Prepare the backend API for scheduling and alerting work in Phase 5.

---

# 3. Scope

## In Scope

Phase 4 covers:

* API application structure
* API routing
* Request validation
* Response models
* Service integration
* Workflow triggering through API where required
* API error handling
* Authentication/authorization boundaries where applicable
* Health/readiness endpoints
* API logging
* API testing
* API documentation
* API-to-service integration

## Out of Scope

The following are not primary objectives of Phase 4:

* Database redesign
* New database access paths
* Major workflow redesign
* Background scheduler implementation
* Reminder scheduling engine
* Alerting infrastructure
* New external provider architecture
* Production deployment infrastructure
* Full production hardening

These concerns belong to the appropriate existing SDD documents and later phases.

---

# 4. Preconditions

Phase 4 must begin only after:

* Phase 1 stabilization is complete.
* Phase 2 database unification is complete.
* Phase 3 live data wiring is complete.
* Services have stable interfaces.
* Workflow execution can operate using live application data.
* Database access occurs through the unified data-access layer.

The API layer must be built on top of these existing components.

---

# 5. API Architecture Principle

The API layer is an interface boundary, not the location of business logic.

The intended flow is:

```text
Client
  ↓
API Route
  ↓
Request Validation
  ↓
Service Layer
  ↓
WorkflowRunner / Business Logic
  ↓
Data Access Layer
  ↓
Database
```

For operations that do not require workflow execution:

```text
Client
  ↓
API Route
  ↓
Request Validation
  ↓
Service Layer
  ↓
Data Access Layer
  ↓
Database
```

The API must not bypass the service/data-access architecture.

---

# 6. Step 1 — Inventory Existing API Surface

Before adding or changing endpoints, inspect the current backend.

### Tasks

Identify:

* Existing API application
* Existing routers
* Existing endpoints
* Existing request models
* Existing response models
* Existing middleware
* Existing authentication mechanisms
* Existing error handlers
* Existing health endpoints
* Existing API tests
* Existing documentation

### Deliverable

Create a clear map:

```text
API Application
      ↓
Routers
      ↓
Endpoints
      ↓
Services
      ↓
Workflow / Data Access
```

Existing endpoints must be preserved unless they are confirmed obsolete or incompatible with the approved architecture.

---

# 7. Step 2 — Define API Boundaries

Each API endpoint must have a clear responsibility.

### An endpoint should generally:

1. Receive the request.
2. Validate the request.
3. Authenticate/authorize where required.
4. Call the appropriate service.
5. Convert the service result into the appropriate response.
6. Return the response.
7. Handle expected errors consistently.

### An endpoint should not:

* Contain complex business rules.
* Directly execute database queries.
* Create independent database connections.
* Implement workflow state machines.
* Call external providers directly unless explicitly defined as an API responsibility.
* Duplicate service logic.

---

# 8. Step 3 — Define Endpoint Categories

The exact endpoint list must be based on confirmed application requirements.

Possible categories include:

```text
Health / Readiness
      ↓
Resource APIs
      ↓
Workflow APIs
      ↓
Operational APIs
```

### Health / Readiness

Used to determine whether the backend is operational.

Examples may include:

```text
GET /health
GET /ready
```

The exact paths must follow the project's existing API conventions.

### Resource APIs

Used for retrieving or modifying application resources through the service layer.

### Workflow APIs

Used where an external client needs to trigger or interact with an approved workflow.

### Operational APIs

Used for approved operational actions where required by the architecture.

No endpoint should be created merely for the sake of increasing API coverage.

---

# 9. Step 4 — Define Request Models

API requests must have explicit validation.

### Tasks

* Identify required request fields.
* Identify optional fields.
* Identify data types.
* Identify allowed values.
* Identify field constraints.
* Reject malformed requests.
* Prevent unexpected input from reaching business logic.

### Principle

Request validation belongs at the API boundary.

Business validation remains in the service/workflow layer.

Therefore:

```text
API Validation
    ↓
"Is this request structurally valid?"
```

while:

```text
Service / Workflow Validation
    ↓
"Is this operation valid according to business rules?"
```

These responsibilities must remain separate.

---

# 10. Step 5 — Define Response Models

API responses must be predictable and consistent.

### Tasks

* Define response structures.
* Define success responses.
* Define resource responses.
* Define operation responses.
* Define error responses.
* Avoid exposing internal database models directly.
* Avoid exposing internal workflow state unnecessarily.

### Principle

Persistence models and API response models should not automatically be treated as the same object.

The API should expose only the information required by the client.

---

# 11. Step 6 — Integrate APIs with Services

API handlers should call the appropriate service layer.

Target structure:

```text
API Route
    ↓
Service
    ↓
Data Access / Workflow
```

### Tasks

* Identify service methods required by each endpoint.
* Reuse existing services where possible.
* Add service methods only when a real capability is required.
* Prevent business logic duplication inside routes.
* Ensure services remain independently testable.

### Example

```text
POST /workflow/execute
        ↓
Workflow Service
        ↓
WorkflowRunner
        ↓
Rent Reminder Workflow
```

The exact endpoint path must follow the final API design.

---

# 12. Step 7 — Integrate Workflow APIs

Where an API is responsible for triggering a workflow, it must use the established WorkflowRunner architecture.

The target flow is:

```text
API Request
    ↓
Request Validation
    ↓
Workflow Service
    ↓
WorkflowRunner
    ↓
LangGraph / Workflow
    ↓
Result
    ↓
API Response
```

The API must not directly manipulate workflow nodes.

Workflow orchestration remains the responsibility of the WorkflowRunner and workflow architecture defined in:

`06_WorkflowRunner_Architecture.md`

and:

`07_LangGraph_Integration.md`

---

# 13. Step 8 — Handle Workflow Execution Results

API responses should represent workflow outcomes at an appropriate abstraction level.

Possible result categories may include:

```text
Success
Completed
Rejected
Validation Failure
Business Failure
Temporary Failure
Internal Failure
```

The exact status mapping must follow the established API and error architecture.

Internal workflow implementation details should not unnecessarily be exposed to API clients.

---

# 14. Step 9 — API Error Handling

API errors must follow:

`10_Security_And_Error_Handling.md`

### Expected Flow

```text
Service / Workflow Error
        ↓
Error Classification
        ↓
API Error Handler
        ↓
Structured Response
```

### Error Categories

Where applicable:

* Invalid request
* Authentication failure
* Authorization failure
* Resource not found
* Business-rule violation
* Database failure
* Provider failure
* Workflow failure
* Unexpected internal error

The API should return stable, predictable error structures.

---

# 15. Step 10 — HTTP Status Code Strategy

HTTP status codes must be used consistently.

The exact mapping should follow the application's API conventions.

Typical categories include:

| Situation                         |        Typical Status |
| --------------------------------- | --------------------: |
| Successful read                   |                   200 |
| Successful creation               |                   201 |
| Successful operation with no body |                   204 |
| Invalid request                   |                   400 |
| Authentication required/failed    |                   401 |
| Permission denied                 |                   403 |
| Resource not found                |                   404 |
| Conflict                          |                   409 |
| Validation failure                |  422 where applicable |
| Unexpected server failure         |                   500 |
| Temporary dependency failure      | 5xx where appropriate |

The final status code for each endpoint must be documented rather than decided inconsistently across individual routes.

---

# 16. Step 11 — Authentication and Authorization

API access must respect the security architecture defined in:

`10_Security_And_Error_Handling.md`

### Tasks

* Identify endpoints requiring authentication.
* Identify endpoints that may remain publicly accessible.
* Identify authorization requirements.
* Validate credentials/tokens using the approved mechanism.
* Prevent unauthorized workflow execution.
* Prevent unauthorized access to tenant/property/payment information.
* Avoid exposing authentication secrets through logs or responses.

The exact authentication technology must follow the confirmed project architecture.

---

# 17. Step 12 — Health and Readiness Endpoints

The backend should expose operational health information where required.

### Health

A health endpoint should provide a lightweight indication that the application process is functioning.

### Readiness

A readiness endpoint should indicate whether the application is ready to serve requests according to the defined dependency requirements.

The readiness design must consider required dependencies such as:

```text
Application
   ↓
Configuration
   ↓
Database
   ↓
Required Dependencies
```

Only dependencies actually required by the application should be included.

---

# 18. Step 13 — API Dependency Management

API routes must obtain their required dependencies through the established application architecture.

### Tasks

* Standardize service injection.
* Standardize database session/client injection where applicable.
* Prevent route-level creation of global resources.
* Ensure request-scoped resources are properly cleaned up.
* Avoid hidden shared mutable state.

The exact dependency-injection mechanism must follow the project's framework and architecture.

---

# 19. Step 14 — API Logging

API activity must be observable without exposing sensitive information.

Relevant events should include, where appropriate:

* Request received
* Endpoint invoked
* Request outcome
* Response status
* Execution duration
* Service/workflow failure
* Dependency failure

Do not log:

* Passwords
* API keys
* Authentication tokens
* Sensitive payment information
* Unnecessary tenant information

Logging must follow:

`11_Observability_And_Logging.md`

---

# 20. Step 15 — API Documentation

The API surface must be documented.

Documentation should include:

* Endpoint
* HTTP method
* Purpose
* Authentication requirement
* Request schema
* Response schema
* Error responses
* Important validation rules

If the framework provides automatic API documentation, it should be kept aligned with the actual implementation.

### Rule

API documentation must represent implemented behavior.

Do not document endpoints that do not exist.

---

# 21. Step 16 — API Versioning

API versioning should be introduced only if required by the project architecture or external compatibility requirements.

If versioning is required, establish a consistent strategy such as:

```text
/api/v1/...
```

The exact versioning strategy must be documented before multiple incompatible API contracts are introduced.

Avoid unnecessary versioning complexity during the initial implementation.

---

# 22. Step 17 — API Testing

Phase 4 requires API-level testing.

## Request Validation Tests

Verify:

* Valid requests
* Missing required fields
* Invalid field types
* Invalid values
* Unexpected input

## Authentication Tests

Verify:

* Valid credentials
* Missing credentials
* Invalid credentials
* Unauthorized access

## Service Integration Tests

Verify:

```text
API
 ↓
Service
 ↓
Expected Result
```

## Workflow API Tests

Verify:

```text
API
 ↓
Workflow Service
 ↓
WorkflowRunner
 ↓
Workflow
 ↓
Expected Result
```

## Error Tests

Verify:

* Not found
* Validation errors
* Business errors
* Database failures
* Workflow failures
* Provider failures where applicable
* Unexpected errors

## Health Tests

Verify:

* Health endpoint
* Readiness endpoint
* Dependency failure behavior where applicable

Testing must remain aligned with:

`12_Backend_Testing_Strategy.md`

---

# 23. Step 18 — API Integration with Live Data

The API must use the live data wiring established in Phase 3.

The intended flow is:

```text
Client
  ↓
API
  ↓
Service
  ↓
Unified Database / Workflow
  ↓
Live Application State
  ↓
Response
```

The API must not introduce:

* Mock runtime data
* Separate database clients
* Duplicate persistence logic
* Independent workflow state
* Hard-coded business decisions

---

# 24. Step 19 — API Performance Baseline

Phase 4 should establish a basic performance baseline without prematurely optimizing the system.

### Measure where useful:

* Request duration
* Database query duration
* Workflow execution duration
* External dependency duration
* Error frequency

The purpose is to identify obvious performance problems.

Detailed production optimization belongs to the hardening stage.

---

# 25. Step 20 — Regression Validation

After API implementation, validate the complete backend.

### Validate

* Application startup
* Database initialization
* Service behavior
* Workflow execution
* Live data wiring
* Existing tests
* Database tests
* Service tests
* Workflow tests
* API tests
* Error handling
* Logging

API implementation must not break existing non-API execution paths.

---

# 26. Phase 4 Deliverables

## Code

* API application structure
* Required routers
* Required endpoints
* Request validation
* Response models
* Service integration
* Workflow integration where required
* Error handlers
* Authentication/authorization boundaries where required
* Health/readiness endpoints where required
* API logging
* API tests

## Documentation

* API endpoint documentation
* Request/response contracts
* Error response contract
* Authentication requirements
* API versioning strategy if required

## Validation

* API endpoints work with live application data.
* API requests are validated.
* API responses are consistent.
* Business logic remains outside route handlers.
* Database access remains outside route handlers.
* Workflow execution uses the established WorkflowRunner.
* API errors are handled consistently.
* Authentication/authorization works where required.
* API tests pass.
* Regression tests pass.

---

# 27. Phase 4 Exit Criteria

Phase 4 is complete only when all applicable criteria are satisfied:

* [ ] API architecture is clearly defined.
* [ ] Required endpoints are implemented.
* [ ] Request validation is implemented.
* [ ] Response contracts are defined.
* [ ] API routes use the service layer.
* [ ] API routes do not contain duplicated business logic.
* [ ] API routes do not directly bypass the data-access architecture.
* [ ] Workflow-triggering APIs use the WorkflowRunner architecture.
* [ ] API errors follow the established error-handling strategy.
* [ ] Authentication/authorization requirements are implemented where applicable.
* [ ] Health/readiness endpoints are implemented where required.
* [ ] API logging follows the observability architecture.
* [ ] API documentation reflects the actual implementation.
* [ ] API tests pass.
* [ ] Existing backend regression tests pass.
* [ ] Live data is correctly exposed through approved service/API boundaries.
* [ ] Phase 5 prerequisites are satisfied.

---

# 28. Phase 4 Risks

| Risk                                     | Impact      | Mitigation                                                         |
| ---------------------------------------- | ----------- | ------------------------------------------------------------------ |
| Business logic placed inside API routes  | High        | Keep business logic in services/workflows                          |
| API directly accesses database           | High        | Enforce service/data-access boundaries                             |
| API duplicates workflow logic            | High        | Use WorkflowRunner                                                 |
| Inconsistent response formats            | Medium      | Define response contracts                                          |
| Sensitive data exposed through APIs      | Critical    | Apply security and authorization rules                             |
| Unauthorized workflow execution          | Critical    | Enforce authentication/authorization                               |
| API contract differs from implementation | Medium      | Keep documentation synchronized                                    |
| API changes break existing clients       | High        | Use explicit compatibility/versioning strategy where required      |
| Slow workflow blocks API requests        | Medium/High | Measure execution duration and follow the approved execution model |
| Poor error mapping                       | Medium      | Centralize API error handling                                      |

---

# 29. Dependencies on Other SDD Documents

Phase 4 must remain aligned with:

* `00_SDD_Master.md`
* `02_Target_Backend_Architecture.md`
* `03_Database_Wiring.md`
* `04_API_And_Service_Layer.md`
* `05_Event_And_Pipeline_Architecture.md`
* `06_WorkflowRunner_Architecture.md`
* `07_LangGraph_Integration.md`
* `08_Integration_And_Provider_Layer.md`
* `10_Security_And_Error_Handling.md`
* `11_Observability_And_Logging.md`
* `12_Backend_Testing_Strategy.md`
* `phases/Phase_1_Stabilization.md`
* `phases/Phase_2_Database_Unification.md`
* `phases/Phase_3_Live_Data_Wiring.md`

Phase 4 must consume the services, database architecture, workflow architecture, and live data flow established by the previous phases.

It must not create parallel implementations of those layers.

---

# 30. Transition to Phase 5

After Phase 4 has passed its exit criteria, implementation can proceed to:

**Phase 5 — Scheduling and Alerting**

Phase 5 will build the background execution, reminder scheduling, retry behavior, and alerting mechanisms required to execute the Rent Reminder Workflow automatically.

Phase 5 must use the API, service, workflow, database, and provider boundaries established in the previous phases rather than creating independent execution paths.
