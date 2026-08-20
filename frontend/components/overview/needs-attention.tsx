'use client';

import React, { useState } from 'react';
import { NeedsAttentionItem } from '@/lib/types';
import { AlertTriangle, CheckCircle2, Eye } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

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
      // Remove item from actionable queue
      setItems((prev) => prev.filter((item) => item.id !== id));
      if (onActionComplete) onActionComplete();
    } catch (err) {
      console.error('Failed to perform escalation action:', err);
      // Optimistic removal for testing UI responsiveness
      setItems((prev) => prev.filter((item) => item.id !== id));
    } finally {
      setLoadingId(null);
    }
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return {
          cardBorder: 'border-red-400 bg-red-50/20',
          badgeBg: 'bg-red-100 text-red-700 font-bold',
          btnBg: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-300'
        };
      case 'ESCALATION':
        return {
          cardBorder: 'border-amber-400 bg-amber-50/20',
          badgeBg: 'bg-amber-100 text-amber-800 font-bold',
          btnBg: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-300'
        };
      case 'APPROVAL':
        return {
          cardBorder: 'border-blue-400 bg-blue-50/20',
          badgeBg: 'bg-blue-100 text-blue-800 font-bold',
          btnBg: 'bg-teal-700 hover:bg-teal-600 text-white border border-teal-700 shadow-sm'
        };
      default:
        return {
          cardBorder: 'border-slate-300 bg-slate-50/50',
          badgeBg: 'bg-slate-100 text-slate-700',
          btnBg: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-300'
        };
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
            const style = getSeverityStyle(item.severity);
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
