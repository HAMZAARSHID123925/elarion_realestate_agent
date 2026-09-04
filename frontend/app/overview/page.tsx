'use client';

import React, { useEffect, useState, useMemo } from 'react';
import SummaryCards from '@/components/overview/summary-cards';
import NeedsAttention from '@/components/overview/needs-attention';
import ActivityToday from '@/components/overview/activity-today';
import AutomationStatus from '@/components/overview/automation-status';
import RecentActivity from '@/components/overview/recent-activity';
import { OverviewDashboardData } from '@/lib/types';
import { apiClient } from '@/lib/api-client';
import { RefreshCw, AlertCircle } from 'lucide-react';

export default function OverviewPage() {
  const [data, setData] = useState<OverviewDashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  }, []);

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getOverviewData();
      setData(res);
    } catch (err: unknown) {
      console.error('Error loading overview data:', err);
      const msg = err instanceof Error ? err.message : 'Failed to connect to backend server. Make sure FastAPI server is running.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {greeting}
          </h1>
          <p className="text-sm font-medium text-slate-500 mt-1">
            Here's what Elarion Agent handled today across your properties.
          </p>
        </div>

        <button
          onClick={fetchOverview}
          disabled={loading}
          className="flex items-center gap-2 text-xs font-semibold text-slate-600 bg-white border border-slate-200 px-3.5 py-2 rounded-lg hover:bg-slate-50 transition-all shadow-sm active:scale-[0.98] disabled:opacity-60"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin text-teal-600' : ''} />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* ── Loading State ────────────────────────────────────────────── */}
      {loading && !data && (
        <div className="flex items-center justify-center h-72">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-slate-500 font-medium">Loading operations data from database...</p>
          </div>
        </div>
      )}

      {/* ── Error State ──────────────────────────────────────────────── */}
      {!loading && error && !data && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-8 text-center max-w-xl mx-auto">
          <div className="w-12 h-12 mx-auto rounded-xl bg-red-100 flex items-center justify-center text-red-600 mb-3">
            <AlertCircle size={24} />
          </div>
          <h3 className="text-red-700 font-bold text-base mb-1">Failed to load overview data</h3>
          <p className="text-red-600 text-xs mb-5">{error}</p>
          <button
            onClick={fetchOverview}
            className="px-5 py-2.5 rounded-xl bg-teal-600 text-white text-sm font-semibold hover:bg-teal-500 transition-colors shadow-sm"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* ── Dashboard Content ────────────────────────────────────────── */}
      {data && (
        <>
          {/* 1. Top Stat Cards */}
          <SummaryCards stats={data.stats} />

          {/* 2. Middle Grid: Needs Attention vs Right Sidebar */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
            {/* Left 2 Columns: Needs Attention & Recent Activity */}
            <div className="lg:col-span-2 space-y-8">
              <NeedsAttention
                items={data.needs_attention}
                onActionComplete={fetchOverview}
              />
              <RecentActivity items={data.recent_activity} />
            </div>

            {/* Right 1 Column: Agent Activity Today & Automation Status */}
            <div className="space-y-6">
              <ActivityToday items={data.agent_activity_today} />
              <AutomationStatus />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
