# Phase 4 — Project-Wide API Layer

> **Document Path:** `docs/SDD/phases/Phase_4_API_Layer.md`
> **Status:** Active Target Phase
> **Scope:** Project-Wide (Maintenance, Rent Reminder, FAQ/Search, Lease Expiry/Renewal)

---

## 1. Purpose

The purpose of Phase 4 is to establish the unified backend API layer on top of the stabilized services, unified database architecture, and live data wiring across all four core workflow domains:
1. **Maintenance Workflow**
2. **Rent Reminder Workflow**
3. **FAQ & Property Search Workflow**
4. **Lease Expiry & Rent Renewal Workflow**

---

## 2. Phase Objectives

1. Establish a unified FastAPI application hosting modular `/api/v1/` routers.
2. Implement **Health & Readiness Endpoints** (`GET /health`, `GET /ready` with live PostgreSQL database probing).
3. Implement **Tenant & Property Resource Endpoints** (`/api/v1/tenants`, `/api/v1/properties`).
4. Implement **Maintenance Ticket Endpoints** (`/api/v1/maintenance/tickets`).
5. Implement **Workflow Triggering Endpoints** (`/api/v1/workflows/rent-reminder/run`, `/evaluate`, `/lease-expiry/scan`, `/renewal-reminder/scan`).
6. Implement **Master Pipeline Ingestion Endpoint** (`/api/v1/pipeline/message`).
7. Enforce strict Pydantic request validation and standardized JSON error envelopes.
8. Validate API integration with live PostgreSQL database and existing test suites.

---

## 3. Phase 4 Target Endpoints Map

```text
FastAPI Server (app/server.py)
  ├── Health Router
  │     ├── GET  /health                                 (Liveness)
  │     └── GET  /ready                                  (Database readiness probe)
  │
  ├── Tenants Router (/api/v1/tenants)
  │     ├── GET  /api/v1/tenants                         (List overdue tenants)
  │     ├── GET  /api/v1/tenants/{tenant_id}             (Get tenant profile)
  │     └── POST /api/v1/tenants/{tenant_id}/hold        (Set/clear manual hold)
  │
  ├── Properties Router (/api/v1/properties)
  │     ├── GET  /api/v1/properties                      (Search property listings)
  │     └── GET  /api/v1/properties/{property_id}        (Get property details)
  │
  ├── Maintenance Router (/api/v1/maintenance)
  │     ├── GET  /api/v1/maintenance/tickets             (List tickets)
  │     ├── POST /api/v1/maintenance/tickets             (Create ticket)
  │     └── GET  /api/v1/maintenance/tickets/{ticket_id} (Ticket detail & vendor)
  │
  ├── Workflows Router (/api/v1/workflows)
  │     ├── POST /api/v1/workflows/rent-reminder/run     (Trigger daily rent reminder batch)
  │     ├── POST /api/v1/workflows/rent-reminder/evaluate (Evaluate single tenant)
  │     ├── POST /api/v1/workflows/lease-expiry/scan     (Trigger lease expiry scan)
  │     └── POST /api/v1/workflows/renewal-reminder/scan (Trigger renewal reminder scan)
  │
  └── Pipeline Router (/api/v1/pipeline)
        └── POST /api/v1/pipeline/message                (Master pipeline ingestion)
```

---

## 4. Phase 4 Deliverables

### Code
* `langgraph_agent/app/api/schemas.py` — Pydantic request/response schemas.
* `langgraph_agent/app/api/routers/health.py` — Health & readiness endpoints.
* `langgraph_agent/app/api/routers/tenants.py` — Tenant resource endpoints.
* `langgraph_agent/app/api/routers/properties.py` — Property resource endpoints.
* `langgraph_agent/app/api/routers/maintenance.py` — Maintenance ticket endpoints.
* `langgraph_agent/app/api/routers/workflows.py` — Workflow trigger endpoints.
* `langgraph_agent/app/api/routers/pipeline.py` — Master pipeline message ingestion.
* `langgraph_agent/app/server.py` — Unified FastAPI application mounting all routers.
* `langgraph_agent/tests/test_api_layer.py` — Automated test suite covering all endpoints.

---

## 5. Phase 4 Exit Criteria

* [ ] Unified FastAPI application initialized and runnable via Uvicorn.
* [ ] Health (`/health`) and Readiness (`/ready` with DB ping) endpoints return expected status.
* [ ] Tenant endpoints query and update live database records via `TenantRepository`.
* [ ] Property endpoints search listings using property data.
* [ ] Maintenance ticket endpoints create and query tickets.
* [ ] Workflow endpoints execute batch scans and return structured summaries.
* [ ] Master pipeline endpoint normalizes input and routes across departments.
* [ ] Request validation rejects malformed payloads with 422 status.
* [ ] Zero direct SQL in route handlers (strict repository boundary).
* [ ] API test suite (`test_api_layer.py`) passes 100%.
* [ ] All 109+ existing project tests continue to pass with zero regressions.
