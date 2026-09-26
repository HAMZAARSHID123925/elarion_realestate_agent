'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/lib/api-client';
import { AgentActivityData } from '@/lib/types';
import ActivityHeader from '@/components/agent-activity/activity-header';
import ActivityMetrics from '@/components/agent-activity/activity-metrics';
import AgentPerformanceGrid from '@/components/agent-activity/agent-performance-grid';
import ActivityFeed from '@/components/agent-activity/activity-feed';
import ActivityDetailDrawer from '@/components/agent-activity/activity-detail-drawer';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function AgentActivityPage() {
  const [data, setData] = useState<AgentActivityData | null>(null);
  const [period, setPeriod] = useState<string>('today');
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [selectedExecution, setSelectedExecution] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (selectedPeriod: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.getAgentActivity(selectedPeriod);
      setData(response);
    } catch (err: any) {
      console.error('Failed to load agent activity:', err);
      setError(err?.message || 'Unable to connect to FastAPI backend');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(period);
  }, [fetchData, period]);

  const handlePeriodChange = (newPeriod: string) => {
    setPeriod(newPeriod);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* 1. Header with Period Selectors */}
      <ActivityHeader
        period={period}
        onPeriodChange={handlePeriodChange}
        onRefresh={() => fetchData(period)}
        isLoading={isLoading}
      />

      {/* Error Banner with Retry */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <AlertCircle size={16} />
            <span>
              <strong>Backend Error:</strong> {error}
            </span>
          </div>
          <button
            onClick={() => fetchData(period)}
            className="flex items-center gap-1 font-bold underline hover:text-rose-900"
          >
            <RefreshCw size={12} />
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && !data ? (
        <div className="space-y-6 animate-pulse">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-28 bg-slate-200/70 rounded-2xl" />
            ))}
          </div>
          <div className="h-44 bg-slate-200/70 rounded-2xl" />
          <div className="h-80 bg-slate-200/70 rounded-2xl" />
        </div>
      ) : data ? (
        <>
          {/* 2. Top Metric KPI Cards */}
          <ActivityMetrics metrics={data.metrics} />

          {/* 3. Agent Workforce Performance Breakdown */}
          <AgentPerformanceGrid
            performance={data.workflow_performance}
            selectedAgent={selectedAgent}
            onSelectAgent={setSelectedAgent}
          />

          {/* 4. Real-Time Autonomous Action Audit Feed */}
          <ActivityFeed
            executions={data.recent_executions}
            selectedAgent={selectedAgent}
            onSelectExecution={setSelectedExecution}
          />

          {/* 5. Detail Drawer Modal */}
          <ActivityDetailDrawer
            execution={selectedExecution}
            onClose={() => setSelectedExecution(null)}
          />
        </>
      ) : null}
    </div>
  );
}
