"""
Pydantic Request and Response Schemas — Phase 4 & Phase 5.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field


# ── Error Envelope ────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str = Field(description="Error code identifier")
    message: str = Field(description="Human-readable error explanation")
    status_code: int = Field(description="HTTP status code")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Health & Readiness ────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "elarion-core-api"
    version: str = "2.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ReadinessResponse(BaseModel):
    status: str
    database: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Tenants ───────────────────────────────────────────────────────────────────

class TenantSummaryResponse(BaseModel):
    tenant_id: str
    tenant_name: Optional[str] = None
    property_address: Optional[str] = None
    rent_due_date: Optional[str] = None
    rent_amount: float = 0.0
    payment_status: Optional[str] = "overdue"
    manual_hold: bool = False
    last_reminder_status: Optional[str] = "none"


class TenantDetailResponse(TenantSummaryResponse):
    property_id: Optional[str] = None
    unit_id: Optional[str] = None
    tenant_phone: Optional[str] = None
    phone_or_email: Optional[str] = None
    last_payment_date: Optional[str] = None
    reminder_30_sent_at: Optional[str] = None
    reminder_5_sent_at: Optional[str] = None
    response_received: bool = False
    human_escalated: bool = False
    escalation_reason: Optional[str] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None


class ManualHoldRequest(BaseModel):
    manual_hold: bool = Field(description="Set to true to suppress automated rent reminders, false to resume")


class ManualHoldResponse(BaseModel):
    tenant_id: str
    manual_hold: bool
    message: str


# ── Properties & Units ────────────────────────────────────────────────────────

class PropertyResponse(BaseModel):
    property_id: str
    title: Optional[str] = None
    address: str
    city: Optional[str] = None
    property_type: Optional[str] = None
    price_lakhs: float = 0.0
    created_at: Optional[Any] = None


class UnitResponse(BaseModel):
    unit_id: str
    property_id: str
    unit_number: str
    created_at: Optional[Any] = None


class PropertyDetailResponse(PropertyResponse):
    units: List[UnitResponse] = []


# ── Maintenance Tickets ───────────────────────────────────────────────────────

class TicketCreateRequest(BaseModel):
    tenant_id: str = Field(description="Tenant ID reporting the issue")
    property_id: Optional[str] = Field(default=None, description="Property ID if known")
    unit_id: Optional[str] = Field(default=None, description="Unit ID if known")
    category: str = Field(description="Issue category: plumbing, electrical, hvac, general, security")
    description: str = Field(description="Detailed issue description")
    urgency: str = Field(default="low", description="Urgency: low, medium, high")
    permission_to_enter: str = Field(default="unconfirmed", description="yes, no, unconfirmed")
    pets_present: str = Field(default="unconfirmed", description="yes, no, unconfirmed")
    created_by: Optional[str] = Field(default="api_user")


class TicketResponse(BaseModel):
    ticket_id: str
    tenant_id: Optional[str] = None
    property_id: Optional[str] = None
    unit_id: Optional[str] = None
    category: str
    description: Optional[str] = None
    urgency: Optional[str] = "low"
    status: str = "OPEN"
    vendor_id: Optional[str] = None
    assignment_status: str = "UNASSIGNED"
    created_at: Optional[Any] = None


class TicketStatusLogResponse(BaseModel):
    log_id: int
    ticket_id: str
    old_status: Optional[str] = None
    new_status: str
    timestamp: Optional[Any] = None


class TicketDetailResponse(TicketResponse):
    status_history: List[TicketStatusLogResponse] = []


# ── Workflow Execution ────────────────────────────────────────────────────────

class RentReminderRunResponse(BaseModel):
    status: str = "completed"
    records_scanned: int = 0
    reminders_sent: int = 0
    followups_sent: int = 0
    escalated: int = 0
    skipped: int = 0
    errors: List[str] = []


class RentReminderEvaluateRequest(BaseModel):
    tenant_id: str = Field(description="Tenant ID to evaluate")
    current_date: Optional[str] = Field(default=None, description="Reference date YYYY-MM-DD (defaults to today)")


class RentReminderEvaluateResponse(BaseModel):
    tenant_id: str
    action: str
    last_reminder_status: str
    days_overdue: int
    rent_amount: float
    logs: List[str] = []
    error: Optional[str] = None


class LeaseExpiryScanResponse(BaseModel):
    status: str = "completed"
    scanned: int = 0
    events_created: int = 0
    run_id: str


class RenewalReminderScanResponse(BaseModel):
    status: str = "completed"
    scanned: int = 0
    reminders_sent: int = 0
    run_id: str


# ── FAQ & Master Pipeline ─────────────────────────────────────────────────────

class FAQQueryRequest(BaseModel):
    query: str = Field(description="Question regarding building policy or property search")
    user_id: Optional[str] = Field(default="api_user", description="Identifier for session tracking")


class FAQQueryResponse(BaseModel):
    query: str
    answer: str
    user_id: str


class PipelineMessageRequest(BaseModel):
    channel: str = Field(default="api", description="Channel identifier (api, web, chat)")
    user_id: str = Field(description="Unique tenant or client user identifier")
    text: str = Field(description="Message text to process through the master pipeline")
    channel_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PipelineMessageResponse(BaseModel):
    channel: str
    user_id: str
    final_response: str
    intent: Optional[str] = None
    active_department: Optional[str] = None


# ── Jobs & Alerting (Phase 5) ─────────────────────────────────────────────────

class JobInfoResponse(BaseModel):
    job_name: str
    description: str
    domain: str
    default_cadence: str
    is_locked: bool = False
    last_run: Optional[Dict[str, Any]] = None


class JobRunResponse(BaseModel):
    job_name: str
    status: str
    attempts: int = 1
    duration_ms: Optional[float] = None
    result_summary: Optional[Any] = None
    error: Optional[str] = None


class DeadLetterRecordResponse(BaseModel):
    dead_letter_id: str
    job_name: str
    status: str
    attempts: int
    started_at: str
    failed_at: str
    duration_ms: float
    error_type: str
    error_message: str


class AlertRecordResponse(BaseModel):
    alert_id: str
    alert_type: str
    severity: str
    message: str
    metadata: Dict[str, Any]
    status: str


# ── Dashboard (Phase 7) ───────────────────────────────────────────────────────

class DashboardMetricsResponse(BaseModel):
    total_properties: int = 0
    total_tenants: int = 0
    active_leases: int = 0
    open_maintenance_tickets: int = 0
    open_escalations: int = 0
    outstanding_rent: float = 0.0


# ── Create/Update Envelopes (Phase 7 CRUD) ────────────────────────────────────

class PropertyCreateRequest(BaseModel):
    title: Optional[str] = None
    address: str
    city: Optional[str] = None
    property_type: Optional[str] = None
    price_lakhs: float = 0.0


class PropertyUpdateRequest(BaseModel):
    title: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    property_type: Optional[str] = None
    price_lakhs: Optional[float] = None


class TenantCreateRequest(BaseModel):
    property_id: str
    unit_id: Optional[str] = None
    tenant_name: str
    name: Optional[str] = None
    tenant_phone: Optional[str] = None
    phone_or_email: Optional[str] = None
    property_address: Optional[str] = None
    rent_amount: float
    rent_due_date: date
    payment_status: str = "paid"


class TenantUpdateRequest(BaseModel):
    tenant_name: Optional[str] = None
    name: Optional[str] = None
    tenant_phone: Optional[str] = None
    phone_or_email: Optional[str] = None
    property_address: Optional[str] = None
    rent_amount: Optional[float] = None
    rent_due_date: Optional[date] = None
    payment_status: Optional[str] = None


class TicketUpdateRequest(BaseModel):
    status: Optional[str] = None
    urgency: Optional[str] = None
    assigned_vendor_id: Optional[str] = None
    permission_to_enter: Optional[str] = None
    pets_present: Optional[str] = None


# ── Leases (Phase 7) ──────────────────────────────────────────────────────────

class LeaseResponse(BaseModel):
    lease_id: str
    tenant_id: str
    property_id: str
    unit_id: Optional[str] = None
    lease_start_date: date
    lease_end_date: date
    monthly_rent: float
    status: str
    created_at: Optional[Any] = None


class LeaseExpiryEventResponse(BaseModel):
    id: int
    event_name: str
    lease_id: str
    tenant_id: str
    property_id: str
    expiry_date: date
    days_remaining: int
    window_days: int
    event_date: date
    event_status: str
    created_at: Optional[Any] = None


# ── Renewals (Phase 7) ────────────────────────────────────────────────────────

class RenewalReminderResponse(BaseModel):
    reminder_id: int
    event_id: Optional[int] = None
    lease_id: str
    tenant_id: str
    property_id: Optional[str] = None
    channel: str
    recipient: str
    reminder_type: str
    status: str
    sent_at: Any
    created_at: Optional[Any] = None


class RenewalIntentResponse(BaseModel):
    intent_id: int
    lease_id: str
    tenant_id: str
    tenant_response: str
    intent: str
    confidence: float
    reasoning: Optional[str] = None
    renewal_status: str
    requested_term: Optional[int] = None
    proposed_rent: Optional[float] = None
    created_at: Optional[Any] = None


# ── Escalations (Phase 7) ─────────────────────────────────────────────────────

class EscalationResponse(BaseModel):
    escalation_id: int
    lease_id: str
    tenant_id: str
    property_id: Optional[str] = None
    escalation_reason: str
    escalation_priority: str
    status: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    notified_at: Optional[Any] = None
    manager_action: Optional[str] = None
    manager_notes: Optional[str] = None
    resolved_at: Optional[Any] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None


class EscalationResolveRequest(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    manager_action: Optional[str] = None
    manager_notes: Optional[str] = None


# ── Documents (Phase 7) ───────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    document_id: int
    lease_id: str
    tenant_id: str
    doc_type: str
    file_name: str
    file_url: Optional[str] = None
    status: str
    uploaded_at: Any
    verified_at: Optional[Any] = None
    verified_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[Any] = None

# ── Authentication (Phase 8) ──────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    user_id: str
    email: str
    role: str
    active: bool
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None

class LoginRequest(BaseModel):
    username: str
    password: str


# ── Dashboard Transcripts & UI Aggregations ────────────────────────────────────

class ConversationMessageSchema(BaseModel):
    message_id: int
    sender_type: str
    sender_name: str
    content: str
    system_event: Optional[str] = None
    timestamp: Any

class ConversationSummarySchema(BaseModel):
    conversation_id: str
    tenant_id: Optional[str] = None
    property_id: Optional[str] = None
    property_name: Optional[str] = "Sunset Apartments"
    unit_id: Optional[str] = None
    unit_number: Optional[str] = "204"
    contact_name: str
    channel: str
    intent: Optional[str] = "General Inquiry"
    urgency: Optional[str] = "Normal"
    status: str = "AI Resolved"
    workflow_triggered: Optional[str] = "Resident Support"
    human_intervention: Optional[str] = "None"
    is_reviewed: bool = False
    last_message_at: Any
    created_at: Any

class ConversationDetailSchema(ConversationSummarySchema):
    messages: List[ConversationMessageSchema] = []

class ConversationsListResponse(BaseModel):
    total: int
    items: List[ConversationSummarySchema]
    limit: int
    offset: int

class NeedsAttentionItemSchema(BaseModel):
    id: str
    severity: str
    title: str
    workflow: str
    action_label: str = "Review"

class AgentActivityTodayItemSchema(BaseModel):
    workflow: str
    runs: int
    rate: int

class RecentActivityItemSchema(BaseModel):
    agent: str
    summary: str
    time_str: str

class AutomationStatusItemSchema(BaseModel):
    name: str
    status: str
    badge: str

class OverviewDashboardResponse(BaseModel):
    stats: Dict[str, Any]
    needs_attention: List[NeedsAttentionItemSchema]
    agent_activity_today: List[AgentActivityTodayItemSchema]
    recent_activity: List[RecentActivityItemSchema] = []
    automation_status: List[AutomationStatusItemSchema] = []

class AutomationCardSchema(BaseModel):
    id: str
    name: str
    status: str                       # "Active" | "Inactive"
    description: str
    handles: List[str] = []           # Short action labels displayed in card body
    channels: List[str]
    escalation_conditions: List[str]
    scope: str
    properties_count: Optional[int] = None
    icon_type: Optional[str] = None   # "maintenance" | "rent" | "support" | "lease" | "reporting"
    steps: Optional[List[Dict[str, Any]]] = None


class AutomationUpdateRequest(BaseModel):
    """Request body for PATCH /dashboard/automations/{id}."""
    active: Optional[bool] = None
    status: Optional[str] = None       # "Active" | "Inactive"
    name: Optional[str] = None
    description: Optional[str] = None
    escalation_conditions: Optional[List[str]] = None
    channels: Optional[List[str]] = None
    scope: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None


class AutomationCreateRequest(BaseModel):
    """Request body for POST /dashboard/automations."""
    id: Optional[str] = None
    name: str
    status: Optional[str] = "Active"
    description: Optional[str] = None
    tagline: Optional[str] = None
    handles: Optional[List[str]] = []
    channels: Optional[List[str]] = ["Email", "WhatsApp"]
    escalation_conditions: Optional[List[str]] = []
    scope: Optional[str] = "All Properties (42)"
    properties_count: Optional[int] = 42
    icon_type: Optional[str] = "maintenance"
    steps: Optional[List[Dict[str, Any]]] = None

class AgentActivityResponse(BaseModel):
    metrics: Dict[str, Any]
    workflow_performance: List[Dict[str, Any]]
    recent_executions: List[Dict[str, Any]]


