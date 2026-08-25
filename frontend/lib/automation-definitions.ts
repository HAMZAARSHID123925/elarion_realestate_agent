/**
 * ┌────────────────────────────────────────────────────────────────────┐
 * │  TenantFlow.ai — Automation Definitions                           │
 * │                                                                    │
 * │  Static configuration derived from the actual LangGraph           │
 * │  core_workflows/ graph definitions. Maps automation IDs to:        │
 * │    • Full execution flow steps (from graph.py node sequences)      │
 * │    • Escalation rules (from conditional_edges + priority logic)    │
 * │    • Active integrations (PM software, messaging, telephony)       │
 * │    • Edit schema (which fields the PM can change)                  │
 * │                                                                    │
 * │  Source graphs read:                                               │
 * │    maintenance/graph.py, rent_reminder/graph.py,                   │
 * │    faq/graph.py, rent_renewal/graph.py                             │
 * └────────────────────────────────────────────────────────────────────┘
 */

export interface WorkflowStep {
  id: string;
  title: string;
  description: string;
  isAiTask?: boolean;
  isConditional?: boolean;
  isCurrent?: boolean;
}

export interface EscalationRule {
  id: string;
  icon: 'emergency' | 'uncertainty' | 'approval' | 'resource' | 'time' | 'sentiment' | 'policy';
  label: string;
  description: string;
}

export interface ActiveIntegration {
  id: string;
  name: string;
  initials: string;
  color: string;
  textColor: string;
  connected: boolean;
}

