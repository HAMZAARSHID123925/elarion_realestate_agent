/**
 * ┌─────────────────────────────────────────────────────────────┐
 * │  TenantFlow.ai — Centralized Design Token System            │
 * │                                                             │
 * │  SINGLE SOURCE OF TRUTH for all semantic colors.            │
 * │  To retheme the entire app, change values in this file.     │
 * │  Never hardcode Tailwind color classes in components.       │
 * └─────────────────────────────────────────────────────────────┘
 */

// ── Urgency Level Tokens ──────────────────────────────────────────────────────
export type UrgencyLevel = 'Critical' | 'High' | 'Normal' | 'Low' | string;

export const URGENCY_TOKENS: Record<string, {
  bg: string;
  text: string;
  dot: string;
  border: string;
}> = {
  Critical: {
    bg: 'bg-red-100',
    text: 'text-red-700',
    dot: 'bg-red-500',
    border: 'border-red-300',
  },
  High: {
    bg: 'bg-amber-100',
    text: 'text-amber-700',
    dot: 'bg-amber-500',
    border: 'border-amber-300',
  },
  Normal: {
    bg: 'bg-slate-100',
    text: 'text-slate-600',
    dot: 'bg-slate-400',
    border: 'border-slate-300',
  },
  Low: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    dot: 'bg-emerald-400',
    border: 'border-emerald-200',
  },
  // Catch-all fallback
  _default: {
    bg: 'bg-slate-100',
    text: 'text-slate-600',
    dot: 'bg-slate-400',
    border: 'border-slate-300',
  },
};

export function getUrgencyToken(urgency: UrgencyLevel) {
  return URGENCY_TOKENS[urgency] ?? URGENCY_TOKENS['_default'];
}


// ── Conversation Status Tokens ────────────────────────────────────────────────
export type ConversationStatus =
  | 'AI Resolved'
  | 'Escalated'
  | 'In Progress'
  | 'Pending Review'
  | string;

export const STATUS_TOKENS: Record<string, {
  bg: string;
  text: string;
  iconColor: string;
}> = {
  'AI Resolved': {
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    iconColor: 'text-emerald-500',
  },
  Escalated: {
    bg: 'bg-amber-100',
    text: 'text-amber-700',
    iconColor: 'text-amber-500',
  },
  'In Progress': {
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    iconColor: 'text-blue-500',
  },
  'Pending Review': {
    bg: 'bg-slate-100',
    text: 'text-slate-600',
    iconColor: 'text-slate-400',
  },
  _default: {
    bg: 'bg-slate-100',
    text: 'text-slate-600',
    iconColor: 'text-slate-400',
  },
};

export function getStatusToken(status: ConversationStatus) {
  return STATUS_TOKENS[status] ?? STATUS_TOKENS['_default'];
}


// ── Channel Tokens ────────────────────────────────────────────────────────────
export type ChannelType = 'WhatsApp' | 'Email' | 'Voice' | 'Web' | string;

export const CHANNEL_TOKENS: Record<string, {
  bg: string;
  text: string;
  emoji: string;
}> = {
  WhatsApp: {
    bg: 'bg-green-50',
    text: 'text-green-700',
    emoji: '💬',
  },
  Email: {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    emoji: '✉️',
  },
  Voice: {
    bg: 'bg-violet-50',
    text: 'text-violet-700',
    emoji: '🎙️',
  },
  Web: {
    bg: 'bg-sky-50',
    text: 'text-sky-700',
    emoji: '🌐',
  },
  _default: {
    bg: 'bg-slate-50',
    text: 'text-slate-600',
    emoji: '💬',
  },
};

export function getChannelToken(channel: ChannelType) {
  return CHANNEL_TOKENS[channel] ?? CHANNEL_TOKENS['_default'];
}


