# TenantFlow.ai — Next.js Frontend Architecture & Roadmap

This directory (`frontend/docs/`) contains all frontend-specific documentation, component contracts, API interfaces, and state management guides for the TenantFlow.ai AI Operations Layer Dashboard.

---

## Architecture Principles
1. **Framework**: Next.js 15+ App Router with TypeScript.
2. **Styling**: Tailwind CSS & CSS Variables with sleek dark mode branding 
3. **Decoupled API Layer**: All server & client components consume backend endpoints via `frontend/lib/api-client.ts` over REST (`http://localhost:8080/api/v1/...`).
4. **No Mock Fallbacks in Production**: Components bind directly to backend response envelopes.

---

## Page Mapping to Endpoints
- `/overview` ➔ `GET /api/v1/dashboard/overview` & `POST /api/v1/human-escalations/{id}/action`
- `/conversations` ➔ `GET /api/v1/dashboard/conversations`
- `/conversations/[id]` ➔ `GET /api/v1/dashboard/conversations/{id}` & `POST /api/v1/dashboard/conversations/{id}/review`
- `/automations` ➔ `GET /api/v1/dashboard/automations` & `PATCH /api/v1/dashboard/automations/{id}`
- `/agent-activity` ➔ `GET /api/v1/dashboard/agent-activity`
- `/properties` ➔ `GET /api/v1/properties/dashboard` & `POST /api/v1/properties` & `DELETE /api/v1/properties/{id}` & `PATCH /api/v1/properties/{id}/status`

---

## Documentation Index
- [Chunk 1: Database Migration & Dashboard Engine](file:///d:/ELARION/elarion_realestate_agent/frontend/docs/CHUNK_1_BACKEND_DASHBOARD_ENGINE.md)
- [Chunk 2: Overview Dashboard UI](file:///d:/ELARION/elarion_realestate_agent/frontend/docs/CHUNK_2_OVERVIEW_DASHBOARD.md)
- [Chunk 3: Conversations Page](file:///d:/ELARION/elarion_realestate_agent/frontend/docs/CHUNK_3_CONVERSATIONS_PAGE.md)
- [Chunk 4: Automations Grid & Rules Engine](file:///d:/ELARION/elarion_realestate_agent/frontend/docs/CHUNK_4_AUTOMATIONS_PAGE.md)
- [Chunk 5: Properties Dashboard Page](file:///d:/ELARION/elarion_realestate_agent/frontend/docs/CHUNK_5_PROPERTIES_PAGE.md)
- [Chunk 6: Agent Activity & Audit Operations Route](file:///d:/ELARION/elarion_realestate_agent/frontend/docs/CHUNK_6_AGENT_ACTIVITY_PAGE.md)


