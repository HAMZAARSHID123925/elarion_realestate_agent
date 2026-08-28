'use client';

import React, { useState, Suspense } from 'react';
import { Building2, Plus } from 'lucide-react';
import { useProperties } from '@/lib/hooks/use-properties';
import PropertyCard from '@/components/properties/property-card';
import PropertyFilterBar from '@/components/properties/property-filter-bar';
import AddPropertyModal from '@/components/properties/add-property-modal';
import DeleteConfirmModal from '@/components/properties/delete-confirm-modal';
import { PropertyDashboardCard } from '@/lib/types';

function PropertiesPageInner() {
  const {
    items, total, loading, error,
    filters, cities,
    setFilters, resetFilters, refetch,
  } = useProperties();

  const [showAddModal, setShowAddModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);

  const handleAddSuccess = () => {
    refetch();
  };

  const handleDeleteRequest = (propertyId: string) => {
    const prop = items.find((p) => p.property_id === propertyId);
    setDeleteTarget({
      id: propertyId,
      title: prop?.title || 'Untitled Property',
    });
  };

  const handleDeleted = () => {
    setDeleteTarget(null);
    refetch();
  };

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-12">
      {/* ── Page Header ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-teal-50 flex items-center justify-center">
              <Building2 size={20} className="text-teal-600" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Properties</h1>
              <p className="text-sm text-slate-500 font-medium mt-0.5">
                Manage operations and AI agent activity across your portfolio.
                {!loading && total > 0 && (
                  <span className="ml-2 font-bold text-slate-700">{total} properties</span>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* + Add Property Button */}
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold shadow-md shadow-teal-900/15 transition-all active:scale-[0.98] flex-shrink-0"
        >
          <Plus size={16} />
          Add Property
        </button>
      </div>

      {/* ── Filter Bar ──────────────────────────────────────────────── */}
      <PropertyFilterBar
        filters={filters}
        cities={cities}
        onApply={(partial) => setFilters(partial)}
        onReset={resetFilters}
      />

      {/* ── Loading State ────────────────────────────────────────────── */}
      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-slate-500 font-medium">Loading properties from database...</p>
          </div>
        </div>
      )}

      {/* ── Error State ──────────────────────────────────────────────── */}
      {!loading && error && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center">
          <p className="text-red-600 font-semibold text-sm mb-2">Failed to load properties</p>
          <p className="text-red-500 text-xs mb-4">{error}</p>
          <button
            onClick={refetch}
            className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-500 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* ── Empty State ──────────────────────────────────────────────── */}
      {!loading && !error && items.length === 0 && (
        <div className="bg-white border border-slate-200 border-dashed rounded-2xl p-12 text-center">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
            <Building2 size={28} className="text-slate-400" />
          </div>
          <h3 className="text-lg font-bold text-slate-700 mb-1">No properties found</h3>
          <p className="text-sm text-slate-500 mb-6">
            {filters.search || filters.status || filters.property_type || filters.city
              ? 'Try adjusting your filters or search term.'
              : 'Get started by adding your first property.'}
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold transition-all"
          >
            <Plus size={16} />
            Add Property
          </button>
        </div>
      )}

      {/* ── Property Cards Grid ──────────────────────────────────────── */}
      {!loading && !error && items.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {items.map((property) => (
            <PropertyCard
              key={property.property_id}
              property={property}
              onDelete={handleDeleteRequest}
              onRefresh={refetch}
            />
          ))}
        </div>
      )}

      {/* ── Add Property Modal ────────────────────────────────────────── */}
      <AddPropertyModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleAddSuccess}
      />

      {/* ── Delete Confirmation Modal ─────────────────────────────────── */}
      <DeleteConfirmModal
        isOpen={!!deleteTarget}
        propertyId={deleteTarget?.id || null}
        propertyTitle={deleteTarget?.title || ''}
        onClose={() => setDeleteTarget(null)}
        onDeleted={handleDeleted}
      />
    </div>
  );
}

// Next.js 15 Suspense wrapper
export default function PropertiesPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <PropertiesPageInner />
    </Suspense>
  );
}
