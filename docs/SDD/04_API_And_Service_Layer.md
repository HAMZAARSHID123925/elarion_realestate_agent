# 04 — API and Service Layer

> **Document Path:** `docs/SDD/04_API_And_Service_Layer.md`
> **Version:** 2.0 (Project-Wide Multi-Workflow API Architecture)
> **Status:** Active
> **Audience:** Developers, AI Coding Agents, Reviewers

---

## 1. Document Purpose

This document defines the unified API and application service architecture for the **Elarion Real Estate Agent Platform**.

The API layer is a thin interface boundary that validates incoming HTTP requests, coordinates with domain application services, triggers LangGraph workflows where required via the WorkflowRunner/Pipeline supervisor, and returns standardized JSON responses.

---

## 2. Target API Architecture

```text
                               HTTP Request
                                    ↓
                       FastAPI Server (app/server.py)
                                    ↓
                       Request Validation (Pydantic)
                                    ↓
        ┌───────────────────────────┴───────────────────────────┐
        ▼                                                       ▼
 [ Resource Routers ]                                 [ Workflow & Pipeline Routers ]
 • Health (/health, /ready)                           • Rent Reminder Scan & Evaluate
 • Tenants (/api/v1/tenants)                          • Lease Expiry & Renewal Scans
 • Properties (/api/v1/properties)                    • Master Pipeline Message (/api/v1/pipeline/message)
 • Maintenance (/api/v1/maintenance/tickets)          • Maintenance Approval Resumption
        ↓                                                       ↓
 [ Application Service Layer ]                        [ Master Pipeline / Department Nodes ]
 • TenantRepository                                   • Layer 2 Orchestrator Graph
 • LeaseExpiryService / RenewalReminderService        • Layer 3 Domain Subgraphs
 • Ticket / Property Repositories                     • Persistent Checkpointer
        └───────────────────────────┬───────────────────────────┘
                                    ↓
                        Unified PostgreSQL Database
```

---

## 3. API Endpoints Map

### 3.1 Health & Operational Endpoints
| Method | Endpoint | Purpose | Response |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness check (process running) | `{"status": "healthy", "timestamp": "..."}` |
| `GET` | `/ready` | Readiness check (probes PostgreSQL database connectivity) | `{"status": "ready", "database": "connected"}` |

### 3.2 Tenant Resource Endpoints
| Method | Endpoint | Purpose | Response |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/tenants` | List tenants with optional overdue filter (`overdue_only=true`) | `[TenantSummaryResponse]` |
| `GET` | `/api/v1/tenants/{tenant_id}` | Retrieve single tenant profile and rent state | `TenantDetailResponse` |
| `POST` | `/api/v1/tenants/{tenant_id}/hold` | Set or clear manual hold override (`{"manual_hold": true}`) | `{"tenant_id": "...", "manual_hold": true}` |

### 3.3 Property Resource Endpoints
| Method | Endpoint | Purpose | Response |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/properties` | Search property listings with city, type, and price filters | `[PropertyResponse]` |
| `GET` | `/api/v1/properties/{property_id}` | Retrieve property details and associated units | `PropertyDetailResponse` |

### 3.4 Maintenance Ticket Endpoints
| Method | Endpoint | Purpose | Response |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/maintenance/tickets` | List maintenance tickets (filter by status, urgency) | `[TicketSummaryResponse]` |
| `POST` | `/api/v1/maintenance/tickets` | Submit new maintenance ticket directly | `TicketCreatedResponse` |
| `GET` | `/api/v1/maintenance/tickets/{ticket_id}` | Retrieve ticket details, assigned vendor, and status log | `TicketDetailResponse` |

### 3.5 Workflow Execution Endpoints
| Method | Endpoint | Purpose | Response |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/workflows/rent-reminder/run` | Execute daily batch rent reminder scan | `RentReminderScanSummary` |
| `POST` | `/api/v1/workflows/rent-reminder/evaluate` | Evaluate and execute reminder rules for a single tenant | `RentReminderExecutionResult` |
| `POST` | `/api/v1/workflows/lease-expiry/scan` | Execute daily lease expiry window scan (90/60/30/7 days) | `LeaseExpiryScanSummary` |
| `POST` | `/api/v1/workflows/renewal-reminder/scan` | Execute daily renewal reminder stage dispatch scan | `RenewalReminderScanSummary` |

### 3.6 Master Pipeline Ingestion Endpoint
| Method | Endpoint | Purpose | Response |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/pipeline/message` | Ingest normalized message (`UnifiedRequest`) across channels | `UnifiedResponse` |

---

## 4. Request and Response Contracts

### 4.1 Request Validation Rules
* Requests must be validated at the boundary via Pydantic models.
* Malformed JSON or invalid data types immediately return `422 Unprocessable Entity` with field-level details.
* Unknown resource identifiers return `404 Not Found`.

### 4.2 Error Response Format
All API errors return consistent JSON envelopes:
```json
{
  "error": "RESOURCE_NOT_FOUND",
  "message": "Tenant with ID 'T-999' does not exist.",
  "status_code": 404,
  "timestamp": "2026-08-17T05:00:00Z"
}
```

---

## 5. Service & Data Access Boundary Rules

1. **Zero SQL in Route Handlers**: Route functions must never construct SQL strings or import `psycopg` directly.
2. **Delegation to Repositories & Services**:
   - Tenant operations delegate to `TenantRepository`.
   - Lease expiry operations delegate to `LeaseExpiryService`.
   - Renewal reminders delegate to `RenewalReminderService`.
   - Master pipeline message processing delegates to `handle_request()`.
3. **Transactional Safety**: State modifications must be atomic and update `updated_at` timestamps.