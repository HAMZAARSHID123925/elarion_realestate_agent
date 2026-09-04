'use client';

import React from 'react';
import { Plug, MessageSquare, Mic, Mail, CheckCircle2, AlertCircle } from 'lucide-react';

const INTEGRATIONS = [
  {
    name: 'WhatsApp Cloud API / Meta Webhooks',
    channel: 'Messaging',
    status: 'Connected',
    port: 'Port 8003',
    description: 'Bi-directional WhatsApp text messaging gateway for maintenance intake, lease inquiries, and rent reminders.'
  },
  {
    name: 'Vapi Voice Assistant',
    channel: 'Voice & Telephony',
    status: 'Connected',
    port: 'Port 8002',
    description: 'Inbound phone calls transcription, tool calling, and live voice interactions powered by LangGraph.'
  },
  {
    name: 'Gmail API / OAuth 2.0',
    channel: 'Email Channel',
    status: 'Configured',
    port: 'Background Task',
    description: 'Automated email triage, thread parsing, attachments extraction, and resident notifications.'
  }
];

export default function IntegrationsPage() {
  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center text-teal-600 shadow-sm">
          <Plug size={22} />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Channels & Integrations</h1>
          <p className="text-sm text-slate-500 font-medium mt-0.5">
            Active multi-channel connectors communicating with the Elarion AI Orchestrator.
          </p>
        </div>
      </div>

      {/* Integrations Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {INTEGRATIONS.map((item) => (
          <div key={item.name} className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-bold px-2.5 py-0.5 rounded bg-slate-100 text-slate-600 uppercase tracking-wider">
                  {item.channel}
                </span>
                <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600">
                  <CheckCircle2 size={13} />
                  {item.status}
                </span>
              </div>
              <h3 className="font-bold text-slate-900 text-base">{item.name}</h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">{item.description}</p>
            </div>
            <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400 font-mono">
              <span>{item.port}</span>
              <span className="text-teal-600 font-sans font-semibold">Active</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