// ── Severity Tokens (for Needs Attention cards) ───────────────────────────────
export const SEVERITY_TOKENS: Record<string, {
  cardBorder: string;
  badgeBg: string;
  btnBg: string;
}> = {
  CRITICAL: {
    cardBorder: 'border-red-400 bg-red-50/20',
    badgeBg: 'bg-red-100 text-red-700 font-bold',
    btnBg: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-300',
  },
  ESCALATION: {
    cardBorder: 'border-amber-400 bg-amber-50/20',
    badgeBg: 'bg-amber-100 text-amber-800 font-bold',
    btnBg: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-300',
  },
  APPROVAL: {
    cardBorder: 'border-blue-400 bg-blue-50/20',
    badgeBg: 'bg-blue-100 text-blue-800 font-bold',
    btnBg: 'bg-teal-700 hover:bg-teal-600 text-white border border-teal-700 shadow-sm',
  },
  _default: {
    cardBorder: 'border-slate-300 bg-slate-50/50',
    badgeBg: 'bg-slate-100 text-slate-700',
    btnBg: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-300',
  },
};

export function getSeverityToken(severity: string) {
  return SEVERITY_TOKENS[severity?.toUpperCase()] ?? SEVERITY_TOKENS['_default'];
}


// ── Message Sender Tokens (Conversation Transcript) ───────────────────────────
export const SENDER_TOKENS = {
  tenant: {
    bubbleBg: 'bg-slate-100',
    bubbleText: 'text-slate-800',
    nameBadgeBg: 'bg-slate-200',
    align: 'items-start',
  },
  ai: {
    bubbleBg: 'bg-emerald-50 border border-emerald-100',
    bubbleText: 'text-slate-800',
    nameBadgeBg: 'bg-emerald-100 text-emerald-700',
    align: 'items-end',
  },
  system: {
    bubbleBg: 'bg-amber-50 border border-amber-200 border-dashed',
    bubbleText: 'text-amber-800 italic text-xs',
    nameBadgeBg: 'bg-amber-100 text-amber-700',
    align: 'items-center',
  },
} as const;

export function getSenderToken(senderType: 'tenant' | 'ai' | 'system') {
  return SENDER_TOKENS[senderType] ?? SENDER_TOKENS.tenant;
}


// ── Brand / Layout Palette (mirrors tailwind.config.js for JS usage) ──────────
export const BRAND = {
  primary: '#10B981',    // emerald-500
  teal: '#0D9488',       // teal-600
  sidebar: '#1E293B',    // slate-800
  sidebarActive: '#0F172A',
  bodyBg: '#F8FAFC',
  cardBg: '#FFFFFF',
  border: '#E2E8F0',
} as const;


// ── Automation Type Tokens ────────────────────────────────────────────────────
export type AutomationIconType =
  | 'maintenance'
  | 'rent'
  | 'support'
  | 'lease'
  | 'reporting'
  | string;

