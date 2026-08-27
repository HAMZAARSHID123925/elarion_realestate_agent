import React from 'react';
import { getChannelToken, ChannelType } from '@/lib/design-tokens';

interface ChannelBadgeProps {
  channel: ChannelType;
  size?: 'sm' | 'md';
}

export default function ChannelBadge({ channel, size = 'md' }: ChannelBadgeProps) {
  const token = getChannelToken(channel);
  const sizeClass = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2.5 py-1';
  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-medium ${token.bg} ${token.text} ${sizeClass}`}>
      <span>{token.emoji}</span>
      {channel}
    </span>
  );
}
