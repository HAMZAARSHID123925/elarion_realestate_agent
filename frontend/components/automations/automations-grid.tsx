'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Plus } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { ALL_AUTOMATIONS, AutomationDefinition } from '@/lib/automation-definitions';
import { AutomationCard as DBAutomationCard } from '@/lib/types';
import AutomationCard from './automation-card';
import AddAutomationModal from './add-automation-modal';

// Skeleton card shown during API fetch
function AutomationCardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 border-t-4 border-t-slate-200 shadow-sm animate-pulse flex flex-col">
      <div className="px-5 pt-5 pb-4 space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-slate-200" />
          <div className="h-4 bg-slate-200 rounded w-36" />
        </div>
        <div className="h-3 bg-slate-100 rounded w-full" />
        <div className="h-3 bg-slate-100 rounded w-3/4" />
      </div>
      <div className="mx-5 mb-4 h-20 bg-amber-50 rounded-lg border border-amber-100" />
      <div className="px-5 pb-4">
        <div className="h-3 bg-slate-100 rounded w-32" />
      </div>
      <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/60 flex gap-3">
        <div className="h-4 bg-slate-200 rounded w-20" />
        <div className="h-7 bg-slate-100 rounded w-24 ml-auto" />
      </div>
    </div>
  );
}

interface AutomationsGridProps {
  onSelectAutomation: (def: AutomationDefinition) => void;
}

