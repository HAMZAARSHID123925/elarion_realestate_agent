'use client';

import React from 'react';
import { X, CheckCircle2, AlertCircle, XCircle, Clock, MessageSquare, Building2, User, ShieldCheck, Terminal } from 'lucide-react';

interface ExecutionDetail {
  id: string;
  title: string;
  summary: string;
  status: string;
  badge: string;
  timestamp: string;
  channel?: string;
  tenant_name?: string;
  property_name?: string;
  unit_number?: string;
  urgency?: string;
  human_intervention?: string;
}

interface DrawerProps {
  execution: ExecutionDetail | null;
  onClose: () => void;
}

export default function ActivityDetailDrawer({ execution, onClose }: DrawerProps) {
  if (!execution) return null;

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes('resolved') || s.includes('complete')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 size={13} />
          AI Resolved
        </span>
      );
    }
    if (s.includes('escalat')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
          <AlertCircle size={13} />
          Human Escalation
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
        <XCircle size={13} />
        {status}
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-sm flex justify-end transition-opacity">
      <div className="w-full max-w-lg bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 overflow-y-auto animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-6 border-b border-slate-200 flex items-start justify-between bg-slate-50/70">
          <div>
            <div className="flex items-center gap-2 mb-2">
              {getStatusBadge(execution.status)}
              <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-200/80 text-slate-700">
                {execution.badge}
              </span>
            </div>
            <h2 className="text-lg font-extrabold text-slate-900 tracking-tight">
              {execution.title}
            </h2>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Ref ID: {execution.id}
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-lg transition-all"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6 flex-1 text-sm text-slate-700">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200/70 text-xs">
            <div className="flex items-center gap-2">
              <User size={14} className="text-slate-400" />
              <div>
                <span className="text-slate-400 block text-[10px] font-bold uppercase">Contact</span>
                <span className="font-semibold text-slate-900">{execution.tenant_name || 'Resident'}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Building2 size={14} className="text-slate-400" />
              <div>
                <span className="text-slate-400 block text-[10px] font-bold uppercase">Unit & Property</span>
                <span className="font-semibold text-slate-900">
                  {execution.unit_number ? `${execution.unit_number} • ` : ''}{execution.property_name || 'Elarion Heights'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <MessageSquare size={14} className="text-slate-400" />
              <div>
                <span className="text-slate-400 block text-[10px] font-bold uppercase">Channel</span>
                <span className="font-semibold text-slate-900">{execution.channel || 'WhatsApp'}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Clock size={14} className="text-slate-400" />
              <div>
                <span className="text-slate-400 block text-[10px] font-bold uppercase">Timestamp</span>
                <span className="font-semibold text-slate-900">{execution.timestamp}</span>
              </div>
            </div>
          </div>

          {/* Action Transcript / Summary */}
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              Autonomous Turn & Response
            </h4>
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-2">
              <p className="text-slate-800 leading-relaxed font-medium">
                {execution.summary}
              </p>
            </div>
          </div>

          {/* Operational Status & Escalation Flag */}
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              Manager Intervention Context
            </h4>
            <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <ShieldCheck size={16} className="text-teal-600" />
                <span className="text-xs font-semibold text-slate-700">
                  Intervention Level: {execution.human_intervention || 'None'}
                </span>
              </div>
              <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                execution.urgency?.toLowerCase() === 'critical'
                  ? 'bg-rose-100 text-rose-700'
                  : 'bg-slate-200/70 text-slate-700'
              }`}>
                Urgency: {execution.urgency || 'Normal'}
              </span>
            </div>
          </div>

          {/* Developer / Operations Telemetry Section */}
          <div className="border-t border-slate-200 pt-5">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-2.5">
              <Terminal size={13} />
              AI Operations Pipeline Trace
            </h4>
            <div className="p-3 rounded-lg bg-slate-900 text-slate-300 font-mono text-[11px] space-y-1.5">
              <div className="text-slate-400">// LangGraph 5-Layer AI Architecture</div>
              <div><span className="text-teal-400">Layer 1:</span> {execution.channel || 'Inbound Channel'} Adapter</div>
              <div><span className="text-teal-400">Layer 2:</span> Orchestration Intent & Urgency Classifier</div>
              <div><span className="text-teal-400">Layer 3:</span> {execution.badge} Subgraph Execution</div>
              <div><span className="text-teal-400">Layer 4:</span> PostgreSQL Checkpoint & Neon DB Synced</div>
              <div><span className="text-teal-400">Status:</span> 200 OK — Audit Event Committed</div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-bold text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 rounded-xl transition-all shadow-sm"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
