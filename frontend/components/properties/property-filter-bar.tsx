'use client';

import React, { useState } from 'react';
import { Search, SlidersHorizontal, X, RotateCcw } from 'lucide-react';
import { PropertyFilters } from '@/lib/types';

interface PropertyFilterBarProps {
  filters: PropertyFilters;
  cities: string[];
  onApply: (partial: Partial<PropertyFilters>) => void;
  onReset: () => void;
}

const PROPERTY_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'house', label: 'House' },
  { value: 'apartment', label: 'Apartment' },
  { value: 'plot', label: 'Plot' },
  { value: 'commercial', label: 'Commercial' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'All Status' },
  { value: 'Active', label: 'Active' },
  { value: 'Inactive', label: 'Inactive' },
];

export default function PropertyFilterBar({ filters, cities, onApply, onReset }: PropertyFilterBarProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasActiveFilters = filters.status || filters.property_type || filters.city;

  return (
    <div className="space-y-3">
      {/* Main Bar */}
      <div className="flex items-center gap-3">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => onApply({ search: e.target.value })}
            placeholder="Search properties..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400 transition-all shadow-sm"
          />
          {filters.search && (
            <button
              onClick={() => onApply({ search: '' })}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Filter Toggle Button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-semibold transition-all shadow-sm ${
            isExpanded || hasActiveFilters
              ? 'bg-teal-50 border-teal-200 text-teal-700'
              : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'
          }`}
        >
          <SlidersHorizontal size={15} />
          Filter
          {hasActiveFilters && (
            <span className="w-5 h-5 rounded-full bg-teal-600 text-white text-[10px] font-bold flex items-center justify-center">
              {[filters.status, filters.property_type, filters.city].filter(Boolean).length}
            </span>
          )}
        </button>

        {/* Reset Button */}
        {hasActiveFilters && (
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <RotateCcw size={14} />
            Reset
          </button>
        )}
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="flex items-center gap-3 bg-white rounded-xl border border-slate-200 p-4 shadow-sm animate-in slide-in-from-top-2 duration-200">
          {/* Status */}
          <div className="flex-1">
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => onApply({ status: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50/50 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400 transition-all appearance-none cursor-pointer"
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Property Type */}
          <div className="flex-1">
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Type</label>
            <select
              value={filters.property_type}
              onChange={(e) => onApply({ property_type: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50/50 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400 transition-all appearance-none cursor-pointer"
            >
              {PROPERTY_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {/* City */}
          <div className="flex-1">
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">City</label>
            <select
              value={filters.city}
              onChange={(e) => onApply({ city: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50/50 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400 transition-all appearance-none cursor-pointer"
            >
              <option value="">All Cities</option>
              {cities.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