export default function AutomationsGrid({ onSelectAutomation }: AutomationsGridProps) {
  const [automations, setAutomations] = useState<AutomationDefinition[]>(ALL_AUTOMATIONS);
  const [activeStatuses, setActiveStatuses] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  const fetchAutomations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const dbCards = await apiClient.getAutomations();
      
      const statusMap: Record<string, boolean> = {};
      const mergedList: AutomationDefinition[] = [];

      // 1. Process DB cards that match our known workflow definitions
      const knownIds = new Set(ALL_AUTOMATIONS.map((a) => a.id));

      ALL_AUTOMATIONS.forEach((staticDef) => {
        const dbCard = dbCards.find((c) => c.id === staticDef.id);
        if (dbCard) {
          const isActive = dbCard.status?.toLowerCase() === 'active';
          statusMap[dbCard.id] = isActive;

          mergedList.push({
            ...staticDef,
            name: dbCard.name || staticDef.name,
            status: dbCard.status || (isActive ? 'Active' : 'Inactive'),
            channels: dbCard.channels?.length ? dbCard.channels : staticDef.channels,
            escalation_conditions: dbCard.escalation_conditions?.length ? dbCard.escalation_conditions : staticDef.escalation_conditions,
            scope: dbCard.scope || staticDef.scope,
            properties_count: dbCard.properties_count || staticDef.properties_count,
            handles: dbCard.handles?.length ? dbCard.handles : staticDef.handles,
            icon_type: dbCard.icon_type || staticDef.icon_type,
            steps: dbCard.steps?.length ? dbCard.steps : staticDef.steps,
          });
        } else {
          statusMap[staticDef.id] = true;
          mergedList.push(staticDef);
        }
      });

      // 2. Handle any extra custom automations created in PostgreSQL DB
      dbCards.forEach((dbCard) => {
        if (!knownIds.has(dbCard.id)) {
          const isActive = dbCard.status?.toLowerCase() === 'active';
          statusMap[dbCard.id] = isActive;

          mergedList.push({
            id: dbCard.id,
            name: dbCard.name,
            icon_type: dbCard.icon_type || 'maintenance',
            tagline: dbCard.description || `Custom operational workflow for ${dbCard.name}.`,
            handles: dbCard.handles || [dbCard.name],
            channels: dbCard.channels || ['WhatsApp', 'Email'],
            escalation_conditions: dbCard.escalation_conditions || ['Manual review requested'],
            scope: dbCard.scope || 'All Properties (42)',
            properties_count: dbCard.properties_count || 42,
            steps: [
              { id: 'step_1', title: 'Trigger Event', description: `Fires on incoming ${dbCard.name} request.` },
              { id: 'step_2', title: 'Process Workflow', description: 'AI evaluates request and executes operational steps.', isAiTask: true, isCurrent: true },
              { id: 'step_3', title: 'Escalation Check', description: 'Evaluates escalation conditions and human sign-off.', isConditional: true },
              { id: 'step_4', title: 'Finalize & Confirm', description: 'Logs outcome in database and notifies stakeholders.' },
            ],
            escalation_rules: (dbCard.escalation_conditions || ['Manual review']).map((cond, idx) => ({
              id: `rule_${idx}`,
              icon: 'uncertainty',
              label: cond,
              description: 'Configured escalation rule persisted in database.'
            })),
            integrations: [
              { id: 'appfolio', name: 'AppFolio', initials: 'AF', color: 'bg-blue-600', textColor: 'text-white', connected: true },
              { id: 'whatsapp', name: 'WhatsApp', initials: 'WA', color: 'bg-green-500', textColor: 'text-white', connected: true },
            ],
            editable_fields: ['active', 'escalation_conditions', 'channels'],
          });
        }
      });

      setAutomations(mergedList);
      setActiveStatuses(statusMap);
    } catch (err) {
      console.warn('[AutomationsGrid] API fetch failed, using fallback:', err);
      setError('Could not connect to database — showing default workflow templates.');
      const defaults: Record<string, boolean> = {};
      ALL_AUTOMATIONS.forEach((a) => { defaults[a.id] = true; });
      setActiveStatuses(defaults);
      setAutomations(ALL_AUTOMATIONS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAutomations();
  }, [fetchAutomations]);

  const handleToggle = async (id: string, active: boolean) => {
    // Optimistic update
    setActiveStatuses((prev) => ({ ...prev, [id]: active }));
    try {
      await apiClient.updateAutomation(id, { active });
    } catch {
      // Revert on failure
      setActiveStatuses((prev) => ({ ...prev, [id]: !active }));
    }
  };

  const handleDelete = async (id: string) => {
    // Optimistic remove
    setAutomations((prev) => prev.filter((a) => a.id !== id));
    try {
      await apiClient.deleteAutomation(id);
    } catch (err) {
      console.error('Delete failed:', err);
      // Re-fetch on error
      fetchAutomations();
    }
  };

  const handleCreated = (newCard: DBAutomationCard) => {
    // Refresh automations list directly from database
    fetchAutomations();
  };

  return (
    <div>
      {/* Error notice (non-blocking) */}
      {error && !loading && (
        <div className="mb-4 px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700 font-medium">
          ⚠ {error}
        </div>
      )}

      {/* Cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {loading
          ? Array.from({ length: 6 }).map((_, i) => <AutomationCardSkeleton key={i} />)
          : automations.map((def) => (
            <AutomationCard
              key={def.id}
              def={def}
              isActive={activeStatuses[def.id] ?? true}
              onViewDetails={() => onSelectAutomation(def)}
              onToggle={(active) => handleToggle(def.id, active)}
              onDelete={(id) => handleDelete(id)}
            />
          ))
        }

        {/* "Add New" placeholder card */}
        {!loading && (
          <button
            id="add-new-automation"
            aria-label="Add new automation"
            onClick={() => setIsAddModalOpen(true)}
            className="bg-white rounded-xl border-2 border-dashed border-slate-200 hover:border-teal-400 hover:bg-teal-50/30
              transition-all duration-200 min-h-[240px] flex flex-col items-center justify-center gap-3
              text-slate-400 hover:text-teal-600 group cursor-pointer"
          >
            <div className="w-12 h-12 rounded-full border-2 border-dashed border-slate-300 group-hover:border-teal-400 flex items-center justify-center transition-colors">
              <Plus size={22} className="group-hover:scale-110 transition-transform" />
            </div>
            <div className="text-center">
              <p className="font-semibold text-sm">Add Automation</p>
              <p className="text-xs mt-0.5 text-slate-400">Configure a new AI workflow</p>
            </div>
          </button>
        )}
      </div>

      {/* Add New Automation Modal */}
      <AddAutomationModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onCreated={handleCreated}
      />
    </div>
  );
}

