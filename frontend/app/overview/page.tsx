'use client';

import React, { useEffect, useState } from 'react';
import SummaryCards from '@/components/overview/summary-cards';
import NeedsAttention from '@/components/overview/needs-attention';
import ActivityToday from '@/components/overview/activity-today';
import AutomationStatus from '@/components/overview/automation-status';
import RecentActivity from '@/components/overview/recent-activity';
import { OverviewDashboardData } from '@/lib/types';
import { apiClient } from '@/lib/api-client';
import { RefreshCw } from 'lucide-react';

export default function OverviewPage() {
  const [data, setData] = useState<OverviewDashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getOverviewData();
      setData(res);
    } catch (err: any) {
      console.error('Error loading overview data:', err);
      setError('Failed to connect to backend server. Make sure FastAPI server is running on port 8080.');
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
            Good morning, John.
          </h1>
          <p className="text-sm font-medium text-slate-500 mt-1">
            Here's what TenantFlow handled today.
          </p>
        </div>

        <button
          onClick={fetchOverview}
          disabled={loading}
          className="flex items-center gap-2 text-xs font-semibold text-slate-600 bg-white border border-slate-200 px-3.5 py-2 rounded-lg hover:bg-slate-50 transition-all shadow-sm"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin text-emerald-500' : ''} />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* 1. Top Stat Cards */}
      {data && <SummaryCards stats={data.stats} />}

      {/* 2. Middle Grid: Needs Attention vs Right Sidebar */}
      <div className="grid grid-cols-3 gap-8 items-start">
        {/* Left 2 Columns: Needs Attention */}
        <div className="col-span-2 space-y-8">
          {data && (
            <NeedsAttention
              items={data.needs_attention}
              onActionComplete={fetchOverview}
            />
          )}
          <RecentActivity items={data?.recent_activity} />

        </div>

        {/* Right 1 Column: Agent Activity Today & Automation Status */}
        <div className="space-y-6">
          {data && <ActivityToday items={data.agent_activity_today} />}
          <AutomationStatus />
        </div>
      </div>
    </div>
  );
}
