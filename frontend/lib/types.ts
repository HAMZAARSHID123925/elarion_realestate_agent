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

export interface AutomationCard {
  id: string;
  name: string;
  status: string;
  description: string;
  channels: string[];
  escalation_conditions: string[];
  scope: string;
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
