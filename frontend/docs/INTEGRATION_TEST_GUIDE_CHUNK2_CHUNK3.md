# TenantFlow.ai â€” Integration Test Guide
## Chunk 2 (Overview Dashboard) + Chunk 3 (Conversations Page)

> **File Path:** `frontend/docs/INTEGRATION_TEST_GUIDE_CHUNK2_CHUNK3.md`
> **Covers:** End-to-end test from sending a pipeline message â†’ DB save â†’ Overview update â†’ Conversations update
> **Prerequisites:** Both servers must be running (see Phase 0 below)
> **Last Updated:** 2026-08-23 â€” Post-test-run fixes applied (Groq model, SSL pool, timezone, escalation FK)

---

> **Last Updated:** 2026-08-24 — Post-test-run fixes applied (Groq model, SSL pool, timezone, escalation FK)

---

## 🛠 Fixes Applied Before This Test Run

> ❗ **Do NOT skip this section.** These 4 bugs were discovered during the first test run and are now fixed. The server must be **restarted** for the fixes to take effect.

| # | Bug | Root Cause | Fixed In |
|---|---|---|---|
| 1 | **Groq LLM 404 error** | `llama-3.3-70b-versatile` was deprecated on your Groq account | `app/orchestrator/nodes.py` → now uses `qwen/qwen3.6-27b` (Groq-native, tool-calling capable, generous rate limits) |
| 2 | **Second message → 500 Internal Server Error** | Neon PostgreSQL dropped the idle SSL connection from the pool (~5 min timeout) | `app/checkpointer.py` → pool now uses `min_size=0`, `max_idle=240s` |
| 3 | **Recent Activity timestamps in UTC** | `TO_CHAR(timestamp, ...)` used DB server UTC time | `database/dashboard_repository.py` → now uses `AT TIME ZONE 'Asia/Karachi'` |
| 4 | **Needs Attention card not showing** | `human_escalations` INSERT used fragile `LIMIT 1` subselects that failed silently on NOT NULL FK constraints | `database/conversation_repository.py` → explicit pre-fetch with safety skip |

### ⚡ Required: Restart the Backend Server

After these fixes, **you MUST restart uvicorn** (the old process had stale code in memory):

```powershell
# In the langgraph_agent/ terminal â€” press Ctrl+C first, then:
python -m uvicorn app.server:app --host 0.0.0.0 --port 8080 --reload
```

> Wait until you see: `INFO: Application startup complete.` before proceeding.

---

## ðŸ“‹ Current Database Baseline (Before This Test Run)

These are the **live numbers right now** after the first test run. Your new tests will increment from here:

| Metric | Value NOW (Before This Test) |
|---|---|
| **Total Conversations** | **6** (5 seed + 1 from WhatsApp test) |
| **AI Resolved** | **4** |
| **Human Escalations (OPEN)** | **1** |
| **Automation Rate** | **~67%** (4 AI resolved of 6 total) |
| **Needs Attention cards** | **1** (should appear after server restart + fix) |

> â„¹ï¸ The Email message (gas smell) was **not saved** to DB because the server hit a 500 (SSL drop bug, now fixed).
> The WhatsApp message WAS saved but got the fallback response because the Groq model was wrong (now fixed).

---

## PHASE 0 â€” Confirm Both Servers Are Running

### Step 0.1 â€” Verify Backend (FastAPI)

```
http://localhost:8080/health
```

**âœ… Expected Output:**
```json
{ "status": "healthy", "service": "elarion-core-api", "version": "2.0" }
```

---

### Step 0.2 â€” Verify Frontend (Next.js)

```
http://localhost:3000
```

**âœ… Expected Output:** Redirected to Overview dashboard. TenantFlow.ai sidebar visible.

---

### Step 0.3 â€” Confirm Groq Model Fix Is Live (Critical Smoke Test)

```powershell
$body = @{ channel="WhatsApp"; user_id="+923000000001"; text="What are the pool hours?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/pipeline/message" -Method POST -Body $body -ContentType "application/json"
```

