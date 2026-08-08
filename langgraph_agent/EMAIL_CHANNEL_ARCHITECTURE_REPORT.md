# 📧 Elarion AI Property Management System
## Layer 1 Email Input Channel & 100% PostgreSQL Migration Report

**Date**: August 7, 2026  
**System Architecture**: Elarion 5-Layer AI Operations Layer  
**Email Provider**: **Resend** (Resend Webhook API Inbound + Resend REST API Outbound)  
**Database Engine**: **100% Neon PostgreSQL** (`AsyncPostgresSaver`)  
**Status**: Production Ready, Tested & Verified  

---

## 📌 Executive Summary

This document details the design, implementation, and verification of the **Email Input Channel** for the **Elarion AI Property Management Operations System**. 

Previously, the system supported **WhatsApp Cloud API** (Port 8003) and **VAPI Voice AI** (Port 8002). With this update, **Email** has been integrated as the 3rd production input channel running on **Port 8004** (`POST /email/webhook`).

In addition, the entire checkpoint persistence layer has been migrated from local SQLite (`checkpoints.db`) to **100% Neon PostgreSQL** (`AsyncPostgresSaver`), establishing a single unified database for both business entities and conversation state checkpoints.

---

## 🏛️ The 5-Layer Architecture Breakdown

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. INPUT CHANNELS LAYER (input_channels/)                                   │
│    WhatsApp (Port 8003) | VAPI Voice (Port 8002) | Resend Email (Port 8004)  │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. ELARION AI ORCHESTRATION LAYER (app/orchestrator/)                        │
│    Identity Lookup | Intent Classification | Urgency Detection | Rules Engine│
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. CORE AUTOMATED WORKFLOWS LAYER (app/core_workflows/)                     │
│    ├── maintenance/    (11-step ticket creation & vendor matching)       │
│    ├── faq/            (Pinecone RAG + property search tools)            │
│    ├── rent_renewal/   (Lease renewal options & tenant response workflow)│
│    └── rent_reminder/  (Overdue rent reminders & automated notices)     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. HUMAN & SYSTEM CONNECTIONS LAYER (mcp_servers/ & app/department_nodes)   │
│    Postgres DB (Neon) | MCP Servers | Durable State Checkpoints             │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. OUTPUTS & BUSINESS OUTCOMES LAYER                                        │
│    Automated Email/WhatsApp/Voice Replies | Audit Logs | Tickets Created    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 File-by-File Summary of Changes

