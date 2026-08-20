'use client';

import React from 'react';
import { AgentActivityTodayItem } from '@/lib/types';
import { Wrench, HelpCircle, DollarSign, FileText } from 'lucide-react';

interface ActivityTodayProps {
  items: AgentActivityTodayItem[];
}

export default function ActivityToday({ items }: ActivityTodayProps) {
  const getWorkflowIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case 'maintenance':
        return <Wrench size={15} className="text-slate-500" />;
      case 'support':
        return <HelpCircle size={15} className="text-slate-500" />;
      case 'rent':
        return <DollarSign size={15} className="text-slate-500" />;
      case 'lease':
        return <FileText size={15} className="text-slate-500" />;
      default:
        return <Wrench size={15} className="text-slate-500" />;
    }
  };

  const getRateColor = (rate: number) => {
    if (rate >= 90) return 'text-emerald-500 font-bold';
    if (rate >= 80) return 'text-emerald-600 font-semibold';
    return 'text-amber-500 font-semibold';
  };

  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
      <h3 className="text-base font-bold text-slate-900 tracking-tight">
        Agent Activity Today
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead>
            <tr className="text-slate-400 border-b border-slate-100 font-semibold">
              <th className="pb-2 font-medium">Workflow</th>
              <th className="pb-2 font-medium text-right">Runs</th>
              <th className="pb-2 font-medium text-right">Rate</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                <td className="py-3 flex items-center gap-2.5 font-medium text-slate-800">
                  {getWorkflowIcon(row.workflow)}
                  <span>{row.workflow}</span>
                </td>
                <td className="py-3 text-right font-semibold text-slate-700">
                  {row.runs}
                </td>
                <td className={`py-3 text-right ${getRateColor(row.rate)}`}>
                  {row.rate}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
