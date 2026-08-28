# Maintenance Workflow Architecture

> **Document Path:** `docs/SDD/Maintenance_Workflow_Architecture.md`
> **Status:** Active Architectural Reference
> **Domain:** Maintenance & Repair Intake

---

## 1. Domain Purpose

The **Maintenance Workflow** (`langgraph_agent/app/core_workflows/maintenance/`) handles tenant maintenance requests, emergency triage, conversational slot filling, automated vendor matching, and human-in-the-loop manager approval.

---

## 2. Workflow State & Nodes

### State Schema (`MaintenanceState`)
* `messages`: Conversation history
* `tenant_identity`: Verified tenant name / phone
* `property_unit`: Associated property ID and unit number
* `issue_category`: Category (`plumbing`, `electrical`, `hvac`, `general`)
* `issue_description`: Extracted complaint details
* `urgency`: Assessed severity (`EMERGENCY`, `HIGH`, `MEDIUM`, `LOW`)
* `permission_to_enter`: Tenant consent (`YES`, `NO`, `SCHEDULE_ONLY`)
* `pets_present`: Animal status (`YES`, `NO`)
* `missing_slots`: List of uncollected slots
* `created_ticket_id`: Unique generated ticket identifier
* `assignment_status`: `ASSIGNED`, `NEEDS_MANUAL_ASSIGNMENT`, `UNASSIGNED`

### Node Flow & Graph Architecture
```text
                       [ Inbound Message ]
                                ↓
                     [ slot_extraction_node ]
                                ↓
                     Are all slots collected?
                       ├── NO  ──► [ conversational_followup_node ] ──► END (Wait for reply)
                       └── YES ──► [ emergency_triage_node ]
                                         ↓
                                 Is it an Emergency?
                                   ├── YES ──► [ emergency_dispatch_node ] ──► [ ticket_creation_node ]
                                   └── NO  ──► [ vendor_matching_node ]
                                                     ↓
                                             Is vendor contracted?
                                               ├── YES ──► [ ticket_creation_node ]
                                               └── NO  ──► [ human_approval_node ] (interrupt)
                                                                 ↓
                                                           [ ticket_creation_node ]
                                                                 ↓
                                                                END
```

---

## 3. Database Persistence

Managed in PostgreSQL via Migration `000_init_base_tables.sql`:
* `vendors`: Registered contractors with categories, service areas, capacity, and contracted properties.
* `maintenance_tickets`: Primary ticket records linked to `tenants`, `properties`, and `units`.
* `ticket_status_log`: Append-only transition history (`OPEN`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`).
* `assignment_attempts`: Audit trail of matching strategies (`CONTRACTED`, `LOCATION_BASED`, `FALLBACK_POOL`).
