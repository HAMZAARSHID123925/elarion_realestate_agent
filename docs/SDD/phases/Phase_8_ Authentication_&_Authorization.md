
# Phase 8: Authentication & Authorization

**Project:** Elarion Real Estate Agent Platform  
**Phase:** 8  
**Status:** Planned  
**Primary Owner:** Backend Engineering  
**Dependency:** Phase 7 — Backend Completeness  
**Next Phase:** Phase 9 — API Production Hardening

---

# 1. Purpose

Phase 8 establishes secure authentication and authorization across the backend APIs required by the Elarion Real Estate Agent Platform dashboard.

The objective is to ensure that:

1. Only authenticated users can access protected dashboard functionality.
2. Users can only access resources and operations permitted by their role and permissions.
3. Every protected API endpoint has an explicit authorization policy.
4. Authentication and authorization are designed around the actual dashboard features and user roles.
5. The frontend team receives a clear authentication contract for Phase 10.
6. Existing backend workflows remain functional and secure.
7. No dashboard feature or required API is accidentally left unprotected or unnecessarily blocked.

---

# 2. Core Principle

Authentication and authorization MUST be designed from the actual dashboard requirements.

The implementation agent MUST NOT create a generic role/permission system without first inspecting:

```text
Dashboard documentation
        ↓
Dashboard features
        ↓
Backend API inventory
        ↓
Existing user/tenant/manager concepts
        ↓
Existing database schema
        ↓
Existing API routes
        ↓
Required access rules
````

Every protected endpoint must have a documented reason for:

* Who can access it.
* What they can do.
* What resources they can access.
* What operations they can perform.

---

# 3. Scope

Phase 8 covers:

1. Authentication architecture.
2. User identity.
3. Login/session/token flow.
4. Authentication middleware/dependencies.
5. Role model.
6. Permission model where required.
7. API endpoint protection.
8. Resource-level authorization where required.
9. Ownership/tenant boundaries where applicable.
10. Password/security handling where applicable.
11. Token/session expiration.
12. Authentication error handling.
13. Authorization error handling.
14. Security-related database changes.
15. Authentication tests.
16. Authorization tests.
17. Dashboard-specific access matrix.
18. Frontend authentication contract.

---

# 4. Dashboard-First Security Requirement

The dashboard is the primary consumer of the backend API.

Therefore, before implementing authorization, the agent MUST produce:

```text
Dashboard Feature
        ↓
API Endpoint
        ↓
Required User Role
        ↓
Required Permission
        ↓
Resource Access Rule
```

Example:

```text
Maintenance Dashboard
        ↓
GET /api/v1/maintenance
        ↓
Manager / Authorized Staff
        ↓
maintenance:read
        ↓
Only permitted property/portfolio resources
```

This is an example only.

The actual role and permission rules MUST be derived from the real dashboard requirements and existing project structure.

---

# 5. Mandatory Discovery Before Implementation

Before changing authentication code, inspect:

```text
docs/
docs/SDD/
dashboard documentation
langgraph_agent/app/
langgraph_agent/app/api/
database/
database/migrations/
tests/
```

The agent must identify:

* Existing user model.
* Existing tenant model.
* Existing manager concepts.
* Existing staff concepts.
* Existing authentication code.
* Existing authorization code.
* Existing API routers.
* Existing API endpoints.
* Existing database relationships.
* Existing dashboard roles if documented.
* Existing environment variables.
* Existing security configuration.

The agent must NOT assume that a user model or role model is missing until the repository has been inspected.

---

# 6. Authentication Model

The project must use one consistent authentication mechanism.

The implementation agent must first inspect the existing project architecture and then select the mechanism that fits it.

The chosen mechanism must define:

```text
Login
   ↓
Credential Verification
   ↓
Authentication Result
   ↓
Token / Session
   ↓
Protected API Request
   ↓
