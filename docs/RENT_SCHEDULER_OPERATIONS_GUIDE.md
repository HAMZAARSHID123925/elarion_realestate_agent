# 🏛️ Elarion AI Property Management - Rent Reminder & Scheduler Operations Guide

**Version**: 2.0  
**Workflow Module**: `app/core_workflows/rent_reminder` & `database/rent_models.py`  
**Execution Engine**: Python 3.13 | LangGraph | SQLite/PostgreSQL | FastAPI Lifespan Async Loop  

---

## 📌 1. Overview & Business Requirements

This document specifies the production operational architecture for the **Automated Morning Rent Reminder & Escalation Engine** in the Elarion AI Property Management platform.

### Core Business Rules & Lifecycle:
1. **Tenant Joining-Date Relative 30-Day Billing Cycle**:
   - Each tenant has an individualized `joining_date` (or `lease_start_date`).
   - Billing cycles run on a 30-day recurring period relative to their joining date.
   - *Example A (Ali Ahmed)*: Joined on `2026-07-01` (Day 1). Billing cycle 30th day falls on `2026-07-30`.
   - *Example B (Furqan Khan)*: Joined on `2026-07-11` (Day 11). Billing cycle 30th day falls on `2026-08-10`.

2. **Day 30 Rent Reminder (#1)**:
   - On the 30th day of the billing cycle (due date), if rent remains unpaid (`payment_status != 'paid'`), the engine sends an automated **30-Day Rent Reminder**.
   - DB Updates: `last_reminder_status = 'reminder_sent'`, `reminder_30_sent_at = timestamp`.

3. **Days 31–35 Unpaid Grace/Warning Window (#2)**:
   - During days 31–35 of the billing cycle (1 to 5 days past the 30th day), if rent is still unpaid, the engine sends an urgent **Days 31–35 Warning Notice**.
   - DB Updates: `last_reminder_status = 'followup_sent'`, `reminder_5_sent_at = timestamp`.

4. **Day 36+ Direct Human Escalation**:
   - If rent remains unpaid on Day 36 (past the 5-day warning window), the system automatically triggers a **Direct Human Transfer**.
   - The case is flagged (`human_escalated = 1`, `payment_status = 'escalated'`), and a comprehensive alert payload is pushed to the property management team.

5. **Manual Hold Override (`manual_hold = 1`)**:
   - Tenants placed under manual hold (e.g. customized payment plans) are automatically skipped by the automated engine.

---

## 🏗️ 2. Architectural Flow & Components

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                       AUTOMATED MORNING SCHEDULER                          │
│               (Triggers daily at 08:00 AM / FastAPI Lifespan)              │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    DATABASE SCAN (get_unpaid_overdue_tenants)             │
│        Queries tenants table for active unpaid records (payment_status!='paid')│
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                  LANGGRAPH SUBGRAPH (rent_reminder_graph)                   │
│                                                                            │
│  [payment_check_node] ──► [reminder_decision_node] ──► Action Branching   │
│                                                              │             │
│            ┌──────────────────────┬──────────────────────────┼──────────┐  │
│            ▼                      ▼                          ▼          ▼  │
│   (Day 30 Reminder)     (Days 31-35 Warning)         (Day 36 Escalation) (Skip)│
│  [reminder_send_node]   [reminder_send_node]   [human_escalation_node]    │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 3. Step-by-Step Production Deployment Guide

### Step 1: Database Migration
Ensure your database contains the `joining_date` column. The model layer automatically performs schema auto-migration upon startup:
```python
from database.rent_models import init_rent_db
init_rent_db()
```

### Step 2: Running Web Server with Integrated Scheduler
When starting the FastAPI webhook server (`whatsapp_server.py` or `email_server.py`), the `AutomatedRentScheduler` starts automatically in the background via FastAPI lifespan:
```powershell
cd langgraph_agent
uvicorn input_channels.whatsapp_server:app --host 0.0.0.0 --port 8003
```

### Step 3: Standalone CLI / Cron Execution
Alternatively, you can trigger the daily batch workflow on demand or via system cron (`crontab` / Windows Task Scheduler):
```powershell
cd langgraph_agent
python -m app.core_workflows.rent_reminder.scheduler
```

---

## 🧪 4. Automated Verification & Testing

To run the complete test suite:
```powershell
cd langgraph_agent
python -m pytest tests/ -v
```

### Verified Test Cases:
- `test_decision_node_unit_tests`: Validates pure rule decisions for Day 30, Days 31-35 warning, Day 36 escalation, and manual hold skips.
- `test_daily_scheduler_batch_execution`: Validates batch execution across candidates and DB persistence.
- `test_automated_rent_scheduler_service`: Validates async background task initialization and clean shutdown.
- `test_rent_renewal_*_flow`: Validates 5% renewal offer calculation, acceptance, rejection, and negotiation branches.