**âœ… Expected:** `final_response` contains a real AI answer â€” NOT `"I had a little trouble understanding that"`.

> âŒ If you still see the fallback message: The server did not reload the fix. Manually restart uvicorn.

---

## PHASE 1 â€” Chunk 2: Overview Dashboard Visual Verification

### Step 1.1 â€” Load the Overview Page

```
http://localhost:3000/overview
```

**âœ… Expected Output â€” All 5 stat cards populated:**

| Section | What You Should See |
|---|---|
| **Conversations** | **6** |
| **AI Resolved** | **4** |
| **Human Escalations** | **1** (amber color) |
| **Automation Rate** | **~67%** (emerald color) |
| **Avg. Response Time** | Some value in seconds |
| **Needs Attention** | **1 card** (CRITICAL â€” from the WhatsApp "leak" message, now visible after fix) |
| **Agent Activity Today** | Table with rows: Resident Support (4 runs), Rent Follow-up (1), Maintenance Request (1) |
| **Recent Activity** | Timeline with 5 AI messages, timestamps in **PKT** (e.g. 07:59 PM) |

---

### Step 1.2 â€” Verify Recent Activity Timestamps Are PKT

The timestamps in **Recent Activity** should now show **Pakistan Standard Time** (UTC+5).

- Previously showed `02:59 PM` (UTC). Now shows `07:59 PM` (PKT). âœ… Fixed.

**âœ… Expected:** Times match your local Pakistan clock (UTC+5).

---

### Step 1.3 â€” Verify "Refresh Data" Button

Click **"Refresh Data"** (top-right).

**âœ… Expected:** Icon spins briefly, numbers stay stable, no errors.

---

## PHASE 2 â€” Send Two Fresh Test Messages

Now with the Groq model fixed, you will get **real AI responses**.

### Step 2.1 â€” Send Message A: Normal Maintenance Request

**Using Swagger UI:**

1. Open `http://localhost:8080/docs`
2. `POST /api/v1/pipeline/message` â†’ **"Try it out"**
3. Paste:

```json
{
  "channel": "WhatsApp",
  "user_id": "+923001112244",
  "text": "Hi, my kitchen tap is leaking badly in Unit 101. Please help!"
}
```

> â„¹ï¸ Using a **different** `user_id` from the first test (`+923001112233`). This creates a fresh conversation instead of updating the old one.

**âœ… Expected API Response:**
```json
{
  "channel": "WhatsApp",
  "user_id": "+923001112244",
  "final_response": "Got it. I've logged a maintenance ticket for the leaking tap...",
  "intent": "Processed",
  "active_department": "orchestrator"
}
```

> âœ… The `final_response` must be a **real AI-generated reply**, not the fallback message.

---

### Step 2.2 â€” Send Message B: Emergency (Escalation)

```json
{
  "channel": "Email",
  "user_id": "maria.test@example.com",
  "text": "URGENT - there is a gas smell in my unit and smoke near the kitchen!"
}
```

**âœ… Expected API Response (HTTP 200 â€” SSL bug is fixed):**
```json
{
  "channel": "Email",
  "user_id": "maria.test@example.com",
  "final_response": "This sounds like an emergency. I am escalating this to a live human manager immediately...",
  "intent": "Processed",
  "active_department": "orchestrator"
}
```

> â— **This MUST return HTTP 200 now** (was 500 before the SSL fix).
> âœ… `gas smell` + `smoke` â†’ `is_emergency = True` â†’ status `Escalated`, urgency `CRITICAL`, row inserted into `human_escalations` with `status = 'OPEN'`

---

## PHASE 3 â€” Verify Database Saved Both Conversations