Identity Resolution
```

The final SDD implementation report must explicitly state:

* Authentication mechanism.
* Token/session mechanism.
* Token/session lifetime.
* Refresh behavior.
* Logout/revocation behavior.
* Password handling.
* Storage strategy.
* Frontend integration requirements.

Do not introduce multiple competing authentication mechanisms without a documented architectural requirement.

---

# 7. Authentication Endpoints

The authentication API must be derived from the dashboard requirements and existing architecture.

Potential endpoint categories include:

```text
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
```

These are examples and MUST NOT automatically be implemented.

The agent must determine the actual required endpoints.

For every authentication endpoint, document:

| Endpoint     | Method | Purpose                       | Authentication Required |
| ------------ | ------ | ----------------------------- | ----------------------- |
| Login        | POST   | Authenticate user             | No                      |
| Logout       | POST   | End authentication session    | Depends on mechanism    |
| Refresh      | POST   | Refresh authentication state  | Depends on mechanism    |
| Current User | GET    | Return authenticated identity | Yes                     |

Only required endpoints should be implemented.

---

# 8. User Identity

The backend must establish a canonical authenticated identity.

At minimum, determine:

```text
User ID
User role
Account status
Relevant ownership/organization context
```

Additional identity information must only be included when required by the dashboard.

The authenticated identity must be available to protected API handlers through the project's established dependency/service architecture.

---

# 9. Role Model

The role model must be based on the actual dashboard.

Possible roles MUST NOT be invented without evidence from the dashboard or project requirements.

The agent must identify the actual required roles.

For each role, document:

```text
Role
Purpose
Accessible Dashboard Areas
Allowed API Operations
Resource Scope
Restrictions
```

Example structure:

| Role   | Dashboard Areas | Read | Create | Update | Delete |
| ------ | --------------- | ---: | -----: | -----: | -----: |
| Role A | Feature X       |  Yes |    Yes |    Yes |     No |
| Role B | Feature X/Y     |  Yes |     No |    Yes |     No |

The final values must come from the actual dashboard requirements.

---

# 10. Permission Model

Use granular permissions only where the dashboard or application actually requires them.

Potential permission categories may include:

```text
properties:read
properties:create
properties:update
properties:delete

tenants:read
tenants:create
tenants:update

leases:read
leases:create
leases:update

maintenance:read
maintenance:create
maintenance:update
maintenance:escalate
```

These are examples.

The agent must not blindly create this exact permission list.

The final permission model must correspond to the actual API inventory produced during Phase 7.

---

# 11. API Authorization Matrix

A complete authorization matrix MUST be created.

Required format:

| Dashboard Feature | API Endpoint  | Method | Role | Permission | Resource Scope |
| ----------------- | ------------- | ------ | ---- | ---------- | -------------- |
| Feature           | `/api/v1/...` | GET    | Role | permission | Scope          |

Every protected Phase 7 endpoint must appear in this matrix.

The matrix must identify:

```text
Public
Authenticated
Role restricted
Permission restricted
Resource restricted
```

This matrix becomes the security contract for Phase 10 frontend integration.

---

# 12. Endpoint Protection

Every protected API endpoint must enforce authorization at the backend.

The frontend MUST NOT be treated as the security boundary.

Incorrect:

```text
Frontend hides button
        ↓
User cannot access feature
```

Correct:

```text
Frontend hides button
        ↓
AND
Backend verifies authorization
        ↓
Request allowed/denied
```

Even if a dashboard button is hidden, a direct API request must still be rejected when unauthorized.

---

# 13. Resource-Level Authorization

Where required, authorization must consider the specific resource.

Example:

```text
Authenticated Manager
        ↓
GET /api/v1/properties/{property_id}
        ↓
Is user allowed to access this property?
        ↓
YES → Return resource
NO  → Deny access
```

The agent must determine whether the project requires:

* Organization-level access.
* Property-level access.
* Portfolio-level access.
* Tenant-level access.
* Manager ownership.
* Administrative override.

Only applicable boundaries should be implemented.

---

# 14. Tenant / User Data Isolation

If the dashboard supports multiple organizations, managers, property portfolios, or tenant boundaries, the backend must prevent unauthorized cross-resource access.

Security must be enforced at the backend data-access boundary.

The implementation must prevent:

```text
User A
   ↓
Request resource belonging to User B
   ↓
Unauthorized data returned
```

Tests must explicitly verify cross-resource access denial where applicable.

---

# 15. Authentication Failure Responses

Authentication failures must use consistent API behavior.

Examples:

```text
Missing credentials
Invalid credentials
Expired authentication
Revoked authentication
Malformed token/session
```

The implementation must distinguish authentication failures from authorization failures.

Typical distinction:

```text
401
Unauthenticated / invalid authentication

