'use client';

import React from 'react';
import { Users, RefreshCw } from 'lucide-react';

interface ActivityHeaderProps {
  period: string;
  onPeriodChange: (period: string) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export default function ActivityHeader({
  period,
  onPeriodChange,
  onRefresh,
  isLoading
}: ActivityHeaderProps) {
  const periods = [
    { id: 'today', label: 'Today' },
    { id: 'yesterday', label: 'Yesterday' },
    { id: '7days', label: 'Last 7 Days' }
  ];

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
      <div className="flex items-center gap-3.5">
        <div className="w-11 h-11 rounded-xl bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-600 shadow-sm">
          <Users size={22} />
        </div>
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Agent Activity & Audit
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Live DB Telemetry
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
            Real-time execution log, autonomous workflow actions, and agent resolution metrics.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 self-end sm:self-center">
        {/* Time Period Filter Pills */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200/80">
          {periods.map((p) => (
            <button
              key={p.id}
              onClick={() => onPeriodChange(p.id)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                period === p.id
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh Data"
          className="p-2 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 rounded-xl border border-slate-200 shadow-sm transition-all disabled:opacity-50"
        >
          <RefreshCw size={16} className={isLoading ? 'animate-spin text-teal-600' : ''} />
        </button>
      </div>
    </div>
  );
}
