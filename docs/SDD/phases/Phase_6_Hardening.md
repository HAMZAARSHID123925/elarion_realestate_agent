# Phase 6 — Project-Wide Production Hardening

> **Document Path:** `docs/SDD/phases/Phase_6_Hardening.md`
> **Status:** Planned Phase
> **Scope:** Project-Wide (Platform-Wide Hardening)

---

## 1. Purpose

The purpose of Phase 6 is to apply final production hardening across the entire Elarion Real Estate Agent Platform, ensuring high availability, connection resilience, rate limiting, security sanitization, and production container packaging.

---

## 2. Phase Objectives

1. **Database & Connection Pool Optimization**:
   - Tune `AsyncConnectionPool` settings (`min_size`, `max_size`, keepalives) for high concurrency.
   - Validate PostgreSQL transaction rollback resilience under simulated network partitions.
2. **Security & Input Sanitization**:
   - Apply rate limiting on public webhook and API ingestion routes.
   - Enforce payload size limits and sanitize HTML/SQL inputs.
   - Ensure complete scrubbing of PII, tokens, and credentials from all log outputs.
3. **Observability & Health Telemetry**:
   - Establish Prometheus / OpenTelemetry metrics endpoints.
   - Track request duration, LLM token latency, database query times, and workflow failure rates.
4. **Container & Deployment Packaging**:
   - Finalize multi-stage Dockerfiles and Docker Compose configuration.
   - Document production environment variables and secret rotation procedures.

---

## 3. Phase 6 Exit Criteria

* [ ] Database connection pool survives high-load stress testing without leaks.
* [ ] Rate limiting actively protects API and webhook routes from abuse.
* [ ] Log auditing confirms zero sensitive tokens, keys, or credentials exposed.
* [ ] Multi-container Docker Compose setup boots cleanly and passes health checks.
* [ ] End-to-end multi-workflow regression suite passes 100%.
