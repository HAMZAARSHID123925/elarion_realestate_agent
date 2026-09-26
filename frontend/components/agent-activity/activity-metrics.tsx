'use client';

import React from 'react';
import { Activity, Sparkles, AlertTriangle, CheckCircle2, TrendingUp } from 'lucide-react';

interface MetricsProps {
  metrics: {
    total_executions: number;
    ai_completed: number;
    human_escalations: number;
    failed: number;
    automation_rate: number;
    rate_change: string;
  };
}

export default function ActivityMetrics({ metrics }: MetricsProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Total Executions */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Total Executions
          </span>
          <div className="w-8 h-8 rounded-lg bg-teal-50 flex items-center justify-center text-teal-600">
            <Activity size={16} />
          </div>
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {metrics.total_executions}
          </span>
          <span className="inline-flex items-center gap-0.5 text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
            <TrendingUp size={12} />
            {metrics.rate_change}
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-1 font-medium">
          Workflow turns processed across all channels
        </p>
      </div>

      {/* 2. AI Completed */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            AI Completed
          </span>
          <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600">
            <Sparkles size={16} />
          </div>
        </div>
        <div className="mt-2">
          <span className="text-3xl font-extrabold text-emerald-600 tracking-tight">
            {metrics.ai_completed}
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-1 font-medium">
          Resolved 100% autonomously without human staff
        </p>
      </div>

      {/* 3. Human Escalations */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Human Escalations
          </span>
          <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
            <AlertTriangle size={16} />
          </div>
        </div>
        <div className="mt-2">
          <span className="text-3xl font-extrabold text-amber-500 tracking-tight">
            {metrics.human_escalations}
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-1 font-medium">
          Handoffs to manager for emergency or custom review
        </p>
      </div>

      {/* 4. Autonomous Resolution Rate */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Autonomous Rate
          </span>
          <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
            <CheckCircle2 size={16} />
          </div>
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {metrics.automation_rate}%
          </span>
        </div>
        {/* Visual Progress Bar */}
        <div className="w-full bg-slate-100 rounded-full h-2 mt-2 overflow-hidden">
          <div
            className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${Math.min(100, Math.max(0, metrics.automation_rate))}%` }}
          />
        </div>
      </div>
    </div>
  );
}
