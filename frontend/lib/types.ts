export interface OverviewStats {
  conversations: number;
  ai_resolved: number;
  human_escalations: number;
  automation_rate: number;
  avg_response_time_seconds: number;
}

export interface NeedsAttentionItem {
  id: string;
  severity: 'CRITICAL' | 'ESCALATION' | 'APPROVAL' | string;
  title: string;
  workflow: string;
  action_label: string;
}

export interface AgentActivityTodayItem {
  workflow: string;
  runs: number;
  rate: number;
}

export interface RecentActivityItem {
  agent: string;
  summary: string;
  time_str: string;
}

export interface AutomationStatusItem {
  name: string;
  status: string;
  badge?: string;
}

export interface OverviewDashboardData {
  stats: OverviewStats;
  needs_attention: NeedsAttentionItem[];
  agent_activity_today: AgentActivityTodayItem[];
  recent_activity?: RecentActivityItem[];
  automation_status?: AutomationStatusItem[];
}


export interface ConversationSummary {
  conversation_id: string;
  tenant_id?: string;
  property_id?: string;
  property_name?: string;
  unit_id?: string;
  unit_number?: string;
  contact_name: string;
  channel: string;
  intent: string;
  urgency: string;
  status: string;
  workflow_triggered: string;
  human_intervention: string;
  is_reviewed: boolean;
  last_message_at: string;
  created_at: string;
}

export interface ConversationsListResponse {
  total: number;
  items: ConversationSummary[];
  limit: number;
  offset: number;
}

export interface ConversationMessage {
  message_id: number;
  sender_type: 'tenant' | 'ai' | 'system';
  sender_name: string;
  content: string;
  system_event?: string;
  timestamp: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[];
}

export interface WorkflowStepData {
  id: string;
  title: string;
  description: string;
  isAiTask?: boolean;
  isConditional?: boolean;
  isCurrent?: boolean;
}

export interface AutomationCard {
  id: string;
  name: string;
  status: string;                   // "Active" | "Inactive"
  description: string;
  tagline?: string;
  handles: string[];                 // Short handle labels for the card body
  channels: string[];                // ["WhatsApp", "Email", "Voice", "Web"]
  escalation_conditions: string[];   // Bullet list in the amber box
  scope: string;                     // "All Properties (42)" | "3 Properties"
  properties_count?: number;
  icon_type?: string;                // "maintenance" | "rent" | "support" | "lease" | "reporting"
  steps?: WorkflowStepData[];
}

export interface AutomationUpdatePayload {
  active?: boolean;
  status?: string;
  name?: string;
  description?: string;
  escalation_conditions?: string[];
  channels?: string[];
  scope?: string;
  steps?: WorkflowStepData[];
}

export interface AgentActivityData {
  metrics: {
    total_executions: number;
    ai_completed: number;
    human_escalations: number;
    failed: number;
    automation_rate: number;
    rate_change: string;
  };
  workflow_performance: Array<{
    agent: string;
    runs: number;
    ai_resolved: number;
    escalated: number;
    failed: number;
    auto_rate: number;
  }>;
  recent_executions: Array<{
    id: string;
    title: string;
    summary: string;
    status: string;
    badge: string;
    timestamp: string;
  }>;
}


// ── Properties Dashboard ─────────────────────────────────────────────────────

export interface PropertyDashboardCard {
  property_id: string;
  title: string | null;
  address: string | null;
  city: string | null;
  property_type: string | null;
  price_lakhs: number;
  status: 'Active' | 'Inactive' | string;
  units_count: number;
  conversations_count: number;
  maintenance_count: number;
  escalations_count: number;
  active_automations: string[];
  created_at: string | null;
}

export interface PropertyDashboardResponse {
  total: number;
  items: PropertyDashboardCard[];
}

export interface PropertyFilters {
  search: string;
  status: string;
  property_type: string;
  city: string;
}

export interface PropertyCreatePayload {
  title: string;
  address: string;
  city: string;
  property_type: string;
  price_lakhs: number;
  status: string;
  units_count: number;
}
