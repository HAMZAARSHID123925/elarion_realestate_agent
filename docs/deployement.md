# Deployment Notes

This document covers what's different about running Elarion on a real server
versus your own laptop. For day-to-day install/config/run instructions, see
the main `README.md` first -- this file only adds the production-specific
pieces.

## 1. Where things run

- `whatsapp_server.py` and `vapi_server.py` are the two long-running
  processes that need to be reachable from the internet (WhatsApp/VAPI both
  call into them via webhook).
- `mcp_server.py` and `mcp_servers/property_search/` are **not** separate
  network services -- they're spawned as stdio subprocesses by whichever
  app process needs them. You never deploy or expose these directly.
- The database is managed Postgres (Neon), reached via `DATABASE_URL`. There
  is nothing to provision or patch yourself for the database server.

## 2. Running via Docker Compose

```bash
docker compose -f docker_compose.yaml up -d
```

This starts `whatsapp-server` and `vapi-server`, each with:
- `restart: unless-stopped` -- if a process crashes (e.g. an unhandled
  exception at 3am), Docker restarts it automatically instead of it staying
  down until someone notices.
- a healthcheck against `GET /health` on each service, so `docker ps` and
  any monitoring you point at Docker will show a service as unhealthy if it
  stops responding, even if the process itself is still technically running.

See the comments at the top of `docker_compose.yaml` for what's intentionally
not included yet (a Postgres container, a proper Dockerfile with dependencies
baked in at build time) and why.

## 3. Exposing the servers publicly

Both WhatsApp and VAPI need a public HTTPS URL to call into:
- `whatsapp_server.py` needs to receive `POST /whatsapp/webhook` from Meta.
- `vapi_server.py` needs to receive requests from your VAPI assistant
  configuration.

Put a reverse proxy (nginx, Caddy, or your cloud provider's load balancer)
in front of both, terminating TLS, and forward to ports `8003` and `8002`
respectively (matching the ports in `docker_compose.yaml`).

## 4. Secrets

- Never commit `.env` -- it's already excluded via `.gitignore`.
- On a real server, prefer your platform's secret manager (or at minimum an
  `.env` file with restrictive file permissions, not baked into an image)
  over hardcoding any credential anywhere in the repo.
- `WHATSAPP_APP_SECRET` is what makes the webhook signature check in
  `whatsapp_server.py` work -- if this leaks, anyone can forge WhatsApp
  webhook calls to your server. Treat it like any other production secret.

## 5. Monitoring / alerting

- Set `TEAM_ALERT_WEBHOOK_URL` (a Slack incoming webhook) in production so
  that if a WhatsApp reply fails to actually reach a tenant, your team gets
  pinged instead of it only showing up in a log nobody's watching.
- Point external uptime monitoring (e.g. UptimeRobot, a status-page service,
  or your cloud provider's health checks) at `GET /health` on both servers,
  independent of Docker's own healthcheck, so you get alerted even if the
  whole host goes down.

## 6. Before you flip the switch to real tenants

1. Confirm you completed the WhatsApp webhook verification handshake for
   real, from a public URL (see README section 6) -- not just the local
   test script.
2. Confirm `VALIDATE_META_SIGNATURE=true` in the production `.env`.
3. Send a real end-to-end WhatsApp message and a real end-to-end VAPI call
   and confirm both produce a ticket in the real database.
4. Know that the emergency-escalation step currently only produces a
   message telling the tenant a human was notified -- no human is actually
   paged yet (see README section 8). Decide whether that's acceptable for
   your initial rollout before real tenants start messaging about
   emergencies.
