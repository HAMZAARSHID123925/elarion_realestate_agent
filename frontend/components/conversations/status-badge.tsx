import React from 'react';
import { getStatusToken, ConversationStatus } from '@/lib/design-tokens';
import { Sparkles, ArrowUpRight, Clock, Eye } from 'lucide-react';

interface StatusBadgeProps {
  status: ConversationStatus;
  size?: 'sm' | 'md';
}

const STATUS_ICONS: Record<string, React.ElementType> = {
  'AI Resolved': Sparkles,
  'Escalated': ArrowUpRight,
  'In Progress': Clock,
  'Pending Review': Eye,
};

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const token = getStatusToken(status);
  const Icon = STATUS_ICONS[status] ?? Sparkles;
  const sizeClass = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2.5 py-1';
  const iconSize = size === 'sm' ? 10 : 12;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-semibold ${token.bg} ${token.text} ${sizeClass}`}>
      <Icon size={iconSize} className={token.iconColor} />
      {status}
    </span>
  );
}
