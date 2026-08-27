'use client';

import React from 'react';
import { Wrench } from 'lucide-react';
import { RecentActivityItem } from '@/lib/types';

interface RecentActivityProps {
  items?: RecentActivityItem[];
}

export default function RecentActivity({ items }: RecentActivityProps) {
  const displayItems = items && items.length > 0 ? items : [
    { agent: 'Maintenance Agent', summary: 'Scheduled plumber for Unit 4B clog issue.', time_str: '10:42 AM' }
  ];

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-bold text-slate-900 tracking-tight">Recent Activity</h3>
      
      <div className="space-y-2">
        {displayItems.map((item, idx) => (
          <div key={idx} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center">
                <Wrench size={18} />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">{item.agent}</h4>
                <p className="text-xs text-slate-500 font-medium">{item.summary}</p>
              </div>
            </div>
            <span className="text-xs font-medium text-slate-400">{item.time_str}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

