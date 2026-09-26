'use client';

import React, { useState, useMemo } from 'react';
import { Search, CheckCircle2, AlertCircle, XCircle, ChevronRight, Filter, MessageSquare, Mail, Phone, Bot } from 'lucide-react';

interface ExecutionItem {
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

interface ActivityFeedProps {
  executions: ExecutionItem[];
  selectedAgent: string;
  onSelectExecution: (item: ExecutionItem) => void;
}

export default function ActivityFeed({
  executions,
  selectedAgent,
  onSelectExecution
}: ActivityFeedProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [channelFilter, setChannelFilter] = useState('all');

  // Filtered executions
  const filteredExecutions = useMemo(() => {
    return executions.filter((item) => {
      // 1. Agent filter
      if (selectedAgent !== 'all') {
        if (!item.badge.toLowerCase().includes(selectedAgent.toLowerCase()) &&
            !item.title.toLowerCase().includes(selectedAgent.toLowerCase())) {
          return false;
        }
      }

      // 2. Status filter
      if (statusFilter !== 'all') {
        const s = item.status.toLowerCase();
        if (statusFilter === 'resolved' && !s.includes('resolved') && !s.includes('completed')) return false;
        if (statusFilter === 'escalated' && !s.includes('escalat')) return false;
        if (statusFilter === 'failed' && !s.includes('failed')) return false;
      }

      // 3. Channel filter
      if (channelFilter !== 'all') {
        const c = (item.channel || '').toLowerCase();
        if (!c.includes(channelFilter.toLowerCase())) return false;
      }

      // 4. Search query
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matchesTitle = item.title.toLowerCase().includes(q);
        const matchesSummary = item.summary.toLowerCase().includes(q);
        const matchesTenant = (item.tenant_name || '').toLowerCase().includes(q);
        const matchesId = item.id.toLowerCase().includes(q);
        if (!matchesTitle && !matchesSummary && !matchesTenant && !matchesId) {
          return false;
        }
      }

      return true;
    });
  }, [executions, selectedAgent, statusFilter, channelFilter, searchTerm]);

  const getChannelBadge = (channel?: string) => {
    const c = (channel || 'whatsapp').toLowerCase();
    if (c.includes('email')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-sky-50 text-sky-700 border border-sky-200">
          <Mail size={11} />
          Email
        </span>
      );
    }
    if (c.includes('voice')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
          <Phone size={11} />
          Voice
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
        <MessageSquare size={11} />
        WhatsApp
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes('resolved') || s.includes('complete')) {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-600">
          <CheckCircle2 size={15} className="text-emerald-500" />
          AI Resolved
        </span>
      );
    }
    if (s.includes('escalat')) {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-600">
          <AlertCircle size={15} className="text-amber-500" />
          Escalated
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-600">
        <XCircle size={15} className="text-rose-500" />
        {status}
      </span>
    );
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 space-y-5">
      {/* Header and Filter Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Bot size={18} className="text-teal-600" />
            Autonomous Action Feed & Audit Trail
          </h2>
          <p className="text-xs text-slate-500 font-medium">
            Chronological log of every automated decision and turn committed to PostgreSQL
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Box */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search actions or tenants..."
              className="pl-8 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all w-48 sm:w-56"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs py-1.5 px-2.5 rounded-xl border border-slate-200 bg-white font-medium text-slate-700 hover:border-slate-300 focus:outline-none cursor-pointer"
          >
            <option value="all">All Statuses</option>
            <option value="resolved">AI Resolved</option>
            <option value="escalated">Escalated</option>
            <option value="failed">Failed</option>
          </select>

          {/* Channel Filter */}
          <select
            value={channelFilter}
            onChange={(e) => setChannelFilter(e.target.value)}
            className="text-xs py-1.5 px-2.5 rounded-xl border border-slate-200 bg-white font-medium text-slate-700 hover:border-slate-300 focus:outline-none cursor-pointer"
          >
            <option value="all">All Channels</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="email">Email</option>
            <option value="voice">Voice</option>
          </select>
        </div>
      </div>

      {/* Feed List */}
      <div className="divide-y divide-slate-100 border border-slate-100 rounded-xl overflow-hidden">
        {filteredExecutions.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Bot size={36} className="mx-auto text-slate-300 mb-2" />
            <p className="text-sm font-semibold text-slate-600">No agent actions found</p>
            <p className="text-xs text-slate-400 mt-0.5">
              Try adjusting your search query or period filter above.
            </p>
          </div>
        ) : (
          filteredExecutions.map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectExecution(item)}
              className="p-4 hover:bg-slate-50/80 transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
            >
              {/* Left Info */}
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  {getChannelBadge(item.channel)}
                  <span className="text-xs font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md">
                    {item.badge}
                  </span>
                  <span className="text-xs font-extrabold text-slate-900">
                    {item.title}
                  </span>
                  {item.unit_number && (
                    <span className="text-[11px] text-slate-400 font-medium">
                      ({item.unit_number})
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-600 line-clamp-1 font-medium pl-0.5">
                  {item.summary}
                </p>
              </div>

              {/* Right Status & Action */}
              <div className="flex items-center gap-4 sm:self-center shrink-0">
                <div className="text-right">
                  <div>{getStatusBadge(item.status)}</div>
                  <span className="text-[10px] text-slate-400 font-medium block mt-0.5">
                    {item.timestamp}
                  </span>
                </div>

                <div className="w-7 h-7 rounded-lg bg-slate-100 group-hover:bg-teal-50 group-hover:text-teal-600 flex items-center justify-center text-slate-400 transition-colors">
                  <ChevronRight size={15} />
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Feed Summary Footer */}
      <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
        <span>
          Showing <strong className="text-slate-700">{filteredExecutions.length}</strong> of{' '}
          <strong className="text-slate-700">{executions.length}</strong> real database records
        </span>
        <span className="text-[11px] font-mono text-slate-400">
          Source: PostgreSQL (conversations + audit_logs)
        </span>
      </div>
    </div>
  );
}
