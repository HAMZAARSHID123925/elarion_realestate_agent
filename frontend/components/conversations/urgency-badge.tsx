import React from 'react';
import { getUrgencyToken, UrgencyLevel } from '@/lib/design-tokens';

interface UrgencyBadgeProps {
  urgency: UrgencyLevel;
  size?: 'sm' | 'md';
}

export default function UrgencyBadge({ urgency, size = 'md' }: UrgencyBadgeProps) {
  const token = getUrgencyToken(urgency);
  const sizeClass = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2.5 py-1';
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold ${token.bg} ${token.text} ${sizeClass}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${token.dot}`} />
      {urgency}
    </span>
  );
}