### Step 3.1 â€” Check via API

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/dashboard/conversations?limit=8" | ConvertTo-Json -Depth 3
```

**âœ… Expected Output:**
```json
{
  "total": 8,
  "items": [
    { "contact_name": "maria.test@example.com", "channel": "Email", "urgency": "CRITICAL", "status": "Escalated" },
    { "contact_name": "+923001112244", "channel": "WhatsApp", "urgency": "CRITICAL", "status": "Escalated" },
    { "contact_name": "+923001112233", "channel": "WhatsApp", "urgency": "CRITICAL", "status": "Escalated" },
    ...5 seed rows...
  ],
  "limit": 8,
  "offset": 0
}
```

> âœ… **Total = 8** (6 before + 2 new)
> âœ… **Email row exists** (was missing before â€” now fixed)
> âœ… Both new rows show `CRITICAL` + `Escalated`

> â„¹ï¸ The WhatsApp "leaking tap" message also shows `CRITICAL + Escalated` because `leak` matches the emergency keyword list. This is by design â€” the state machine treats active water leaks as critical.

---

### Step 3.2 â€” Check Conversation Messages Were Saved

Pick the `conversation_id` for `maria.test@example.com` and run:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/dashboard/conversations/TF-XXXXX" | ConvertTo-Json -Depth 5
```

**âœ… Expected Output:**
```json
{
  "conversation_id": "TF-XXXXX",
  "contact_name": "maria.test@example.com",
  "channel": "Email",
  "urgency": "CRITICAL",
  "status": "Escalated",
  "messages": [
    { "sender_type": "tenant", "content": "URGENT - there is a gas smell in my unit and smoke near the kitchen!" },
    { "sender_type": "ai", "sender_name": "TenantFlow AI", "content": "This sounds like an emergency..." }
  ]
}
```

> âœ… **Two messages minimum** â€” tenant turn + AI turn.

---

## PHASE 4 â€” Chunk 2: Verify Overview Dashboard Updated

### Step 4.1 â€” Refresh the Overview Page

Navigate to `http://localhost:3000/overview` and click **"Refresh Data"**.

**âœ… Expected Updated Numbers:**

| Section | Before Phase 2 | After Phase 2 (Expected) |
|---|---|---|
| **Conversations** | 6 | **8** |
| **AI Resolved** | 4 | **4** (both new messages were Escalated, not AI Resolved) |
| **Human Escalations** | 1 | **3** (1 old + 2 new OPEN escalations) |
| **Automation Rate** | ~67% | **~50%** (4 AI resolved of 8 total) |
| **Needs Attention cards** | 1 | **3 cards** |

---

### Step 4.2 â€” Verify Needs Attention Cards Appear

**âœ… Expected:**
- Red-bordered CRITICAL cards appear
- Title shows contact name + message preview
- **"Review"** action button visible

> âŒ If still empty: check uvicorn terminal for `human_escalations INSERT skipped` warning. If present, run `python database/migrations/run_migration.py` from project root to ensure `leases` and `tenants` tables have rows.

---

### Step 4.3 â€” Verify Agent Activity Today Updated

**âœ… Expected:**
- Rows still visible: `Resident Support`, `Rent Follow-up`, `Maintenance Request`
- Run counts may have incremented

---

### Step 4.4 â€” Verify Recent Activity Timeline Updated

**âœ… Expected:**
- Newest AI response at the **top**
- Timestamps in **PKT** matching your local clock

---

## PHASE 5 â€” Chunk 3: Conversations Page

### Step 5.1 â€” Load the Conversations Page

```
http://localhost:3000/conversations
```

**âœ… Expected:**
- Subtitle shows **8 total**
- Filter bar with all controls visible
- **8 rows** in the table

---

### Step 5.2 â€” Verify Badge Colors

| Badge Type | What You Should See |
|---|---|
| **Channel: WhatsApp** | Green pill with ðŸ’¬ emoji |
| **Channel: Email** | Blue pill with âœ‰ï¸ emoji |
| **Urgency: CRITICAL** | Red pill with red dot |
| **Urgency: High** | Amber pill with amber dot |
| **Urgency: Normal** | Slate/grey pill |
| **Status: AI Resolved** | Emerald pill with âœ¨ icon |
| **Status: Escalated** | Amber pill with â†— icon |

---

