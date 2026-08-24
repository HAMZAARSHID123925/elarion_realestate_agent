import {
  OverviewDashboardData,
  ConversationSummary,
  ConversationsListResponse,
  ConversationDetail,
  AutomationCard,
  AgentActivityData
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error [${response.status}]: ${errorText || response.statusText}`);
  }

  return response.json();
}

export const apiClient = {
  // Overview Dashboard
  getOverviewData: async (): Promise<OverviewDashboardData> => {
    return fetchJson<OverviewDashboardData>('/dashboard/overview');
  },

  // Manager Actions (Approve / Review)
  performEscalationAction: async (id: string, action: 'Approve' | 'Review' | 'Resolve'): Promise<{ status: string }> => {
    return fetchJson<{ status: string }>(`/human-escalations/${id}/action`, {
      method: 'POST',
      body: JSON.stringify({ action })
    });
  },

  // Conversations List & Details
  getConversations: async (params?: Record<string, string>): Promise<ConversationsListResponse> => {
    const query = new URLSearchParams(params || {}).toString();
    return fetchJson<ConversationsListResponse>(`/dashboard/conversations?${query}`);
  },

  getConversationDetail: async (id: string): Promise<ConversationDetail> => {
    return fetchJson<ConversationDetail>(`/dashboard/conversations/${id}`);
  },

  markConversationReviewed: async (id: string): Promise<{ status: string }> => {
    return fetchJson<{ status: string }>(`/dashboard/conversations/${id}/review`, {
      method: 'POST'
    });
  },

  // Automations Grid
  getAutomations: async (): Promise<AutomationCard[]> => {
    return fetchJson<AutomationCard[]>('/dashboard/automations');
  },

  toggleAutomation: async (id: string, active: boolean): Promise<{ status: string; active: boolean }> => {
    return fetchJson<{ status: string; active: boolean }>(`/dashboard/automations/${id}?active=${active}`, {
      method: 'PATCH'
    });
  },

  // Agent Activity & Analytics
  getAgentActivity: async (period = 'today'): Promise<AgentActivityData> => {
    return fetchJson<AgentActivityData>(`/dashboard/agent-activity?period=${period}`);
  }
};
