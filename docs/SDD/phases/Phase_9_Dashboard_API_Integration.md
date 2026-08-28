# Phase 9: Dashboard API Integration & Backend Connectivity

## 1. Purpose

Phase 9 establishes the complete connection between the Elarion Real Estate Agent backend and the existing frontend/dashboard.

The goal is NOT to redesign the dashboard.

The goal is to connect the existing dashboard features to the backend APIs implemented in previous phases while preserving the dashboard's existing UI, workflows, terminology, and feature structure.

This phase should ensure that every dashboard feature that requires backend functionality has a clearly defined API contract and a working frontend-to-backend connection.

---

# 2. Primary Objectives

Phase 9 must accomplish the following:

1. Audit the existing dashboard feature structure.
2. Map every dashboard feature to its corresponding backend API.
3. Identify dashboard features that currently use mock/static data.
4. Replace applicable mock/static data with real backend API calls.
5. Connect dashboard actions to backend endpoints.
6. Connect dashboard tables, cards, metrics, filters, and detail views to real backend data.
7. Implement frontend API client/service boundaries.
8. Implement loading, success, empty, and error states.
9. Implement authentication-aware API communication.
10. Preserve existing dashboard UI and UX.
11. Ensure backend API contracts match frontend requirements.
12. Validate the complete frontend → API → service → database flow.

---

# 3. Critical Dashboard Rule

The existing dashboard is the source of truth for dashboard functionality.

Do NOT create arbitrary APIs simply because they appear useful.

Every dashboard API should exist for one of these reasons:

- An existing dashboard feature requires it.
- An existing dashboard action requires it.
- An existing dashboard data view requires it.
- An existing dashboard workflow requires it.
- A backend operation required by the dashboard has no existing endpoint.

The implementation must not ignore existing dashboard functionality.

---

# 4. Dashboard Feature → API Mapping

Create a complete mapping between dashboard features and backend endpoints.

The mapping must contain:

| Dashboard Feature | Dashboard Screen | User Action | Backend API | HTTP Method | Status |
|---|---|---|---|---|---|
| Dashboard Overview | Overview | View metrics | Existing/Required endpoint | GET | TBD |
| Properties | Properties | List properties | Existing/Required endpoint | GET | TBD |
| Property Details | Properties | View property | Existing/Required endpoint | GET | TBD |
| Tenants | Tenants | List tenants | Existing/Required endpoint | GET | TBD |
| Tenant Details | Tenants | View tenant | Existing/Required endpoint | GET | TBD |
| Leases | Leases | View leases | Existing/Required endpoint | GET | TBD |
| Rent Reminders | Rent/Rent Reminder | View reminder status | Existing/Required endpoint | GET | TBD |
| Rent Reminder Action | Rent/Rent Reminder | Trigger/send reminder | Existing/Required endpoint | POST | TBD |
| Lease Expiry | Lease Management | View expiry events | Existing/Required endpoint | GET | TBD |
| Renewal Reminders | Renewal | View renewal status | Existing/Required endpoint | GET | TBD |
| Maintenance | Maintenance | View tickets | Existing/Required endpoint | GET | TBD |
| Maintenance Details | Maintenance | View ticket | Existing/Required endpoint | GET | TBD |
| Maintenance Action | Maintenance | Update/escalate ticket | Existing/Required endpoint | PATCH/POST | TBD |
| Human Escalation | Escalations | View escalations | Existing/Required endpoint | GET | TBD |
| Background Jobs | Operations | View jobs | `/api/v1/jobs` | GET | Implemented |
| Job Trigger | Operations | Manually run job | `/api/v1/jobs/{job_name}/run` | POST | Implemented |
| Dead Letter | Operations | View failed jobs | `/api/v1/jobs/dead-letter` | GET | Implemented |
| Alerts | Operations | View alerts | `/api/v1/jobs/alerts` | GET | Implemented |

The exact mapping must be based on the actual dashboard implementation and actual backend routes.

Do not assume that an endpoint exists.

---

# 5. API Contract Audit

Before connecting the frontend, inspect every backend API.

For each endpoint document:

- Endpoint path
- HTTP method
- Authentication requirement
- Authorization requirement
- Request parameters
- Request body
- Response schema
- Error responses
- Pagination requirements
- Filtering requirements
- Sorting requirements
- Required frontend fields
- Database source
- Service/repository responsible

Example:

