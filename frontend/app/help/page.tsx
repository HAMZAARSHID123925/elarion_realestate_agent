'use client';

import React from 'react';
import { HelpCircle, BookOpen, MessageSquare, Terminal, FileText, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

export default function HelpPage() {
  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center text-teal-600 shadow-sm">
          <HelpCircle size={22} />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Help & Documentation</h1>
          <p className="text-sm text-slate-500 font-medium mt-0.5">
            Operational guides, API endpoints reference, and architectural documentation.
          </p>
        </div>
      </div>

      {/* Guide Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center mb-4">
            <BookOpen size={20} />
          </div>
          <h3 className="font-bold text-slate-900 text-base">Channel Operations Guide</h3>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Learn how WhatsApp webhooks, Gmail OAuth 2.0 polling, and Vapi voice assistant interact with the master graph.
          </p>
          <div className="mt-4 text-xs font-mono text-slate-400">
            docs/GMAIL_CHANNEL_OPERATIONS_GUIDE.md
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
            <Terminal size={20} />
          </div>
          <h3 className="font-bold text-slate-900 text-base">FastAPI REST Endpoints</h3>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Explore Swagger API documentation for conversation triage, properties CRUD, and automations at <code>/docs</code>.
          </p>
          <div className="mt-4 text-xs font-mono text-slate-400">
            http://localhost:8080/docs
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-4">
            <FileText size={20} />
          </div>
          <h3 className="font-bold text-slate-900 text-base">LangGraph Subgraphs</h3>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Review state transitions, slot collection patterns, and human-in-the-loop escalation rules.
          </p>
          <div className="mt-4 text-xs font-mono text-slate-400">
            langgraph_agent/ARCHITECTURE_REPORT.md
          </div>
        </div>
      </div>
    </div>
  );
}
