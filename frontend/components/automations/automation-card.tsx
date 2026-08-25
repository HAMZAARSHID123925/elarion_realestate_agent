'use client';

import React from 'react';
import {
  Wrench, BellRing, HeadphonesIcon, FileText, BarChart3,
  Building2, Settings2, ChevronRight, AlertTriangle, Trash2
} from 'lucide-react';
import { AutomationDefinition } from '@/lib/automation-definitions';
import { getAutomationToken } from '@/lib/design-tokens';

// ── Icon resolver ─────────────────────────────────────────────────────────────
function AutomationIcon({ type, className }: { type: string; className?: string }) {
  const cls = className ?? 'w-5 h-5';
  switch (type) {
    case 'maintenance': return <Wrench className={cls} />;
    case 'rent':        return <BellRing className={cls} />;
    case 'support':     return <HeadphonesIcon className={cls} />;
    case 'lease':       return <FileText className={cls} />;
    case 'reporting':   return <BarChart3 className={cls} />;
    default:            return <Settings2 className={cls} />;
  }
}

interface AutomationCardProps {
  def: AutomationDefinition;
  isActive: boolean;
  onViewDetails: () => void;
  onToggle?: (active: boolean) => void;
  onDelete?: (id: string) => void;
}

export default function AutomationCard({
  def,
  isActive,
  onViewDetails,
  onToggle,
  onDelete,
}: AutomationCardProps) {
  const tokens = getAutomationToken(def.icon_type);

  return (
    <article
      role="button"
      tabIndex={0}
      aria-label={`${def.name} automation — click to view details`}
      onClick={onViewDetails}
      onKeyDown={(e) => e.key === 'Enter' && onViewDetails()}
      className={`
        relative bg-white rounded-xl border border-slate-200 border-t-4 ${tokens.cardAccent}
        shadow-sm hover:shadow-lg hover:-translate-y-0.5
        transition-all duration-200 cursor-pointer
        flex flex-col overflow-hidden group
        focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 focus-visible:ring-offset-2
      `}
    >
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="px-5 pt-5 pb-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl ${tokens.iconBg} flex items-center justify-center flex-shrink-0 shadow-sm`}>
              <AutomationIcon type={def.icon_type} className={`w-5 h-5 ${tokens.iconColor}`} />
            </div>
            <h3 className="font-bold text-slate-900 text-base leading-tight">{def.name}</h3>
          </div>

          {/* Active badge */}
          <span
            className={`
              inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold flex-shrink-0
              ${isActive
                ? `${tokens.badgeBg} ${tokens.badgeText}`
                : 'bg-slate-100 text-slate-500'
              }
            `}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
            {isActive ? 'Active' : 'Inactive'}
          </span>
        </div>

        {/* Handles — hyperlink-style blue labels */}
        <div className="mt-3 text-sm text-slate-600 leading-relaxed">
          <span className="font-semibold text-slate-700">Handles: </span>
          {def.handles.map((h, i) => (
            <React.Fragment key={h}>
              <span className="text-teal-600 font-medium hover:underline cursor-pointer">
                {h}
              </span>
              {i < def.handles.length - 1 && <span className="text-slate-400">, </span>}
            </React.Fragment>
          ))}
        </div>

        {/* Channels */}
        <div className="mt-1.5 text-sm text-slate-500">
          <span className="font-semibold text-slate-700">Channels: </span>
          {def.channels.join(', ')}
        </div>
      </div>

      {/* ── Escalation Conditions box ──────────────────────────────── */}
      {def.escalation_conditions.length > 0 && (
        <div className="mx-5 mb-4 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 mb-1.5">
            <AlertTriangle size={12} />
            Escalation Conditions
          </div>
          <ul className="space-y-0.5">
            {def.escalation_conditions.slice(0, 3).map((cond) => (
              <li key={cond} className="flex items-start gap-1.5 text-xs text-amber-800">
                <span className="text-amber-400 mt-0.5 flex-shrink-0">•</span>
                {cond}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Properties scope ────────────────────────────────────────── */}
      <div className="px-5 pb-4">
        <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
          <Building2 size={13} className="text-slate-400" />
          {def.scope}
        </div>
      </div>

      {/* ── Action buttons ──────────────────────────────────────────── */}
      <div
        className="px-5 py-3 border-t border-slate-100 bg-slate-50/60 flex items-center gap-2 mt-auto"
        onClick={(e) => e.stopPropagation()} // prevent card click when clicking buttons
        role="presentation"
      >
        <button
          id={`view-details-${def.id}`}
          onClick={(e) => { e.stopPropagation(); onViewDetails(); }}
          className="flex items-center gap-1 text-sm font-semibold text-teal-600 hover:text-teal-700 transition-colors group/btn"
        >
          View Details
          <ChevronRight size={14} className="group-hover/btn:translate-x-0.5 transition-transform" />
        </button>

        <div className="ml-auto flex items-center gap-2">
          <button
            id={`configure-${def.id}`}
            onClick={(e) => { e.stopPropagation(); onViewDetails(); }}
            className="flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-700 border border-slate-200 hover:border-slate-300 rounded-lg px-3 py-1.5 bg-white hover:bg-slate-50 transition-all"
          >
            <Settings2 size={13} />
            Configure
          </button>

          {onDelete && (
            <button
              id={`delete-card-${def.id}`}
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm(`Are you sure you want to delete "${def.name}" automation? This will remove it from PostgreSQL database.`)) {
                  onDelete(def.id);
                }
              }}
              title="Delete Automation"
              className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 border border-slate-200 hover:border-red-200 rounded-lg transition-colors"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Hover overlay glow effect */}
      <div className={`absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none ${tokens.iconBg} mix-blend-multiply`} style={{ opacity: 0 }} />
    </article>
  );
}
