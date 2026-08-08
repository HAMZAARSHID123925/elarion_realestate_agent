# Elarion Real Estate AI Agent

An AI agent for property management that talks to tenants over WhatsApp and
voice (VAPI), understands maintenance requests and FAQs, creates real
maintenance tickets, and routes them to vendors -- backed by a real Postgres
database (Neon) and audited with a full activity log.

This README covers install, configuration, running each server, and running
the tests. See `docs/architecture.md` and `docs/api_contracts.md` for how the
pieces fit together, and `docs/deployement.md` for deploying beyond your own
machine.

## 1. Project layout (5-Layer AI Operations Architecture)

```text
langgraph_agent/
  input_channels/               Layer 1: Input channel webhooks & adapters
    whatsapp_server.py           - Meta WhatsApp Cloud API (port 8003)
    vapi_server.py               - VAPI Voice API endpoint (port 8002)
  app/
    pipeline.py                  - Master entry point: handle_request(channel, user_id, raw_text, ...)
    orchestrator/                Layer 2: Elarion AI Orchestration (intent/urgency classification & routing)
    core_workflows/              Layer 3: Core Automated Workflows
      maintenance/               - 11-step maintenance request automation & ticket creation
      faq/                       - Tenant support & FAQ RAG knowledge base
      rent_renewal/              - Lease / Rent Renewal workflow (scaffolding ready)
  whatsapp_server.py            Launcher shim for input_channels/whatsapp_server.py
  vapi_server.py                Launcher shim for input_channels/vapi_server.py
  mcp_server.py                 MCP tool server for tenant lookup, ticket creation & vendor matching
mcp_servers/property_search/    Second MCP server, used by the FAQ workflow
database/                       schema.sql, seed.sql, migrations/
docs/                           architecture, API contracts, deployment notes
```

## 2. Prerequisites

- Python 3.11+
- A Postgres database. This project is already configured against a managed
  Neon Postgres instance (see `DATABASE_URL` below) -- you don't need to
  install Postgres locally.
- A Groq API key (LLM calls)
- (Optional, only if you want the FAQ/RAG workflow) Google Gemini + Pinecone
  API keys
- (Optional, only if you're wiring up the WhatsApp channel) a Meta for
  Developers app with WhatsApp Cloud API access

## 3. Install

```bash
cd langgraph_agent
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install fastapi uvicorn requests python-dotenv "psycopg[binary]" psycopg_pool \
            mcp langgraph langchain-core langchain-groq pydantic
pip install -r requirements-faq.txt   # only needed for the FAQ/RAG workflow
```

> Note: there isn't yet a single consolidated `requirements.txt` in this
> project -- `requirements-faq.txt` only lists the *extra* packages the FAQ
> workflow needs, on top of the "core" packages listed in the first
> `pip install` above (these were inferred from the actual imports across
> `whatsapp_server.py`, `vapi_server.py`, `mcp_server.py`, and the
> orchestrator/maintenance packages). Freezing a proper `requirements.txt`
> (`pip freeze > requirements.txt` from a working venv) is worth doing next.

## 4. Configure environment variables

Copy the example file and fill in real values:

```bash
cd langgraph_agent
cp .env.example .env
```

`langgraph_agent/.env.example` lists every variable the project actually
uses and what each one is for. At minimum you need:

- `DATABASE_URL` -- your Postgres connection string
- `GROQ_API_KEY` -- for the LLM calls (intent classification, slot extraction)

Only if you're using the FAQ/RAG workflow:
- `GOOGLE_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_NAMESPACE`

Only if you're wiring up WhatsApp:
- `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET`,
  `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_API_VERSION`, `VALIDATE_META_SIGNATURE`
  (keep this `"true"` outside of a throwaway local debugging session)
- `TEAM_ALERT_WEBHOOK_URL` -- a Slack incoming-webhook URL. If a WhatsApp
  reply fails to send back to a tenant, this is where the team gets alerted
  (without it, a CRITICAL log line is written instead, which nobody may see).
- `WHATSAPP_RATE_LIMIT_MAX_MESSAGES` / `WHATSAPP_RATE_LIMIT_WINDOW_SECONDS`
  -- per-phone-number rate limiting on the webhook (defaults: 10 messages
  per 60 seconds).

The `.env` file is already excluded from Git via `.gitignore` -- never commit
real secrets.

## 5. Set up the database

The schema, seed data, and migrations live in `database/`. Point `psql` (or
your preferred client) at the `DATABASE_URL` from your `.env` and run:

```bash
psql "$DATABASE_URL" -f database/schema.sql
psql "$DATABASE_URL" -f database/seed.sql          # optional sample data
# apply anything under database/migrations/ in order, if present
```

`langgraph_agent/init_db.py` may also help bootstrap this -- check its
contents before running it against a database you care about.

## 6. Run the servers

Each server is independent; run whichever ones you need.

```bash
cd langgraph_agent

# Voice channel (VAPI) -- http://localhost:8002
python vapi_server.py

# WhatsApp channel (Meta Cloud API) -- http://localhost:8003
python whatsapp_server.py
```

Both expose a `GET /health` endpoint for uptime checks.
`mcp_server.py` does **not** need to be started separately -- each of the
above processes spawns it automatically over stdio the first time it needs a
database tool (see `app/orchestrator/maintenance/mcp_client.py`).

Or run everything together with Docker Compose (auto-restarts each service
if it crashes, and polls `/health`):

```bash
docker compose -f docker_compose.yaml up
```

### WhatsApp webhook setup (one-time, before going live)

1. Run `whatsapp_server.py` somewhere with a public URL (use `ngrok http 8003`
   for local testing, or your real server's address in production).
2. In the Meta App Dashboard, set the webhook URL to
   `https://<your-public-url>/whatsapp/webhook` and the verify token to the
   same value as `WHATSAPP_VERIFY_TOKEN` in your `.env`.
3. Meta will call `GET /whatsapp/webhook` once to confirm you control the
   endpoint -- this only happens when you save/change the URL in the
   dashboard, not on every message.
4. Send a real WhatsApp message to your test number and confirm you get a
   reply end-to-end. `test_whatsapp_local.py` only exercises your own
   machine talking to itself and does **not** replace this real,
   public-internet test.

## 7. Run the tests

```bash
cd langgraph_agent
python -m pytest test_orchestrator.py test_mcp_client.py \
    test_maintenance_stage1.py test_maintenance_stage3.py test_maintenance_stage4.py \
    test_faq_stage1.py test_production_readiness.py -v
```

`test_whatsapp_local.py` is a manual script, not a pytest suite -- run it
directly (`python test_whatsapp_local.py`) with `whatsapp_server.py` already
running locally.

## 8. Known, intentional limitations (not bugs)

- When the maintenance workflow escalates a request to `escalation_node.py`,
  it currently stops there with a message telling the tenant a human has
  been notified -- there is no real SMS/call/Slack integration wired up yet
  to actually page someone. This is intentional at this stage of the
  project and will be connected to a real notification channel later; it is
  not something this pass of fixes touched.
