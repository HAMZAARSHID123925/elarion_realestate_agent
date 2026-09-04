'use client';

import React from 'react';
import {
  X,
  Building2,
  Home,
  Building,
  LandPlot,
  Store,
  MapPin,
  DollarSign,
  Layers,
  MessageSquare,
  Wrench,
  AlertTriangle,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Calendar,
  Activity,
  Bot
} from 'lucide-react';
import Link from 'next/link';
import { PropertyDashboardCard } from '@/lib/types';
import { getPropertyStatusToken, getPropertyTypeToken } from '@/lib/design-tokens';

interface PropertyDetailModalProps {
  property: PropertyDashboardCard | null;
  isOpen: boolean;
  onClose: () => void;
  onToggleStatus?: (propertyId: string, currentStatus: string) => void;
}

const TYPE_ICONS: Record<string, React.ElementType> = {
  house: Home,
  apartment: Building,
  plot: LandPlot,
  commercial: Store,
};

export default function PropertyDetailModal({
  property,
  isOpen,
  onClose,
  onToggleStatus
}: PropertyDetailModalProps) {
  if (!isOpen || !property) return null;

  const statusToken = getPropertyStatusToken(property.status);
  const typeToken = getPropertyTypeToken(property.property_type || '');
  const TypeIcon = TYPE_ICONS[property.property_type || ''] || Building2;

  const createdDate = property.created_at
    ? new Date(property.created_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : 'Recently Added';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Card */}
      <div className="relative w-full max-w-2xl bg-white rounded-3xl shadow-2xl border border-slate-200/80 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-6 bg-gradient-to-r from-slate-900 to-slate-800 text-white flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-white/10 backdrop-blur-md flex items-center justify-center text-teal-400 border border-white/10 shadow-inner">
              <TypeIcon size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h2 className="text-xl font-bold tracking-tight text-white">
                  {property.title || 'Untitled Property'}
                </h2>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusToken.bg} ${statusToken.text}`}>
                  {property.status}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/10 text-slate-300 capitalize">
                  {property.property_type || 'Property'}
                </span>
              </div>

              <p className="flex items-center gap-1.5 text-xs text-slate-300 font-medium mt-1.5">
                <MapPin size={13} className="text-teal-400 flex-shrink-0" />
                <span>{property.address ? `${property.address}, ` : ''}{property.city || 'Location unassigned'}</span>
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          
          {/* Key Metric Highlights */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-50 border border-slate-200/70 rounded-2xl p-3.5 text-center">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Valuation / Rent</span>
              <span className="text-lg font-extrabold text-slate-900 mt-0.5 block">
                {property.price_lakhs > 0 ? `${property.price_lakhs} Lakhs` : 'N/A'}
              </span>
            </div>

            <div className="bg-slate-50 border border-slate-200/70 rounded-2xl p-3.5 text-center">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Total Units</span>
              <span className="text-lg font-extrabold text-slate-900 mt-0.5 block">
                {property.units_count} {property.units_count === 1 ? 'Unit' : 'Units'}
              </span>
            </div>

            <div className="bg-slate-50 border border-slate-200/70 rounded-2xl p-3.5 text-center">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Conversations</span>
              <span className="text-lg font-extrabold text-teal-600 mt-0.5 block">
                {property.conversations_count}
              </span>
            </div>

            <div className="bg-slate-50 border border-slate-200/70 rounded-2xl p-3.5 text-center">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Maintenance</span>
              <span className="text-lg font-extrabold text-slate-900 mt-0.5 block">
                {property.maintenance_count}
              </span>
            </div>
          </div>

          {/* AI Operations Status */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-700 uppercase tracking-wider">
                <Bot size={16} className="text-teal-600" />
                <span>Active AI Workflows Assigned</span>
              </div>
              <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1">
                <CheckCircle2 size={13} />
                Autonomous Dispatch
              </span>
            </div>

            {property.active_automations.length > 0 ? (
              <div className="flex flex-wrap gap-2 pt-1">
                {property.active_automations.map((auto, i) => (
                  <div
                    key={i}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-teal-50 border border-teal-200/60 text-teal-800 text-xs font-semibold shadow-xs"
                  >
                    <Sparkles size={12} className="text-teal-600" />
                    <span>{auto}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 py-1">
                All portfolio-wide automations (Maintenance, Rent Reminders, Support) actively cover this property.
              </p>
            )}
          </div>

          {/* Escalation & Risk Overview */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-slate-50/70 border border-slate-200/70 rounded-2xl p-4">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-700 mb-1">
                <AlertTriangle size={15} className={property.escalations_count > 0 ? 'text-amber-500' : 'text-slate-400'} />
                <span>Human Escalations</span>
              </div>
              <p className="text-2xl font-extrabold text-slate-900 mt-1">
                {property.escalations_count} <span className="text-xs font-medium text-slate-500 font-sans">pending reviews</span>
              </p>
              <p className="text-[11px] text-slate-500 mt-1">
                {property.escalations_count > 0
                  ? 'Urgent tenant inquiries needing property manager decision.'
                  : 'Zero pending escalation bottlenecks.'}
              </p>
            </div>

            <div className="bg-slate-50/70 border border-slate-200/70 rounded-2xl p-4">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-700 mb-1">
                <Calendar size={15} className="text-teal-600" />
                <span>Created Date</span>
              </div>
              <p className="text-base font-bold text-slate-900 mt-1">
                {createdDate}
              </p>
              <p className="text-[11px] text-slate-500 mt-1">
                Property ID: <span className="font-mono font-semibold">{property.property_id}</span>
              </p>
            </div>
          </div>

        </div>

        {/* Footer Actions */}
        <div className="p-4 px-6 border-t border-slate-100 bg-slate-50/60 flex items-center justify-between gap-3">
          <div className="text-xs text-slate-400">
            Status: <strong className="text-slate-700 font-semibold">{property.status}</strong>
          </div>

          <div className="flex items-center gap-3">
            {onToggleStatus && (
              <button
                type="button"
                onClick={() => onToggleStatus(property.property_id, property.status)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-white transition-colors shadow-xs"
              >
                Set {property.status === 'Active' ? 'Inactive' : 'Active'}
              </button>
            )}

            <Link
              href="/conversations"
              onClick={onClose}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold transition-all shadow-md shadow-teal-900/15 active:scale-[0.98]"
            >
              <span>View Property Conversations</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