```text
GET /api/v1/maintenance/tickets

Authentication:
Required

Authorization:
Manager / Property Manager

Query Parameters:
status
priority
page
page_size

Response:
{
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
}

Frontend Usage:
Maintenance Dashboard → Ticket Table
````

---

# 6. Frontend API Client Architecture

Do not place raw HTTP requests throughout dashboard components.

Create a centralized frontend API layer.

Recommended structure:

```text
frontend/
│
├── src/
│   ├── api/
│   │   ├── client.*
│   │   ├── auth.*
│   │   ├── dashboard.*
│   │   ├── properties.*
│   │   ├── tenants.*
│   │   ├── leases.*
│   │   ├── rent.*
│   │   ├── maintenance.*
│   │   ├── renewal.*
│   │   ├── escalation.*
│   │   └── jobs.*
│   │
│   ├── hooks/
│   │   ├── useProperties.*
│   │   ├── useTenants.*
│   │   ├── useLeases.*
│   │   ├── useMaintenance.*
│   │   └── useJobs.*
│   │
│   └── ...
```

The exact structure must follow the existing frontend architecture.

Do not create duplicate API abstractions if an equivalent frontend service layer already exists.

---

# 7. Base API Client

Create or standardize a single API client responsible for:

* Backend base URL
* Authentication headers
* Request serialization
* Response parsing
* Error normalization
* Timeout handling
* Token handling
* Common headers

Example conceptual flow:

```text
Dashboard Component
        ↓
Frontend API Service
        ↓
Central API Client
        ↓
Authentication
        ↓
HTTP Request
        ↓
FastAPI Backend
        ↓
Router
        ↓
Service
        ↓
Repository
        ↓
PostgreSQL
```

---

# 8. Authentication Integration

The frontend must use the authentication mechanism implemented in previous phases.

The frontend must NOT:

* Store credentials insecurely.
* Hardcode tokens.
* Bypass authentication.
* Call protected endpoints without authentication.
* Implement a second independent authentication system.

Authentication flow:

```text
User
 ↓
Dashboard Login
 ↓
Authentication API
 ↓
Access Token / Session
 ↓
Frontend Auth State
 ↓
API Client
 ↓
Authorization Header / Session
 ↓
Protected Backend Endpoint
```

If authentication is session-cookie based, use the existing session mechanism.

If JWT-based, use the existing JWT implementation.

Do not introduce a new authentication mechanism unless the SDD explicitly requires it.

---

# 9. Dashboard Overview Integration

Connect the dashboard overview to real backend data.

Potential dashboard data includes:

* Total properties
* Occupied properties
* Vacant properties
* Active leases
* Rent status
* Pending rent reminders
* Lease expirations
* Open maintenance tickets
* Emergency maintenance tickets
* Pending renewals
* Human escalations
* Operational alerts

Only expose metrics that are actually supported by the existing dashboard requirements and backend data.

Do not fabricate metrics.

---

# 10. Property Management Integration

Connect the Properties dashboard to backend APIs.

Required operations depend on existing dashboard functionality:

```text
GET    /properties
GET    /properties/{id}
POST   /properties
PATCH  /properties/{id}
DELETE /properties/{id}
```

Only implement missing operations if the dashboard actually requires them.

Support:

* Property listing
* Property search
* Property filtering
* Property details
* Property status
* Tenant/lease relationships where applicable

---

# 11. Tenant Management Integration

Connect tenant-related dashboard screens to backend APIs.

Potential operations:

```text
GET   /tenants
GET   /tenants/{id}
POST  /tenants
PATCH /tenants/{id}
```

Dashboard should be able to display relevant tenant information without exposing sensitive data unnecessarily.

---

# 12. Lease Management Integration

Connect lease-related dashboard functionality.

Potential operations:

```text
GET /leases
GET /leases/{id}
```

Required dashboard information may include:

* Lease status
* Start date
* End date
* Tenant
* Property
* Rent amount
* Expiry status
* Renewal status

The frontend must consume the backend's canonical lease data.

---

# 13. Rent Reminder Integration

Connect the existing Rent Reminder dashboard functionality to the backend.

Dashboard should be capable of displaying:

* Rent status
* Reminder status
* Reminder history where supported
* Tenants requiring reminders
* Overdue rent
* Escalation status
* Reminder scan information

Potential actions:

```text
GET  /rent-reminders
GET  /rent-reminders/{id}
POST /rent-reminders/{id}/trigger
```

Exact routes must match the implemented backend API.

Do not create duplicate reminder logic in the frontend.

The frontend only requests actions.

Business rules remain in the backend.

---

# 14. Lease Expiry Integration

Connect lease expiry information to the dashboard.

Dashboard should consume:

* Upcoming expirations
* 90-day window
* 60-day window
* 30-day window
* 7-day window
* Expired leases
* Expiry event history

The backend remains responsible for expiry calculations.

The frontend only displays the resulting state.

---

# 15. Renewal Reminder Integration

Connect renewal reminder functionality.

Dashboard may display:

* Upcoming renewal stages
* 90-day reminders
* 60-day reminders
* 30-day reminders
* 7-day reminders
* Reminder status
* Tenant response
* Manager notification status

Do not duplicate renewal-stage calculations in frontend code.

---

# 16. Maintenance Dashboard Integration

Connect maintenance dashboard functionality.

Potential operations:

```text
GET   /maintenance/tickets
GET   /maintenance/tickets/{id}
POST  /maintenance/tickets
PATCH /maintenance/tickets/{id}
```

Dashboard should support existing features such as:

* Open tickets
* Assigned tickets
* Unassigned tickets
* Emergency tickets
* Standard tickets
* SLA status
* Escalation status
* Ticket details
* Ticket updates

SLA calculations remain backend responsibilities.

---

# 17. Human Escalation Integration

Connect escalation-related dashboard views.

Dashboard should display applicable:

* Escalated cases
* Reason
* Workflow
* Tenant/property
* Current status
* Created time
* Resolution status

Any escalation action must go through authenticated backend APIs.

---

# 18. Background Jobs Dashboard Integration

Connect the dashboard's operational/job monitoring UI to:

```text
GET  /api/v1/jobs
POST /api/v1/jobs/{job_name}/run
GET  /api/v1/jobs/dead-letter
GET  /api/v1/jobs/alerts
```

Dashboard should be able to display:

* Registered jobs
* Job status
* Schedule/cadence
* Last execution
* Execution duration
* Success/failure
* Dead-letter records
* Operational alerts

Manual job triggering must require the authorization rules established in the security phase.

---

# 19. Loading States

Every API-backed dashboard component must handle:

```text
Loading
   ↓
