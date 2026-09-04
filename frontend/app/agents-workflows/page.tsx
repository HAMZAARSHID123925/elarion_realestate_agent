'use client';

import React from 'react';
import { Workflow, Layers, ArrowRight, ShieldCheck, Sparkles, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

const WORKFLOW_DEPARTMENTS = [
  {
    name: 'Maintenance Triage & Vendor Dispatch',
    domain: 'Maintenance',
    status: 'Active',
    description: 'Multi-turn slot collection, emergency classification, priority vendor matching, and auto-dispatch.',
    graph: 'Layer 3 Subgraph (maintenance/graph.py)'
  },
  {
    name: 'Resident FAQ & Policy RAG',
    domain: 'FAQ & Support',
    status: 'Active',
    description: 'Vector-backed semantic search over lease terms, building policies, parking rules, and property amenities.',
    graph: 'Layer 3 Subgraph (faq/graph.py)'
  },
  {
    name: 'Lease Renewal & Negotiation Pipeline',
    domain: 'Rent Renewal',
    status: 'Active',
    description: 'Automatic 90/60/30-day expiry scan, tenant intent classification, dynamic rent proposal generation.',
    graph: 'Layer 3 Subgraph (rent_renewal/graph.py)'
  },
  {
    name: 'Automated Rent Reminders & Overdue Tracking',
    domain: 'Rent Reminder',
    status: 'Active',
    description: 'Day 30/35 payment notification dispatch, dispute handling, and direct human escalation triggers.',
    graph: 'Layer 3 Subgraph (rent_reminder/graph.py)'
  }
];

export default function AgentsWorkflowsPage() {
  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center text-teal-600 shadow-sm">
            <Workflow size={22} />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Agents & Workflows</h1>
            <p className="text-sm text-slate-500 font-medium mt-0.5">
              LangGraph-powered stateful agents and department subgraph orchestrators.
            </p>
          </div>
        </div>

        <Link
          href="/automations"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold shadow-md shadow-teal-900/10 transition-all active:scale-[0.98]"
        >
          <Sparkles size={14} />
          <span>Edit Automation Rules</span>
        </Link>
      </div>

      {/* Architecture Highlights */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
          <Layers size={15} className="text-teal-600" />
          <span>Multi-Layer Orchestration Topology</span>
        </div>
        <p className="text-sm text-slate-600 leading-relaxed max-w-3xl">
          Elarion uses an isolated 3-layer architecture: <strong>Layer 1 (Ingestion & Normalization)</strong> bridges WhatsApp, Voice (Vapi), and Email channels; <strong>Layer 2 (Supervisor Router)</strong> classifies intent and handles state transitions; <strong>Layer 3 (Department Graphs)</strong> executes isolated stateful workflows with checkpointer persistence.
        </p>
      </div>

      {/* Department Graphs List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {WORKFLOW_DEPARTMENTS.map((dept) => (
          <div key={dept.name} className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-md bg-teal-50 text-teal-700 border border-teal-200">
                  {dept.domain}
                </span>
                <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600">
                  <CheckCircle2 size={13} />
                  {dept.status}
                </span>
              </div>
              <h3 className="font-bold text-slate-900 text-base mt-2">{dept.name}</h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">{dept.description}</p>
            </div>
            <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400 font-mono">
              <span>{dept.graph}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
