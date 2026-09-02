import React from 'react';
import { getChannelToken, ChannelType, CHANNEL_TOKENS } from '@/lib/design-tokens';

interface ChannelBadgeProps {
  channel: ChannelType;
  size?: 'sm' | 'md';
}

// Maps raw DB values to display-friendly labels
const DISPLAY_LABELS: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'Email',
  voice: 'Voice',
  web: 'Web',
};

export default function ChannelBadge({ channel, size = 'md' }: ChannelBadgeProps) {
  const token = getChannelToken(channel);
  const displayLabel = DISPLAY_LABELS[channel?.toLowerCase()] ?? channel;
  const sizeClass = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2.5 py-1';
  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-medium ${token.bg} ${token.text} ${sizeClass}`}>
      <span>{token.emoji}</span>
      {displayLabel}
    </span>
  );
}
