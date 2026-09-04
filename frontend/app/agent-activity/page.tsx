'use client';

import React from 'react';
import { Users, Activity, Sparkles, ArrowRight, ShieldCheck, Clock, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

export default function AgentActivityPage() {
  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center text-teal-600 shadow-sm">
            <Users size={22} />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Agent Activity</h1>
            <p className="text-sm text-slate-500 font-medium mt-0.5">
              Real-time monitoring and execution analytics across all AI agent workflows.
            </p>
          </div>
        </div>

        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Live Agent Monitoring
        </span>
      </div>

      {/* Metric Highlights */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Workers</span>
            <Activity size={16} className="text-teal-600" />
          </div>
          <p className="text-2xl font-extrabold text-slate-900 mt-2">4 Workflows</p>
          <p className="text-xs text-slate-500 mt-1">Maintenance, FAQ, Renewal & Rent Reminders</p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Orchestration Health</span>
            <ShieldCheck size={16} className="text-emerald-600" />
          </div>
          <p className="text-2xl font-extrabold text-emerald-600 mt-2">100% Operational</p>
          <p className="text-xs text-slate-500 mt-1">LangGraph Layer 2 & 3 state persistence</p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Average Turn Latency</span>
            <Clock size={16} className="text-blue-600" />
          </div>
          <p className="text-2xl font-extrabold text-slate-900 mt-2">&lt; 1.2s</p>
          <p className="text-xs text-slate-500 mt-1">FastAPI async worker response time</p>
        </div>
      </div>

      {/* Feature Roadmap Card */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-2xl p-8 shadow-xl">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/20 text-teal-300 text-xs font-semibold mb-4 border border-teal-500/30">
            <Sparkles size={13} />
            Telemetry & Deep Tracing
          </div>
          <h2 className="text-xl font-bold tracking-tight">Granular Execution Timeline & Token Usage</h2>
          <p className="text-sm text-slate-300 mt-2 leading-relaxed">
            Full LangSmith trace playback, human-in-the-loop audit logs, and per-property agent utilization breakdown will appear here in the upcoming release.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/overview"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-900 text-xs font-bold transition-all shadow-md"
            >
              <span>View Overview Summary</span>
              <ArrowRight size={14} />
            </Link>
            <Link
              href="/automations"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-all"
            >
              <span>Manage Automation Rules</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