403
Authenticated but not authorized
```

The project's established API error format must be used.

---

# 16. Password Security

If password-based authentication exists or is required by the dashboard:

Passwords MUST:

* Never be stored in plaintext.
* Never be logged.
* Never be returned by APIs.
* Use an appropriate password hashing mechanism.
* Be compared securely.
* Follow project security requirements.

Credentials must not appear in:

```text
Logs
API responses
Error messages
Dead-letter records
Telemetry
Audit records
```

---

# 17. Token / Session Security

If token-based authentication is used, define:

* Token lifetime.
* Refresh lifetime.
* Refresh behavior.
* Revocation strategy.
* Signing/verification mechanism.
* Secret management.
* Required claims.
* Expiration validation.

Secrets MUST come from environment/configuration management.

Never hardcode authentication secrets.

---

# 18. Frontend Authentication Contract

Phase 8 must produce a clear contract for the frontend team.

The documentation must specify:

```text
Login request
Login response
Authentication storage expectations
Authenticated request format
Current-user request
Logout behavior
Expired-session behavior
Unauthorized behavior
```

Example conceptual flow:

```text
Frontend
   ↓
POST /auth/login
   ↓
Backend
   ↓
Authentication result
   ↓
Frontend stores authentication state
   ↓
Frontend calls protected API
   ↓
Backend validates authentication
   ↓
Backend validates authorization
   ↓
