'use client';

import React, { useState, useEffect } from 'react';
import { Search, SlidersHorizontal, X } from 'lucide-react';
import { ConversationFilters } from '@/lib/hooks/use-conversations';

// ── Static filter option lists ─────────────────────────────────────────────────
// These mirror the DB enum values exactly so filters match the backend ILIKE queries.
const CHANNELS  = ['WhatsApp', 'Email', 'Voice', 'Web'];
const INTENTS   = ['Maintenance Request', 'Rent Follow-up', 'Lease Question', 'General Inquiry'];
const URGENCIES = ['Critical', 'High', 'Normal', 'Low'];
const STATUSES  = ['AI Resolved', 'Escalated', 'In Progress', 'Pending Review'];
const DATE_RANGES = [
  { label: 'Today',      value: 'today' },
  { label: 'Last 7 Days',  value: '7days' },
  { label: 'Last 30 Days', value: '30days' },
  { label: 'Last 90 Days', value: '90days' },
  { label: 'All Time',     value: 'all' },
];

interface FilterBarProps {
  filters: ConversationFilters;
  onApply: (partial: Partial<ConversationFilters>) => void;
  onReset: () => void;
}

export default function FilterBar({ filters, onApply, onReset }: FilterBarProps) {
  // Local draft state — only committed when user clicks "Apply Filters"
  const [draft, setDraft] = useState<ConversationFilters>(filters);

  // Sync search in real-time (debounced in hook), rest requires Apply click
  useEffect(() => {
    onApply({ search: draft.search });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.search]);

  const handleApply = () => onApply(draft);

  const handleReset = () => {
    setDraft({
      search: '', property_id: '', unit_id: '',
      channel: '', intent: '', urgency: '',
      status: '', date_range: '7days', page: 1,
    });
    onReset();
  };

  // Keep draft in sync when parent resets
  useEffect(() => { setDraft(filters); }, [filters]);

  const set = (key: keyof ConversationFilters, value: string | number) =>
    setDraft((prev) => ({ ...prev, [key]: value }));

  const hasActiveFilters =
    draft.channel || draft.intent || draft.urgency ||
    draft.status || draft.property_id || draft.unit_id;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
      {/* Row 1: Search + Property + Unit + Channel */}
      <div className="grid grid-cols-4 gap-3">
        {/* Search */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Search</label>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              id="conv-search"
              type="text"
              value={draft.search}
              onChange={(e) => set('search', e.target.value)}
              placeholder="Search conversations…"
              className="w-full pl-8 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all"
            />
          </div>
        </div>

        {/* Property — plain text for now; dynamic dropdown requires extra endpoint */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Property</label>
          <input
            id="conv-property"
            type="text"
            value={draft.property_id}
            onChange={(e) => set('property_id', e.target.value)}
            placeholder="Property name or ID…"
            className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all"
          />
        </div>

        {/* Unit */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Unit</label>
          <input
            id="conv-unit"
            type="text"
            value={draft.unit_id}
            onChange={(e) => set('unit_id', e.target.value)}
            placeholder="e.g. 204"
            className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all"
          />
        </div>

        {/* Channel */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Channel</label>
          <select
            id="conv-channel"
            value={draft.channel}
            onChange={(e) => set('channel', e.target.value)}
            className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all appearance-none cursor-pointer"
          >
            <option value="">All Channels</option>
            {CHANNELS.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      {/* Row 2: Intent + Urgency + Status + Date Range + Buttons */}
      <div className="grid grid-cols-4 gap-3 items-end">
        {/* Intent */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Intent</label>
          <select
            id="conv-intent"
            value={draft.intent}
            onChange={(e) => set('intent', e.target.value)}
            className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all appearance-none cursor-pointer"
          >
            <option value="">All Intents</option>
            {INTENTS.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        </div>

        {/* Urgency */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Urgency</label>
          <select
            id="conv-urgency"
            value={draft.urgency}
            onChange={(e) => set('urgency', e.target.value)}
            className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all appearance-none cursor-pointer"
          >
            <option value="">All Levels</option>
            {URGENCIES.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>

        {/* Status */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Status</label>
          <select
            id="conv-status"
            value={draft.status}
            onChange={(e) => set('status', e.target.value)}
            className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all appearance-none cursor-pointer"
          >
            <option value="">All Statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {/* Date Range + Action Buttons row */}
        <div className="flex items-end gap-2">
          <div className="flex-1 space-y-1">
            <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Date Range</label>
            <select
              id="conv-date-range"
              value={draft.date_range}
              onChange={(e) => set('date_range', e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all appearance-none cursor-pointer"
            >
              {DATE_RANGES.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Action buttons row */}
      <div className="flex items-center justify-between pt-1">
        {hasActiveFilters ? (
          <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
            <SlidersHorizontal size={12} />
            Filters active
          </span>
        ) : (
          <span />
        )}
        <div className="flex items-center gap-2">
          <button
            id="conv-clear-btn"
            onClick={handleReset}
            className="px-4 py-2 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-all flex items-center gap-1.5"
          >
            <X size={12} />
            Clear
          </button>
          <button
            id="conv-apply-btn"
            onClick={handleApply}
            className="px-5 py-2 text-xs font-semibold text-white bg-teal-600 hover:bg-teal-500 rounded-lg shadow-sm shadow-teal-900/10 transition-all active:scale-95"
          >
            Apply Filters
          </button>
        </div>
      </div>
    </div>
  );
}
