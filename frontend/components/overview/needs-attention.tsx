'use client';

import React, { useState } from 'react';
import { NeedsAttentionItem } from '@/lib/types';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { getSeverityToken } from '@/lib/design-tokens';

interface NeedsAttentionProps {
  items: NeedsAttentionItem[];
  onActionComplete?: () => void;
}

export default function NeedsAttention({ items: initialItems, onActionComplete }: NeedsAttentionProps) {
  const [items, setItems] = useState<NeedsAttentionItem[]>(initialItems);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const handleAction = async (id: string, actionLabel: string) => {
    setLoadingId(id);
    try {
      const action = actionLabel.includes('Approve') ? 'Approve' : 'Review';
      await apiClient.performEscalationAction(id, action);
      setItems((prev) => prev.filter((item) => item.id !== id));
      if (onActionComplete) onActionComplete();
    } catch (err) {
      console.error('Failed to perform escalation action:', err);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <AlertTriangle size={20} className="text-amber-500" />
        <h3 className="text-lg font-bold text-slate-900 tracking-tight">Needs Attention</h3>
      </div>

      {items.length === 0 ? (
        <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-500">
          <CheckCircle2 size={32} className="mx-auto text-emerald-500 mb-2" />
          <p className="font-medium text-sm">All escalated cases are currently resolved!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const style = getSeverityToken(item.severity);
            const isLoading = loadingId === item.id;
            return (
              <div
                key={item.id}
                className={`p-4 rounded-xl border ${style.cardBorder} flex items-center justify-between transition-all bg-white shadow-sm`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2.5">
                    <span className={`text-[10px] uppercase px-2 py-0.5 rounded ${style.badgeBg}`}>
                      {item.severity}
                    </span>
                    <span className="font-bold text-slate-900 text-base">{item.title}</span>
                  </div>
                  <p className="text-xs text-slate-500 font-medium pl-0.5">
                    {item.workflow}
                  </p>
                </div>

                <button
                  onClick={() => handleAction(item.id, item.action_label)}
                  disabled={isLoading}
                  className={`px-5 py-1.5 rounded-lg text-xs font-semibold transition-all ${style.btnBg} ${
                    isLoading ? 'opacity-50 cursor-not-allowed' : 'active:scale-95'
                  }`}
                >
                  {isLoading ? 'Processing...' : item.action_label}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
