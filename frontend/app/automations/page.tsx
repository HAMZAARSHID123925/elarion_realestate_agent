'use client';

import React, { useState } from 'react';
import { Sparkles, Search } from 'lucide-react';
import AutomationsGrid from '@/components/automations/automations-grid';
import AutomationDetailModal from '@/components/automations/automation-detail-modal';
import { AutomationDefinition } from '@/lib/automation-definitions';

export default function AutomationsPage() {
  const [selectedDef, setSelectedDef] = useState<AutomationDefinition | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-12">

      {/* ── Page Header ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-xl bg-teal-50 flex items-center justify-center">
              <Sparkles size={20} className="text-teal-600" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Automations
            </h1>
          </div>
          <p className="text-sm text-slate-500 font-medium ml-12">
            Workflows TenantFlow.ai is currently configured to handle.
          </p>
        </div>

        {/* Search bar */}
        <div className="relative w-72">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            id="automations-search"
            type="text"
            placeholder="Search automations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 text-sm bg-white border border-slate-200 rounded-xl
              focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent
              placeholder:text-slate-400 shadow-sm transition-all"
          />
        </div>
      </div>

      {/* ── Automations Grid ─────────────────────────────────────────── */}
      <AutomationsGrid onSelectAutomation={setSelectedDef} />

      {/* ── Detail Modal ─────────────────────────────────────────────── */}
      <AutomationDetailModal
        def={selectedDef}
        isOpen={selectedDef !== null}
        onClose={() => setSelectedDef(null)}
        onSaved={() => setSelectedDef(null)}
      />
    </div>
  );
}