Response
```

The exact implementation depends on the selected authentication mechanism.

---

# 19. Dashboard Feature Protection

The agent must explicitly audit every dashboard feature from Phase 7.

For example:

```text
Dashboard Overview
Properties
Tenants
Leases
Rent
Rent Reminders
Lease Expiry
Renewals
Maintenance
Notifications
Escalations
Documents
Jobs
Alerts
```

This list is a starting reference only.

The actual dashboard feature inventory from Phase 7 is authoritative.

For each feature:

```text
Feature
↓
API endpoints
↓
Authentication requirement
↓
Role requirement
↓
Permission requirement
↓
Resource scope
```

must be documented.

No dashboard feature may be silently ignored.

---

# 20. Background Jobs & Internal Services

Background jobs must be considered separately from user-facing APIs.

The agent must inspect:

```text
Phase 5 job scheduler
JobRunner
Job registry
Maintenance monitor
Dead-letter queue
Alert service
```

Determine:

* Which operations are internal.
* Which operations are user-triggered.
* Which job endpoints require administrative authorization.
* Which internal service calls must not be exposed publicly.

For example:

```text
POST /api/v1/jobs/{job_name}/run
```

must NOT remain unrestricted if it can trigger privileged background operations.

The appropriate access policy must be derived from the dashboard/admin requirements.

---

# 21. Audit Logging

Security-sensitive operations should be auditable where required.

Potential events:

```text
Login success
Login failure
Logout
Authorization failure
Sensitive resource modification
Administrative action
Manual job trigger
```

Only events required by the project's security and compliance needs should be recorded.

Sensitive credentials and tokens MUST NOT be logged.

---

# 22. Security Configuration

Review:

```text
Environment variables
Secrets
CORS
Authentication configuration
Token configuration
Database credentials
External provider credentials
```

Do not hardcode secrets.

Do not expose secrets through:

```text
API responses
Logs
Exceptions
Dead-letter records
Telemetry
```

Existing Phase 5 payload sanitization must remain intact.

---

# 23. Testing Requirements

Authentication tests must include:

### Login

```text
Valid credentials
Invalid credentials
Missing credentials
Disabled user where applicable
```

### Authentication

```text
Valid authentication
Expired authentication
Invalid authentication
Missing authentication
```

### Authorization

```text
Allowed role
Denied role
Allowed permission
Denied permission
```

### Resource Isolation

Where applicable:

```text
User A → User A resource → Allowed
User A → User B resource → Denied
```

### Protected APIs

Every protected dashboard API must have at least one authorization test.

### Internal Operations

Privileged operational endpoints must have authorization tests.

---

# 24. Regression Testing

All existing tests must continue to pass.

At minimum:

```text
Phase 1 tests
Phase 2 tests
Phase 3 tests
Phase 4 tests
Phase 5 tests
Phase 6 tests
Phase 7 tests
Phase 8 authentication tests
```

No regression is acceptable.

---

# 25. Required Deliverables

At the end of Phase 8, the agent must provide:

## 25.1 Authentication Architecture

Document:

* Authentication mechanism.
* Token/session mechanism.
* Login flow.
* Logout flow.
* Refresh flow if applicable.
* Current-user flow.

## 25.2 Role Inventory

List every implemented role and explain its dashboard purpose.

## 25.3 Permission Inventory

List every implemented permission and its associated dashboard/API feature.

## 25.4 Authorization Matrix

Provide the complete:

```text
Dashboard Feature
→ Endpoint
→ Method
→ Role
→ Permission
→ Resource Scope
```

mapping.

## 25.5 Changed Files

List all:

* Created files.
* Modified files.
* Deleted files, if any.

## 25.6 Database Changes

Document all migrations.

## 25.7 API Changes

List all authentication and authorization-related endpoints.

## 25.8 Test Results

Provide:

```text
Authentication tests:
Authorization tests:
Security tests:
Existing regression tests:
Total:
Passed:
Failed:
Warnings:
```

## 25.9 Frontend Authentication Contract

Provide exact instructions the frontend team needs for Phase 10.

---

# 26. Phase 8 Exit Criteria

Phase 8 is complete only when:

* [ ] Authentication architecture is implemented.
* [ ] Dashboard users can authenticate through the defined mechanism.
* [ ] Authenticated identity is available to protected APIs.
* [ ] Dashboard-specific roles are defined.
* [ ] Required permissions are defined.
* [ ] Authorization matrix is complete.
* [ ] All required protected APIs enforce authorization.
* [ ] Resource-level authorization is implemented where required.
* [ ] Cross-resource access is prevented where applicable.
* [ ] Authentication errors are consistent.
* [ ] Authorization errors are consistent.
* [ ] Passwords/secrets are protected.
* [ ] Tokens/sessions are securely handled.
* [ ] Privileged operational APIs are protected.
* [ ] Security-sensitive actions are audited where required.
* [ ] Authentication tests pass.
* [ ] Authorization tests pass.
* [ ] Existing regression suite passes.
* [ ] Frontend authentication contract is documented.
* [ ] No dashboard feature has been ignored during authorization design.

---

# 27. Explicit Non-Goals

Phase 8 does NOT include:

### Backend Feature Discovery

Handled by:

```text
Phase 7
```

### General API Hardening

Handled by:

```text
Phase 9
```

### Frontend API Integration

Handled by:

```text
Phase 10
```

### End-to-End Validation

Handled by:

```text
Phase 11
```

### Deployment

Handled by:

```text
Phase 12
```

---

# 28. Implementation Rules

The implementation agent MUST:

1. Inspect the existing repository before modifying authentication code.
2. Inspect the dashboard documentation before defining roles or permissions.
3. Use the Phase 7 API inventory as the security surface.
4. Protect every applicable dashboard API.
5. Never rely on frontend UI restrictions for security.
6. Never invent dashboard roles without evidence.
7. Never invent permissions without a real authorization requirement.
8. Never expose privileged internal operations unnecessarily.
9. Never hardcode credentials or secrets.
10. Never log passwords, tokens, API keys, or secrets.
11. Preserve existing domain workflows.
12. Preserve existing Phase 5 background-job security.
13. Add automated tests for authentication and authorization.
14. Run the complete regression suite.
15. Clearly document all assumptions.
16. If dashboard requirements are unclear, report the ambiguity instead of silently inventing behavior.
17. Do not begin frontend integration during this phase.

---

# 29. Final Phase Verdict

The final implementation report MUST contain:

```text
PHASE 8 STATUS:

COMPLETE
or
INCOMPLETE
```

If INCOMPLETE:

```text
Remaining blockers:
1.
2.
3.
```

If COMPLETE:

```text
Authentication:
[summary]

Authorization:
[summary]

Dashboard Coverage:
[summary]

Protected API Count:
[number]

Roles:
[list]

Permissions:
[list]

Security Tests:
[number]

Regression Tests:
[number]

Frontend Handoff:
[exact authentication/integration contract]
```

---

# 30. Phase Transition

Once Phase 8 is verified:

```text
Phase 7
Backend Completeness
        ↓
Phase 8
Authentication & Authorization
        ↓
Phase 9
API Production Hardening
        ↓
Backend Handoff
        ↓
Phase 10
Frontend ↔ Backend Integration
```

Phase 9 must not begin until the Phase 8 exit criteria and final security audit have been completed.

```