export const AUTOMATION_TOKENS: Record<string, {
  cardAccent: string;       // top border color class
  iconBg: string;           // icon wrapper background
  iconColor: string;        // icon fill color
  badgeBg: string;          // active badge bg
  badgeText: string;        // active badge text
  stepColor: string;        // timeline step accent color
  aiTaskBg: string;         // "AI TASK" pill bg
  aiTaskText: string;       // "AI TASK" pill text
}> = {
  maintenance: {
    cardAccent: 'border-t-teal-500',
    iconBg: 'bg-teal-50',
    iconColor: 'text-teal-600',
    badgeBg: 'bg-emerald-100',
    badgeText: 'text-emerald-700',
    stepColor: 'text-teal-600',
    aiTaskBg: 'bg-emerald-100',
    aiTaskText: 'text-emerald-700',
  },
  rent: {
    cardAccent: 'border-t-amber-500',
    iconBg: 'bg-amber-50',
    iconColor: 'text-amber-600',
    badgeBg: 'bg-emerald-100',
    badgeText: 'text-emerald-700',
    stepColor: 'text-amber-600',
    aiTaskBg: 'bg-amber-100',
    aiTaskText: 'text-amber-700',
  },
  support: {
    cardAccent: 'border-t-blue-500',
    iconBg: 'bg-blue-50',
    iconColor: 'text-blue-600',
    badgeBg: 'bg-emerald-100',
    badgeText: 'text-emerald-700',
    stepColor: 'text-blue-600',
    aiTaskBg: 'bg-blue-100',
    aiTaskText: 'text-blue-700',
  },
  lease: {
    cardAccent: 'border-t-violet-500',
    iconBg: 'bg-violet-50',
    iconColor: 'text-violet-600',
    badgeBg: 'bg-emerald-100',
    badgeText: 'text-emerald-700',
    stepColor: 'text-violet-600',
    aiTaskBg: 'bg-violet-100',
    aiTaskText: 'text-violet-700',
  },
  reporting: {
    cardAccent: 'border-t-rose-500',
    iconBg: 'bg-rose-50',
    iconColor: 'text-rose-600',
    badgeBg: 'bg-emerald-100',
    badgeText: 'text-emerald-700',
    stepColor: 'text-rose-600',
    aiTaskBg: 'bg-rose-100',
    aiTaskText: 'text-rose-700',
  },
  _default: {
    cardAccent: 'border-t-slate-400',
    iconBg: 'bg-slate-50',
    iconColor: 'text-slate-600',
    badgeBg: 'bg-emerald-100',
    badgeText: 'text-emerald-700',
    stepColor: 'text-slate-500',
    aiTaskBg: 'bg-slate-100',
    aiTaskText: 'text-slate-600',
  },
};

export function getAutomationToken(iconType: AutomationIconType) {
  return AUTOMATION_TOKENS[iconType] ?? AUTOMATION_TOKENS['_default'];
}


// ── Property Status Tokens ────────────────────────────────────────────────────
export type PropertyStatus = 'Active' | 'Inactive' | string;

export const PROPERTY_STATUS_TOKENS: Record<string, {
  bg: string;
  text: string;
  dot: string;
  border: string;
}> = {
  Active: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    dot: 'bg-emerald-500',
    border: 'border-emerald-200',
  },
  Inactive: {
    bg: 'bg-slate-100',
    text: 'text-slate-500',
    dot: 'bg-slate-400',
    border: 'border-slate-300',
  },
  _default: {
    bg: 'bg-slate-100',
    text: 'text-slate-600',
    dot: 'bg-slate-400',
    border: 'border-slate-300',
  },
};

export function getPropertyStatusToken(status: PropertyStatus) {
  return PROPERTY_STATUS_TOKENS[status] ?? PROPERTY_STATUS_TOKENS['_default'];
}


// ── Property Type Tokens ──────────────────────────────────────────────────────
export type PropertyType = 'house' | 'apartment' | 'plot' | 'commercial' | string;

export const PROPERTY_TYPE_TOKENS: Record<string, {
  iconBg: string;
  iconColor: string;
  label: string;
}> = {
  house: {
    iconBg: 'bg-blue-50',
    iconColor: 'text-blue-600',
    label: 'House',
  },
  apartment: {
    iconBg: 'bg-violet-50',
    iconColor: 'text-violet-600',
    label: 'Apartment',
  },
  plot: {
    iconBg: 'bg-amber-50',
    iconColor: 'text-amber-600',
    label: 'Plot',
  },
  commercial: {
    iconBg: 'bg-rose-50',
    iconColor: 'text-rose-600',
    label: 'Commercial',
  },
  _default: {
    iconBg: 'bg-slate-50',
    iconColor: 'text-slate-600',
    label: 'Property',
  },
};

export function getPropertyTypeToken(type: PropertyType) {
  return PROPERTY_TYPE_TOKENS[type] ?? PROPERTY_TYPE_TOKENS['_default'];
}