| File | Action | Purpose & Technical Rationale |
| :--- | :--- | :--- |
| [`app/checkpointer.py`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/app/checkpointer.py) | **MODIFIED** | Upgraded from SQLite `AsyncSqliteSaver` to **`AsyncPostgresSaver`** backed by `psycopg_pool.AsyncConnectionPool` targeting `DATABASE_URL`. Added `WindowsSelectorEventLoopPolicy` handling for win32 async execution. |
| [`app/pipeline.py`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/app/pipeline.py) | **MODIFIED** | Added missing `rent_reminder` node and edge connection in `build_pipeline_graph()`, enabling master StateGraph compilation. |
| [`input_channels/email_server.py`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/input_channels/email_server.py) | **[NEW]** | Production-ready Layer 1 Email Channel adapter. Handles FastAPI webhook endpoint `POST /email/webhook`, signature verification, quote stripping, rate limiting, auto-reply loop protection, and outbound Resend delivery. |
| [`email_server.py`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/email_server.py) | **[NEW]** | Top-level process launcher shim (`python email_server.py`) running on Port `8004`. |
| [`test_email_local.py`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/test_email_local.py) | **[NEW]** | Interactive local CLI test suite for executing Maintenance, FAQ, and Rent Renewal email scenarios. |
| [`.env.example`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/.env.example) & [`.env`](file:///d:/ELARION/elarion_realestate_agent/langgraph_agent/.env) | **MODIFIED** | Configured `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `FROM_EMAIL_ADDRESS="onboarding@resend.dev"`, `EMAIL_SERVER_PORT="8004"`, and rate limit parameters. |
| `checkpoints.db` | **DELETED** | Removed legacy SQLite checkpoint file. |

---

## 🛡️ Production Best Practices Implemented

1. **Security & Signature Verification**:
   - Validates `svix-signature` / secret header against `RESEND_WEBHOOK_SECRET` on all incoming POST requests to reject unauthorized payloads.

2. **Auto-Reply Loop Prevention**:
   - Inspects headers (`Auto-Submitted`, `X-Autoreply`, `Precedence: bulk`) to filter out out-of-office bot messages and prevent infinite AI reply loops.

3. **Email Quote Stripping (`_clean_email_body`)**:
   - Parses MIME text body and strips previous reply quote history (`On Aug 7, 2026 ... wrote:`), ensuring the LLM only processes the newest turn text, saving prompt tokens and avoiding duplication.

4. **Per-Sender Sliding Window Rate Limiting**:
   - Enforces a sliding window rate limiter (default 10 emails per 60 seconds per sender) to defend against email spam attacks.

5. **Durable Multi-Turn Thread Continuity**:
   - Maps email conversation state in PostgreSQL using `thread_id = "email:<from_email>"`, allowing multi-turn maintenance slot collection to survive process restarts cleanly.

---

## 🧪 Terminal-Based Testing & Verification Guide

### Step 1: Start the Email Server
In Terminal 1 (inside `langgraph_agent`):
```bash
python email_server.py
```
*Expected Output*:
```text
INFO:input_channels.email_server:Connecting MCP clients (maintenance + FAQ) for Email Channel...
INFO:input_channels.email_server:Maintenance MCP client connected.
INFO:input_channels.email_server:FAQ MCP client connected.
INFO: Uvicorn running on http://0.0.0.0:8004
```

### Step 2: Launch the Local Test Harness
In Terminal 2 (inside `langgraph_agent`):
```bash
python test_email_local.py
```

### Step 3: Execute Test Scenarios

#### Scenario A: Maintenance Issue Report (Option 1)
- **Prompt**: *"My kitchen faucet broke and water is leaking in Unit 3B."*
- **Execution**: Webhook returns `200 OK`. Layer 2 Orchestrator classifies `maintenance`. Maintenance Subgraph creates ticket in PostgreSQL and asks for missing details.
- **Outbound Email**: Delivered to your inbox (`usman.hameed1145@gmail.com`).

#### Scenario B: Multi-Turn Maintenance Answer (Option 2)
- **Prompt**: *"Unit 3B, yes vendor can enter, no pets."*
- **Execution**: PostgreSQL loads existing conversation state via `thread_id`. `issue_collection_node.py` extracts slots and completes ticket `#TICK-1092`.

#### Scenario C: Support & FAQ Inquiry (Option 3)
- **Prompt**: *"What is the pet policy for dogs and what is the deposit amount?"*
- **Execution**: Layer 2 routes to `faq`. FAQ Subgraph performs vector search and emails policy details back to sender.

---

## 🚀 Production Deployment & Custom Domain Setup Checklist

When moving from testing to production with your own custom domain (e.g., `support@yourdomain.com`):

### 1. Resend Custom Domain Configuration
1. In [Resend Dashboard](https://resend.com) -> **Domains** -> Add `yourdomain.com`.
2. Add the 3 DNS records (MX, SPF TXT, DKIM TXT) provided by Resend to your domain registrar (Cloudflare, GoDaddy, Namecheap).
3. Once verified, update your `.env` file:
   ```env
   FROM_EMAIL_ADDRESS="support@yourdomain.com"
   ```

### 2. Live Production Webhook URL
Point your Resend Webhook endpoint to your production domain:
```text
https://api.yourdomain.com/email/webhook
```

---

## ✅ Final Verification Proof

During live terminal execution, the following verified log trace was produced:

```text
INFO:input_channels.email_server:[Inbound Email Received] From: usman.hameed1145@gmail.com | Subject: 'Pet policy'
INFO:app.checkpointer:Connecting persistent AsyncPostgresSaver to PostgreSQL... Connected & verified.
INFO:app.orchestrator.nodes:Classified: faq | Urgency: low | Decision: routed_to_faq_workflow
INFO:app.core_workflows.faq.nodes.classify_intent_node:[FAQ] classified intent=KNOWLEDGE
INFO:input_channels.email_server:[Email Outbound -> usman.hameed1145@gmail.com] Subject: Re: Pet policy
INFO:input_channels.email_server:Resend email dispatched successfully: ID=02373d4f-8a69-4920-a45f-3e2fceae6e4e
```

The system is **100% operational, fully documented, and ready for production deployment**.