export interface AutomationDefinition {
  id: string;
  name: string;
  status?: string;
  icon_type: string;
  tagline: string;
  handles: string[];
  channels: string[];
  escalation_conditions: string[];
  scope: string;
  properties_count: number;
  steps: WorkflowStep[];
  escalation_rules: EscalationRule[];
  integrations: ActiveIntegration[];
  editable_fields: Array<'active' | 'escalation_conditions' | 'channels'>;
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. MAINTENANCE REQUEST
//    Source: maintenance/graph.py
//    receptionist → issue_collection → priority_detection
//    → [escalation | validation] → request_builder
//    → ticket_creation → vendor_matching → human_approval
//    → vendor_assignment → response_generator
// ─────────────────────────────────────────────────────────────────────────────
const MAINTENANCE: AutomationDefinition = {
  id: 'maintenance_request',
  name: 'Maintenance Request',
  icon_type: 'maintenance',
  tagline: 'End-to-end ticket triage, vendor dispatch, and tenant notification.',
  handles: ['Collect details', 'classify urgency', 'ticket creation', 'vendor assignment'],
  channels: ['WhatsApp', 'Email', 'Voice', 'Web'],
  escalation_conditions: [
    'Emergency detected (e.g., flood)',
    'AI confidence < 85%',
    'Estimate > $500 requires sign-off',
    'Primary vendor unavailable',
  ],
  scope: 'All Properties (42)',
  properties_count: 42,
  steps: [
    { id: 'incoming_request', title: 'Incoming Request', description: 'Triggers via WhatsApp, Email, Voice, or Web chat.' },
    { id: 'identify_tenant', title: 'Identify Tenant & Property', description: 'Receptionist node matches contact info to lease records.' },
    { id: 'classify_intent', title: 'Classify Intent & Detect Urgency', description: 'NLP analysis to categorize issue and flag emergencies.', isAiTask: true, isCurrent: true },
    { id: 'collect_details', title: 'Collect Details & Create Ticket', description: 'Gathers required slots and logs in PM software.' },
    { id: 'assign_vendor', title: 'Assign Vendor & Notify Tenant', description: 'Dispatches work order and sends status update.' },
    { id: 'human_approval', title: 'Human Approval (if needed)', description: 'Estimates >$500 or flagged emergencies require PM sign-off.', isConditional: true },
    { id: 'response_generator', title: 'Generate Final Response', description: 'Sends confirmation to tenant with ticket ID and ETA.' },
  ],
  escalation_rules: [
    { id: 'emergency_keywords', icon: 'emergency', label: 'Emergency Keywords', description: 'Routes immediately to on-call human.' },
    { id: 'ai_uncertainty', icon: 'uncertainty', label: 'AI Uncertainty', description: 'Confidence score < 85% flags for review.' },
    { id: 'approval_required', icon: 'approval', label: 'Approval Required', description: 'Estimates > $500 require PM sign-off.' },
    { id: 'vendor_unavailable', icon: 'resource', label: 'Vendor Unavailable', description: 'Re-routes if primary vendor rejects.' },
  ],
  integrations: [
    { id: 'appfolio', name: 'AppFolio', initials: 'AF', color: 'bg-blue-600', textColor: 'text-white', connected: true },
    { id: 'whatsapp', name: 'WhatsApp', initials: 'WA', color: 'bg-green-500', textColor: 'text-white', connected: true },
    { id: 'twilio', name: 'Twilio', initials: 'TW', color: 'bg-red-500', textColor: 'text-white', connected: true },
  ],
  editable_fields: ['active', 'escalation_conditions', 'channels'],
};

// ─────────────────────────────────────────────────────────────────────────────
// 2. RENT REMINDER
//    Source: rent_reminder/graph.py
//    payment_check → reminder_decision
//    → [reminder_send | human_escalation | END] → followup_tracker
// ─────────────────────────────────────────────────────────────────────────────
const RENT_REMINDER: AutomationDefinition = {
  id: 'rent_reminder',
  name: 'Rent Reminder',
  icon_type: 'rent',
  tagline: 'Automated payment follow-ups, late fee calculation, and tenant disputes.',
  handles: ['Automated follow-ups', 'payment link generation', 'late fee calculation'],
  channels: ['WhatsApp', 'Email', 'SMS'],
  escalation_conditions: ['> 15 days past due', 'Tenant dispute initiated', 'Payment plan request detected'],
  scope: '3 Properties',
  properties_count: 3,
  steps: [
    { id: 'payment_check', title: 'Payment Status Check', description: 'Queries ledger for overdue balances and days-past-due count.' },
    { id: 'reminder_decision', title: 'Reminder Decision Engine', description: 'Determines action: SEND_REMINDER, SEND_FOLLOWUP, ESCALATE, or SKIP.', isAiTask: true, isCurrent: true },
    { id: 'reminder_send', title: 'Send Reminder / Follow-up', description: 'Delivers personalized message with payment link via preferred channel.' },
    { id: 'followup_tracker', title: 'Follow-up Tracker', description: 'Logs attempt count, last contact date, and schedules next nudge.' },
    { id: 'human_escalation', title: 'Human Escalation', description: 'Routes to PM when past 15 days or dispute is raised.', isConditional: true },
  ],
  escalation_rules: [
    { id: 'overdue_threshold', icon: 'time', label: 'Overdue Threshold', description: '> 15 days past due triggers PM review queue.' },
    { id: 'dispute', icon: 'sentiment', label: 'Tenant Dispute', description: 'Detected dispute language pauses automation immediately.' },
    { id: 'ai_uncertainty', icon: 'uncertainty', label: 'AI Uncertainty', description: 'Low-confidence classification flags for human review.' },
  ],
  integrations: [
    { id: 'appfolio', name: 'AppFolio', initials: 'AF', color: 'bg-blue-600', textColor: 'text-white', connected: true },
    { id: 'stripe', name: 'Stripe', initials: 'ST', color: 'bg-violet-600', textColor: 'text-white', connected: true },
    { id: 'twilio', name: 'Twilio', initials: 'TW', color: 'bg-red-500', textColor: 'text-white', connected: true },
  ],
  editable_fields: ['active', 'escalation_conditions', 'channels'],
};

// ─────────────────────────────────────────────────────────────────────────────
// 3. RESIDENT SUPPORT (FAQ)
//    Source: faq/graph.py
//    classify_intent → [rag_retrieve | collect_property_slots | clarify]
//    → rag_generate → compose_response
// ─────────────────────────────────────────────────────────────────────────────
const RESIDENT_SUPPORT: AutomationDefinition = {
  id: 'resident_support',
  name: 'Resident Support',
  icon_type: 'support',
  tagline: 'General FAQ, community rules, and amenity booking assistance.',
  handles: ['General FAQ', 'community rules', 'amenity booking assistance'],
  channels: ['WhatsApp', 'Web', 'Email'],
  escalation_conditions: ['Complex policy questions', 'Frustration sentiment detected', 'Multiple clarification loops'],
  scope: 'All Properties (42)',
  properties_count: 42,
  steps: [
    { id: 'classify_intent', title: 'Classify Intent', description: 'Determines if query is KNOWLEDGE, PROPERTY, MIXED, or UNCLEAR.', isAiTask: true, isCurrent: true },
    { id: 'rag_retrieve', title: 'RAG Knowledge Retrieve', description: 'Searches vector knowledge base for matching FAQ content.' },
    { id: 'rag_generate', title: 'RAG Answer Generation', description: 'LLM generates a grounded answer from retrieved documents.', isAiTask: true },
    { id: 'property_slots', title: 'Collect Property Slots', description: 'For MIXED / PROPERTY queries: gathers building, unit, and amenity details.', isConditional: true },
    { id: 'call_property_mcp', title: 'Query Property MCP', description: 'Calls live property data API for real-time availability and rules.' },
    { id: 'compose_response', title: 'Compose & Send Response', description: 'Merges knowledge answer + property data and delivers to resident.' },
  ],
  escalation_rules: [
    { id: 'complex_policy', icon: 'policy', label: 'Complex Policy Questions', description: 'Routes to human when answer confidence is low.' },
    { id: 'frustration', icon: 'sentiment', label: 'Frustration Detected', description: 'Negative sentiment triggers immediate PM hand-off.' },
    { id: 'clarification_loops', icon: 'uncertainty', label: 'Clarification Loops', description: 'More than 2 UNCLEAR classifications in a session escalates.' },
  ],
  integrations: [
    { id: 'pinecone', name: 'Pinecone', initials: 'PC', color: 'bg-teal-500', textColor: 'text-white', connected: true },
    { id: 'whatsapp', name: 'WhatsApp', initials: 'WA', color: 'bg-green-500', textColor: 'text-white', connected: true },
    { id: 'openai', name: 'OpenAI', initials: 'AI', color: 'bg-slate-800', textColor: 'text-white', connected: true },
  ],
  editable_fields: ['active', 'escalation_conditions', 'channels'],
};

// ─────────────────────────────────────────────────────────────────────────────
// 4. LEASE RENEWAL
//    Source: rent_renewal/graph.py
//    lease_check → renewal_reminder_decision → renewal_reminder_send
//    → intent_classification → manager_notification
//    → document_check → document_verification → renewal_tracker
// ─────────────────────────────────────────────────────────────────────────────
const LEASE_RENEWAL: AutomationDefinition = {
  id: 'lease_renewal',
  name: 'Lease Renewal',
  icon_type: 'lease',
  tagline: 'Document collection, signature chasing, and pre-renewal intent checks.',
  handles: ['Document collection', 'signature chasing', 'pre-renewal intent checks'],
  channels: ['Email', 'WhatsApp', 'Web'],
  escalation_conditions: ['Tenant declines renewal', 'Documents missing after deadline', 'Negotiation requested'],
  scope: 'All Properties (42)',
  properties_count: 42,
  steps: [
    { id: 'lease_check', title: 'Lease Expiry Check', description: 'Scans all active leases for upcoming expiry dates (30/60/90-day windows).' },
    { id: 'renewal_reminder', title: 'Send Renewal Reminder', description: 'Delivers personalized renewal invitation via preferred channel.' },
    { id: 'intent_classification', title: 'Classify Renewal Intent', description: 'AI determines: YES, NO, NEGOTIATION, or UNCLEAR from tenant reply.', isAiTask: true, isCurrent: true },
    { id: 'manager_notification', title: 'Manager Notification (HITL)', description: 'Creates review task in PM software when YES or NEGOTIATION.', isConditional: true },
    { id: 'document_check', title: 'Document Collection Check', description: 'Tracks checklist: ID, income proof, lease signature.' },
    { id: 'document_verification', title: 'Document Verification', description: 'Validates submitted documents and updates lease status.' },
    { id: 'renewal_tracker', title: 'Renewal Status Tracker', description: 'Finalizes state: RENEWED, DECLINED, or IN_PROGRESS.' },
  ],
  escalation_rules: [
    { id: 'decline', icon: 'sentiment', label: 'Tenant Declines', description: 'NO intent triggers PM notification for unit re-listing.' },
    { id: 'document_deadline', icon: 'time', label: 'Document Deadline Missed', description: 'Missing docs after 7 days flags for human follow-up.' },
    { id: 'negotiation', icon: 'approval', label: 'Negotiation Requested', description: 'NEGOTIATION intent always requires PM sign-off.' },
    { id: 'ai_uncertainty', icon: 'uncertainty', label: 'Unclear Intent', description: 'Repeated UNCLEAR classifications escalate to PM review.' },
  ],
  integrations: [
    { id: 'appfolio', name: 'AppFolio', initials: 'AF', color: 'bg-blue-600', textColor: 'text-white', connected: true },
    { id: 'docusign', name: 'DocuSign', initials: 'DS', color: 'bg-amber-500', textColor: 'text-white', connected: true },
    { id: 'whatsapp', name: 'WhatsApp', initials: 'WA', color: 'bg-green-500', textColor: 'text-white', connected: true },
  ],
  editable_fields: ['active', 'escalation_conditions', 'channels'],
};

// ─────────────────────────────────────────────────────────────────────────────
// 5. OWNER REPORTING
//    (modeled from card screenshot description — no graph.py found)
// ─────────────────────────────────────────────────────────────────────────────
const OWNER_REPORTING: AutomationDefinition = {
  id: 'owner_reporting',
  name: 'Owner Reporting',
  icon_type: 'reporting',
  tagline: 'Automated monthly portfolio reports with variance analysis and delivery.',
  handles: ['Automated monthly portfolio generation', 'variance explanations'],
  channels: ['Email', 'Web Portal'],
  escalation_conditions: ['Occupancy variance > 10%', 'Maintenance cost spike detected', 'Owner requests custom period'],
  scope: 'All Properties (42)',
  properties_count: 42,
  steps: [
    { id: 'schedule_trigger', title: 'Schedule Trigger', description: 'Fires on the 1st of each month (or on-demand by PM).' },
    { id: 'portfolio_fetch', title: 'Portfolio Data Fetch', description: 'Pulls occupancy, income, maintenance, and expense data from PM system.' },
    { id: 'variance_analysis', title: 'Variance Analysis', description: 'AI computes month-over-month deltas and flags anomalies.', isAiTask: true, isCurrent: true },
    { id: 'report_generation', title: 'Report Generation', description: 'Compiles branded PDF with charts, KPIs, and AI narrative summary.', isAiTask: true },
    { id: 'owner_delivery', title: 'Owner Delivery', description: 'Emails report and posts to owner web portal with audit trail.' },
    { id: 'anomaly_escalation', title: 'Anomaly Escalation (if needed)', description: 'Significant variances trigger PM review before delivery.', isConditional: true },
  ],
  escalation_rules: [
    { id: 'occupancy_variance', icon: 'emergency', label: 'Occupancy Variance', description: '> 10% drop in occupancy triggers PM notification.' },
    { id: 'cost_spike', icon: 'approval', label: 'Cost Spike Detected', description: 'Maintenance costs 2× above average flagged for review.' },
    { id: 'custom_request', icon: 'policy', label: 'Custom Report Request', description: 'Owner requests always routed through PM for approval.' },
  ],
  integrations: [
    { id: 'appfolio', name: 'AppFolio', initials: 'AF', color: 'bg-blue-600', textColor: 'text-white', connected: true },
    { id: 'sendgrid', name: 'SendGrid', initials: 'SG', color: 'bg-cyan-500', textColor: 'text-white', connected: true },
    { id: 'openai', name: 'OpenAI', initials: 'AI', color: 'bg-slate-800', textColor: 'text-white', connected: true },
  ],
  editable_fields: ['active', 'escalation_conditions'],
};

// ─────────────────────────────────────────────────────────────────────────────
// Registry — O(1) lookup by automation ID
// ─────────────────────────────────────────────────────────────────────────────
export const AUTOMATION_DEFINITIONS: Record<string, AutomationDefinition> = {
  maintenance_request: MAINTENANCE,
  rent_reminder: RENT_REMINDER,
  resident_support: RESIDENT_SUPPORT,
  lease_renewal: LEASE_RENEWAL,
  owner_reporting: OWNER_REPORTING,
};

export function getAutomationDefinition(id: string): AutomationDefinition | null {
  return AUTOMATION_DEFINITIONS[id] ?? null;
}

export const ALL_AUTOMATIONS: AutomationDefinition[] = [
  MAINTENANCE,
  RENT_REMINDER,
  RESIDENT_SUPPORT,
  LEASE_RENEWAL,
  OWNER_REPORTING,
];