Request
   ↓
Success ──→ Render Data
   │
   ├──→ Empty State
   │
   └──→ Error State
```

No dashboard screen should remain blank without explanation while an API request is loading.

---

# 20. Error Handling

Normalize backend errors into user-friendly dashboard messages.

Example:

```text
Backend:
401 Unauthorized

Frontend:
"Your session has expired. Please sign in again."
```

```text
Backend:
403 Forbidden

Frontend:
"You do not have permission to perform this action."
```

```text
Backend:
404 Not Found

Frontend:
"The requested record could not be found."
```

```text
Backend:
500 Internal Server Error

Frontend:
"Something went wrong. Please try again."
```

Do not expose stack traces, database errors, credentials, SQL statements, or internal implementation details to dashboard users.

---

# 21. Pagination, Filtering & Search

Where backend endpoints support large datasets, dashboard tables must use server-side:

* Pagination
* Filtering
* Search
* Sorting

Do not load the entire database into the browser simply to perform filtering.

The API contract must define:

```text
page
page_size
search
status
sort_by
sort_order
```

Only implement parameters actually required by the dashboard.

---

# 22. API State Management

Use the existing frontend state-management/data-fetching architecture.

If the frontend already uses:

* React Query
* SWR
* Redux
* Zustand
* Context
* Custom hooks

continue using the existing architecture.

Do not introduce another state-management system without a documented requirement.

---

# 23. Mock Data Removal

Audit the frontend for:

* Hardcoded dashboard statistics
* Mock properties
* Mock tenants
* Mock leases
* Mock maintenance tickets
* Fake job data
* Static alerts
* Fake rent reminder data

For every mock dataset determine:

```text
MOCK DATA
   ↓
Is it required for UI-only development?
   ├── YES → Keep isolated from production API layer
   └── NO  → Replace with backend API
```

Never silently remove useful development fixtures without verifying their purpose.

---

# 24. Environment Configuration

Frontend backend configuration must use environment variables.

Example:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

or the equivalent configuration system used by the existing frontend.

Do not hardcode:

```text
http://localhost:8000
```

throughout frontend source files.

Production and development environments must be configurable independently.

---

# 25. CORS & Network Configuration

Verify:

```text
Frontend
   ↓
Backend URL
   ↓
CORS
   ↓
Authentication
   ↓