### Step 5.3 â€” Test Search Filter

Type **`maria`** in the Search box.

**âœ… Expected (after 350ms debounce):**
- Only 1 row: `maria.test@example.com` â€” Email â€” CRITICAL â€” Escalated

Clear search â†’ all 8 rows return.

---

### Step 5.4 â€” Test Channel Filter

1. Set **Channel** â†’ `Email` â†’ Click **"Apply Filters"**

**âœ… Expected:**
- Only Email conversations remain
- "Filters active" label visible in emerald color

Click **"Clear"** â†’ all 8 rows return.

---

### Step 5.5 â€” Test Urgency Filter

1. Set **Urgency** â†’ `Critical` â†’ Click **"Apply Filters"**

**âœ… Expected:**
- Only CRITICAL rows appear (new messages + TF-96614)
- All show red `CRITICAL` badge

Click **"Clear"** to reset.

---

### Step 5.6 â€” Test Status Filter

1. Set **Status** â†’ `Escalated` â†’ Click **"Apply Filters"**

**âœ… Expected:**
- All escalated conversations appear
- All show amber `Escalated` badge

Click **"Clear"** to reset.

---

### Step 5.7 â€” Test Multi-Filter Combination

1. Set **Channel** = `Email`
2. Set **Status** = `Escalated`
3. Click **"Apply Filters"**

**âœ… Expected:**
- Only maria.test@example.com row
- "Filters active" indicator shows

Click **"Clear"**.

---

### Step 5.8 â€” Test Date Range Filter

1. Set **Date Range** â†’ `Today` â†’ Click **"Apply Filters"**

**âœ… Expected:**
- Only today's conversations (3 from today's session)
- Seed data from Aug 17-20 hidden

Set **Date Range** â†’ `Last 7 Days` â†’ Apply â†’ all 8 return.

---

## PHASE 6 â€” Conversation Drawer Verification

### Step 6.1 â€” Open the Drawer

Click the `maria.test@example.com` Emergency row.

**âœ… Expected:**
- Dark backdrop + right-side drawer slides in (480px)
- Header: `maria.test@example.com` + conversation ID + `Email` (blue) + `CRITICAL` (red) + `Escalated` (amber)

---

### Step 6.2 â€” Verify Drawer Metadata

| Field | Expected Value |
|---|---|
| ðŸ¢ Property | `Sunset Apartments` (fallback) |
| # Unit | `Unit 204` (fallback) |
| âš¡ Workflow | `orchestrator` or `Resident Support` |
| ðŸ“… Created | Today's date |

---

### Step 6.3 â€” Verify Message Transcript

**âœ… Expected:**
- **Tenant bubble** (left, grey): `"URGENT - there is a gas smell in my unit and smoke near the kitchen!"`
- **AI bubble** (right, emerald): Real AI emergency response (NOT the old fallback "I had a little trouble..." â€” that was the broken model)
- Timestamps in **PKT**
- Transcript auto-scrolled to bottom

---

### Step 6.4 â€” Test "Mark as Reviewed" Button

Click **"Mark as Reviewed"**.

**âœ… After clicking:**
- Button changes to `"Already Reviewed"` (grey/disabled)
- `"âœ… Reviewed"` badge appears in header

---

### Step 6.5 â€” Verify Drawer Close Behaviors

| Method | Expected |
|---|---|
| **X button** | Drawer slides out right, backdrop disappears |
| **Escape key** | Drawer closes instantly |
| **Backdrop click** | Drawer closes instantly |

---

## PHASE 7 â€” Full Cycle Verification (Chunk 2 + Chunk 3 Connected)

### Step 7.1 â€” Note Current Count

Open `http://localhost:3000/overview` â€” Conversations stat card: **8**.

### Step 7.2 â€” Send a Third Message

```json
{
  "channel": "Voice",
  "user_id": "tenant-john-doe-789",
  "text": "Hello, I want to renew my lease for another year."
}
```

### Step 7.3 â€” Refresh Overview

