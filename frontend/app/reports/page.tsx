'use client';

import React from 'react';
import { BarChart3, TrendingUp, Download, Calendar, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export default function ReportsPage() {
  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center text-teal-600 shadow-sm">
            <BarChart3 size={22} />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Reports & Analytics</h1>
            <p className="text-sm text-slate-500 font-medium mt-0.5">
              Portfolio operational metrics, rent collection rates, and maintenance turnaround summaries.
            </p>
          </div>
        </div>

        <button
          disabled
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 text-slate-400 text-xs font-semibold cursor-not-allowed"
        >
          <Download size={14} />
          <span>Export Monthly PDF (Coming Soon)</span>
        </button>
      </div>

      {/* Report Types Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
            <TrendingUp size={20} />
          </div>
          <h3 className="font-bold text-slate-900 text-base">Rent Collection Rollup</h3>
          <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
            Monthly collected vs overdue rent amounts, automatic Day 30/35 reminder efficacy, and recovery rates.
          </p>
          <span className="inline-block mt-4 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-600">
            Automated Generation
          </span>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
            <Calendar size={20} />
          </div>
          <h3 className="font-bold text-slate-900 text-base">Lease Renewal Forecast</h3>
          <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
            Upcoming 90, 60, and 30-day lease expirations, tenant renewal intents, and vacancy risk projections.
          </p>
          <span className="inline-block mt-4 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-600">
            Proactive Pipeline
          </span>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-4">
            <BarChart3 size={20} />
          </div>
          <h3 className="font-bold text-slate-900 text-base">Maintenance SLA Performance</h3>
          <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
            Vendor dispatch response times, category breakdowns (HVAC, plumbing, electrical), and tenant satisfaction scores.
          </p>
          <span className="inline-block mt-4 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-600">
            Vendor Metrics
          </span>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 flex items-center justify-between shadow-sm">
        <div>
          <h4 className="font-bold text-slate-900 text-sm">Looking for immediate operational data?</h4>
          <p className="text-xs text-slate-500 mt-0.5">Explore active conversations and properties in the live operational dashboard.</p>
        </div>
        <Link
          href="/overview"
          className="flex items-center gap-1.5 text-xs font-bold text-teal-600 hover:text-teal-700 transition-colors"
        >
          <span>Back to Overview</span>
          <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
}
