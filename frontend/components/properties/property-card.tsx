'use client';

import React, { useState } from 'react';
import {
  Building2,
  Home,
  Building,
  LandPlot,
  Store,
  MessageSquare,
  Wrench,
  AlertTriangle,
  ArrowRight,
  Trash2,
  ToggleLeft,
  ToggleRight,
  Bot,
} from 'lucide-react';
import { PropertyDashboardCard } from '@/lib/types';
import { getPropertyStatusToken, getPropertyTypeToken } from '@/lib/design-tokens';
import { apiClient } from '@/lib/api-client';

interface PropertyCardProps {
  property: PropertyDashboardCard;
  onDelete: (propertyId: string) => void;
  onRefresh: () => void;
  onViewDetail?: (property: PropertyDashboardCard) => void;
}

const TYPE_ICONS: Record<string, React.ElementType> = {
  house: Home,
  apartment: Building,
  plot: LandPlot,
  commercial: Store,
};

/** Compact automation tag names for card display */
function shortenAutomationName(name: string): string {
  const map: Record<string, string> = {
    'Maintenance Request Handler': 'Maintenance',
    'Resident Support Agent': 'Resident Support',
    'Rent Collection Automation': 'Rent',
    'Lease Renewal Automation': 'Lease',
    'Lease Renewal Manager': 'Lease',
  };
  return map[name] || name.split(' ').slice(0, 2).join(' ');
}

/** Returns a deterministic icon for the automation tag */
function automationTagIcon(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes('maintenance') || lower.includes('wrench')) return '🔧';
  if (lower.includes('support') || lower.includes('resident')) return '👥';
  if (lower.includes('rent') || lower.includes('collect')) return '💰';
  if (lower.includes('lease') || lower.includes('renewal')) return '📄';
  if (lower.includes('report') || lower.includes('owner')) return '📊';
  if (lower.includes('security')) return '🔒';
  return '⚡';
}

export default function PropertyCard({ property, onDelete, onRefresh, onViewDetail }: PropertyCardProps) {
  const [toggling, setToggling] = useState(false);
  const statusToken = getPropertyStatusToken(property.status);
  const typeToken = getPropertyTypeToken(property.property_type || '');
  const TypeIcon = TYPE_ICONS[property.property_type || ''] || Building2;

  const handleToggleStatus = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (toggling) return;
    setToggling(true);
    try {
      const newStatus = property.status === 'Active' ? 'Inactive' : 'Active';
      await apiClient.togglePropertyStatus(property.property_id, newStatus);
      onRefresh();
    } catch (err) {
      console.error('Failed to toggle status:', err);
    } finally {
      setToggling(false);
    }
  };

  const handleCardClick = () => {
    if (onViewDetail) {
      onViewDetail(property);
    }
  };

  return (
    <div
      onClick={handleCardClick}
      className={`
        group relative bg-white rounded-2xl border border-slate-200
        shadow-sm hover:shadow-lg hover:border-teal-200/60 hover:-translate-y-0.5
        transition-all duration-300 ease-out flex flex-col overflow-hidden cursor-pointer
      `}
    >
      {/* ── Card Header ──────────────────────────────────────────── */}
      <div className="p-5 pb-0">
        <div className="flex items-start justify-between gap-3">
          {/* Property Icon + Name */}
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <div className={`w-10 h-10 rounded-xl ${typeToken.iconBg} flex items-center justify-center flex-shrink-0 shadow-sm`}>
              <TypeIcon size={20} className={typeToken.iconColor} />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="font-bold text-slate-900 text-base leading-tight truncate group-hover:text-teal-600 transition-colors">
                {property.title || 'Untitled Property'}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5 truncate">
                {property.units_count > 0 && (
                  <span className="font-semibold text-slate-600">{property.units_count} {property.units_count === 1 ? 'Unit' : 'Units'}</span>
                )}
                {property.units_count > 0 && (property.city || property.address) && ' • '}
                {property.city && <span>{property.city}</span>}
                {!property.city && property.address && <span>{property.address}</span>}
                {property.city && property.address && <span>, {property.address}</span>}
              </p>
            </div>
          </div>

          {/* Status Badge */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${statusToken.bg} ${statusToken.text} flex-shrink-0`}>
            <span className={`w-2 h-2 rounded-full ${statusToken.dot}`} />
            {property.status}
          </div>
        </div>
      </div>

      {/* ── Stats Row ────────────────────────────────────────────── */}
      <div className="px-5 pt-4 pb-3">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Conversations</p>
            <p className="text-2xl font-extrabold text-slate-900 mt-0.5 leading-none">
              {property.conversations_count.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Maintenance</p>
            <p className="text-2xl font-extrabold text-slate-900 mt-0.5 leading-none">
              {property.maintenance_count.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-[11px] font-medium text-red-400 uppercase tracking-wider">Escalations</p>
            <p className={`text-2xl font-extrabold mt-0.5 leading-none ${property.escalations_count > 0 ? 'text-red-600' : 'text-slate-900'}`}>
              {property.escalations_count.toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* ── Active Automations ────────────────────────────────────── */}
      {property.active_automations.length > 0 && (
        <div className="px-5 pb-3">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Active Automations</p>
          <div className="flex flex-wrap gap-1.5">
            {property.active_automations.map((auto, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-slate-100 text-slate-600 text-[11px] font-medium border border-slate-200/60"
              >
                <span className="text-[10px]">{automationTagIcon(auto)}</span>
                {shortenAutomationName(auto)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Card Footer ──────────────────────────────────────────── */}
      <div className="mt-auto border-t border-slate-100 px-5 py-3 flex items-center justify-between">
        {/* View Activity Button */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            if (onViewDetail) onViewDetail(property);
          }}
          className="flex items-center gap-1.5 text-sm font-semibold text-teal-600 hover:text-teal-700 transition-colors group/btn"
        >
          <span>View Property Activity</span>
          <ArrowRight size={14} className="transition-transform group-hover/btn:translate-x-1" />
        </button>

        {/* Action Buttons */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          {/* Toggle Status */}
          <button
            onClick={handleToggleStatus}
            disabled={toggling}
            className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 hover:bg-teal-50 transition-all disabled:opacity-50"
            title={`Toggle to ${property.status === 'Active' ? 'Inactive' : 'Active'}`}
          >
            {property.status === 'Active' ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
          </button>

          {/* Delete */}
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(property.property_id); }}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all"
            title="Delete property"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
