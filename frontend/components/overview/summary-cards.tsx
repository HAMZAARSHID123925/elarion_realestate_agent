'use client';

import React from 'react';
import { OverviewStats } from '@/lib/types';
import { Sparkles, ArrowUpRight } from 'lucide-react';

interface SummaryCardsProps {
  stats: OverviewStats;
}

export default function SummaryCards({ stats }: SummaryCardsProps) {
  return (
    <div className="grid grid-cols-5 gap-4">
      {/* 1. CONVERSATIONS */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-2">
          Conversations
        </span>
        <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
          {stats.conversations}
        </div>
      </div>

      {/* 2. AI RESOLVED */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
        <div className="flex items-center gap-1.5 mb-2">
          <Sparkles size={14} className="text-emerald-500" />
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            AI Resolved
          </span>
        </div>
        <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
          {stats.ai_resolved}
        </div>
      </div>

      {/* 3. HUMAN ESCALATIONS */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-2">
          Human Escalations
        </span>
        <div className="text-3xl font-extrabold text-amber-500 tracking-tight">
          {stats.human_escalations}
        </div>
      </div>

      {/* 4. AUTOMATION RATE */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-2">
          Automation Rate
        </span>
        <div className="text-3xl font-extrabold text-emerald-500 tracking-tight flex items-baseline gap-1">
          <span>{stats.automation_rate}%</span>
        </div>
      </div>

      {/* 5. AVG. RESPONSE TIME */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-2">
          Avg. Response Time
        </span>
        <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
          {stats.avg_response_time_seconds} sec
        </div>
      </div>
    </div>
  );
}