**âœ… Expected:**
- Conversations: **9**
- New AI response appears at top of Recent Activity

### Step 7.4 â€” Go to Conversations, Verify New Row

```
http://localhost:3000/conversations
```

**âœ… Expected:**
- **9 total** in subtitle
- New row at top: `tenant-john-doe-789` â€” Voice â€” lease intent
- ðŸŽ™ï¸ Voice channel badge visible

---

## âœ… Final Pass / Fail Checklist

| Test Area | Pass? |
|---|---|
| Both servers healthy | â˜ |
| Groq model fix confirmed (real AI response, not fallback) | â˜ |
| Overview loads with correct DB numbers (6 convs, ~67%) | â˜ |
| Message A (WhatsApp) â†’ HTTP 200, real AI response | â˜ |
| Message B (Email) â†’ HTTP 200 (was 500, now fixed) | â˜ |
| Total conversations increments to 8 | â˜ |
| Email conversation appears in DB (was missing before) | â˜ |
| Needs Attention card(s) appear after escalation | â˜ |
| Recent Activity timestamps show PKT time | â˜ |
| Human Escalations counter matches Needs Attention count | â˜ |
| Conversations page loads with correct 8 total | â˜ |
| All 3 badge types render correct colors | â˜ |
| Search filter works (debounced, auto-fires) | â˜ |
| Channel filter works with Apply | â˜ |
| Urgency filter works with Apply | â˜ |
| Status filter works with Apply | â˜ |
| Multi-filter combination works | â˜ |
| Date Range = Today shows only today's conversations | â˜ |
| Clear button resets all filters | â˜ |
| Row click opens drawer | â˜ |
| Drawer shows correct transcript messages | â˜ |
| Drawer transcript has real AI response (not fallback) | â˜ |
| "Mark as Reviewed" button works | â˜ |
| Escape/backdrop/X all close the drawer | â˜ |
| New message (Phase 7) updates BOTH pages | â˜ |

---

## ðŸ› Troubleshooting Guide

| Symptom | Root Cause | Fix |
|---|---|---|
| Groq 404 on LLM call | `llama-3.3-70b-versatile` deprecated | Fixed in `nodes.py`. **Restart uvicorn.** |
| Second message â†’ 500 Internal Server Error | Neon SSL connection dropped from pool | Fixed in `checkpointer.py`. **Restart uvicorn.** |
| `consuming input failed: SSL connection closed` | Same SSL pool issue | Restart uvicorn â€” fix applied |
| Recent Activity times 5 hrs behind | UTC used instead of PKT | Fixed in `dashboard_repository.py`. No restart needed. |
| Needs Attention card missing | `human_escalations` INSERT failing on NOT NULL FK | Fixed in `conversation_repository.py`. Re-send test messages. |
| `human_escalations INSERT skipped` in logs | No rows in `leases` or `tenants` table | Run `python database/migrations/run_migration.py` from project root |
| Overview shows all zeros | DB not seeded | Run migration `008_add_conversations_and_messages.sql` |
| `MCP Client not connected` in logs | MCP server not started (warning only, not crash) | Non-critical: pipeline works, tenant lookup degrades to Guest identity |
| AI always says "I had a little trouble" | Groq model was 404 | Fixed in `nodes.py` â€” restart uvicorn |
| Email conversation not in DB | Was caused by SSL 500 crash before fix | After fix: re-send the email message â€” it will now save correctly |
| `active_department` always shows `"orchestrator"` | Hardcoded in `pipeline.py` router response schema | Non-critical cosmetic â€” correct dept tracked internally in DB |
| Search doesn't auto-fire | 350ms debounce â€” wait a moment | Normal behavior |
| Drawer shows no messages | `conv_dict` bug (fixed in Chunk 3 code) | Verify the conversations detail API router fix was applied |
| Human Escalations count doesn't match Needs Attention | Old mismatch between `!= CLOSED` vs `= OPEN` queries | Fixed in `dashboard_repository.py` â€” both now use `status = 'OPEN'` |