API
```

Backend CORS must allow only the configured frontend origins.

Do not use unrestricted:

```text
allow_origins=["*"]
```

for production authenticated APIs unless explicitly justified by the architecture.

---

# 26. API Contract Consistency

The frontend and backend must agree on:

* Field names
* Data types
* Nullability
* Enum values
* Date formats
* Error formats
* Pagination structure
* Authentication behavior

Example:

Backend:

```json
{
  "tenant_id": "123",
  "lease_end_date": "2026-09-30"
}
```

Frontend must not expect:

```json
{
  "tenantId": "123",
  "leaseEnd": "09/30/2026"
}
```

unless an explicit transformation layer exists.

---

# 27. Security Requirements

Before declaring Phase 9 complete:

* No API keys in frontend source code.
* No database credentials in frontend.
* No hardcoded authentication tokens.
* Protected endpoints require authentication.
* Mutating operations require authorization.
* Sensitive backend errors are not exposed.
* CORS is restricted.
* API requests use HTTPS in production.
* User permissions are respected by the backend.
* Frontend cannot bypass backend authorization.

---

# 28. Integration Testing

Create integration tests covering critical dashboard flows.

At minimum test:

### Authentication

```text
Login
→ Receive authentication state
→ Access protected dashboard API
```

### Properties

```text
Dashboard
→ Properties API
→ Backend
→ Database
→ Real property data
```

### Rent Reminder

```text
Dashboard
→ Rent Reminder API
→ Backend workflow
→ Database
→ Updated reminder state
→ Dashboard refresh
```

### Maintenance

```text
Dashboard
→ Maintenance API
→ Backend
→ Database
→ Updated ticket
→ Dashboard refresh
```

### Jobs

```text
Dashboard
→ GET /api/v1/jobs
→ Display jobs

Dashboard
→ POST /api/v1/jobs/{job_name}/run
→ Backend JobRunner
→ Job execution
→ Result
```

---

# 29. End-to-End Validation

Validate the complete architecture:

```text
┌─────────────────────┐
│      Dashboard      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Frontend API Layer │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Authentication/Auth │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      FastAPI        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Routers / Services  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Repositories     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    PostgreSQL       │
└─────────────────────┘
```

---

# 30. Phase 9 Deliverables

## Backend

* Verify all dashboard-required endpoints.
* Add only genuinely missing endpoints.
* Finalize API response schemas.
* Finalize authentication/authorization integration.
* Finalize CORS configuration.
* Verify pagination/filtering/search requirements.
* Verify API error contracts.

## Frontend

* Central API client.
* Feature-specific API services.
* Authentication integration.
* Dashboard API hooks/services.
* Real data integration.
* Loading states.
* Empty states.
* Error states.
* Mutation handling.
* Data refresh/invalidation.

## Documentation

Create:

```text
docs/SDD/
└── phases/
    └── Phase_9_Dashboard_API_Integration.md
```

Also maintain an API mapping document if required:

```text
docs/SDD/
└── 13_Dashboard_API_Mapping.md
```

---

# 31. Phase 9 Exit Criteria

Phase 9 is complete only when:

* [ ] Every dashboard feature has been audited.
* [ ] Every backend-dependent dashboard feature has an API mapping.
* [ ] Existing backend endpoints are reused wherever possible.
* [ ] Missing APIs are implemented only where required.
* [ ] Dashboard no longer depends on unnecessary mock data.
* [ ] Central frontend API client is implemented.
* [ ] Authentication is connected.
* [ ] Authorization is respected.
* [ ] Dashboard overview uses real backend data.
* [ ] Property data is connected.
* [ ] Tenant data is connected.
* [ ] Lease data is connected.
* [ ] Rent Reminder data/actions are connected.
* [ ] Lease Expiry data is connected.
* [ ] Renewal data is connected.
* [ ] Maintenance data/actions are connected.
* [ ] Human escalation data is connected.
* [ ] Background Jobs APIs are connected.
* [ ] Loading states are implemented.
* [ ] Empty states are implemented.
* [ ] Error states are implemented.
* [ ] CORS is correctly configured.
* [ ] Environment configuration is implemented.
* [ ] Critical frontend-backend flows pass integration testing.
* [ ] No sensitive credentials are exposed to the frontend.
* [ ] No unnecessary duplicate business logic exists in the frontend.
* [ ] Existing backend tests continue to pass.
* [ ] Dashboard integration tests pass.
* [ ] Complete frontend → backend → database flows are verified.

---

# 32. Important Implementation Rule

The development agent must inspect the actual frontend/dashboard before implementing Phase 9.

It must NOT assume:

* dashboard pages,
* component names,
* frontend framework,
* existing API client,
* state management,
* routes,
* mock data structure,
* authentication implementation,
* or endpoint names.

All implementation decisions must be based on the actual repository.

The agent must first produce a Dashboard → API Mapping Audit and only then implement the integration.

---

# 33. Phase 9 Completion Report

At the end of Phase 9, the development agent must provide:

1. Complete dashboard feature inventory.
2. Complete Dashboard → API mapping.
3. Existing endpoints reused.
4. New endpoints created.
5. Endpoints modified.
6. Frontend files created.
7. Frontend files modified.
8. Authentication integration details.
9. API client architecture.
10. Mock data removed/replaced.
11. Integration tests added.
12. Test results.
13. Remaining gaps.
14. Security issues, if any.
15. Final Phase 9 status.

The report must clearly distinguish between:

* Implemented
* Verified
* Partially implemented
* Not implemented
* Blocked

No functionality should be marked complete without evidence from the actual codebase and tests.

```
