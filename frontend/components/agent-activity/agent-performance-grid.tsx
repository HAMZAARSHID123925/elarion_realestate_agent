'use client';

import React from 'react';
import { Wrench, HelpCircle, DollarSign, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

interface AgentPerformanceItem {
  agent: string;
  runs: number;
  ai_resolved: number;
  escalated: number;
  failed: number;
  auto_rate: number;
}

interface PerformanceGridProps {
  performance: AgentPerformanceItem[];
  selectedAgent: string;
  onSelectAgent: (agent: string) => void;
}

export default function AgentPerformanceGrid({
  performance,
  selectedAgent,
  onSelectAgent
}: PerformanceGridProps) {
  const getAgentConfig = (name: string) => {
    const lower = name.toLowerCase();
    if (lower.includes('maintenance')) {
      return {
        icon: <Wrench size={18} className="text-blue-600" />,
        bgIcon: 'bg-blue-50',
        badgeColor: 'border-blue-200 text-blue-700 bg-blue-50',
        description: 'HVAC, plumbing, emergency tickets & vendor matching'
      };
    }
    if (lower.includes('rent') || lower.includes('collection')) {
      return {
        icon: <DollarSign size={18} className="text-emerald-600" />,
        bgIcon: 'bg-emerald-50',
        badgeColor: 'border-emerald-200 text-emerald-700 bg-emerald-50',
        description: 'Day-30 & Day-35 overdue rent followups & escalation'
      };
    }
    if (lower.includes('lease') || lower.includes('renewal')) {
      return {
        icon: <FileText size={18} className="text-purple-600" />,
        bgIcon: 'bg-purple-50',
        badgeColor: 'border-purple-200 text-purple-700 bg-purple-50',
        description: 'Lease expiration windows, renewals & tenant options'
      };
    }
    return {
      icon: <HelpCircle size={18} className="text-teal-600" />,
      bgIcon: 'bg-teal-50',
      badgeColor: 'border-teal-200 text-teal-700 bg-teal-50',
      description: 'Pinecone RAG lease Q&A, amenity FAQs & listings'
    };
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-900 tracking-tight">
            AI Agent Workforce Performance
          </h2>
          <p className="text-xs text-slate-500 font-medium">
            Autonomous resolution efficiency breakdown by agent specialty
          </p>
        </div>
        {selectedAgent !== 'all' && (
          <button
            onClick={() => onSelectAgent('all')}
            className="text-xs font-semibold text-teal-600 hover:text-teal-700 hover:underline"
          >
            Clear Agent Filter
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {performance.map((item) => {
          const config = getAgentConfig(item.agent);
          const isSelected = selectedAgent.toLowerCase() === item.agent.toLowerCase();

          return (
            <div
              key={item.agent}
              onClick={() => onSelectAgent(isSelected ? 'all' : item.agent)}
              className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                isSelected
                  ? 'bg-slate-900 text-white border-slate-900 shadow-md ring-2 ring-teal-500/50'
                  : 'bg-white border-slate-200/90 hover:border-slate-300 shadow-sm text-slate-900'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${isSelected ? 'bg-slate-800' : config.bgIcon}`}>
                    {config.icon}
                  </div>
                  <div>
                    <h3 className={`text-sm font-bold tracking-tight ${isSelected ? 'text-white' : 'text-slate-900'}`}>
                      {item.agent}
                    </h3>
                    <p className={`text-[11px] ${isSelected ? 'text-slate-400' : 'text-slate-500'}`}>
                      {item.runs} total runs
                    </p>
                  </div>
                </div>

                <span
                  className={`text-xs font-extrabold px-2 py-0.5 rounded-full border ${
                    isSelected
                      ? 'bg-teal-500/20 text-teal-300 border-teal-500/30'
                      : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  }`}
                >
                  {item.auto_rate}%
                </span>
              </div>

              <p className={`text-[11px] mt-3 line-clamp-2 leading-relaxed ${isSelected ? 'text-slate-300' : 'text-slate-500'}`}>
                {config.description}
              </p>

              {/* Progress bar */}
              <div className={`w-full h-1.5 rounded-full mt-3 overflow-hidden ${isSelected ? 'bg-slate-800' : 'bg-slate-100'}`}>
                <div
                  className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, item.auto_rate))}%` }}
                />
              </div>

              {/* Pill Stats */}
              <div className="flex items-center justify-between text-[11px] mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800">
                <span className={`inline-flex items-center gap-1 ${isSelected ? 'text-slate-300' : 'text-slate-600'}`}>
                  <CheckCircle2 size={12} className="text-emerald-500" />
                  {item.ai_resolved} Resolved
                </span>
                <span className={`inline-flex items-center gap-1 ${isSelected ? 'text-slate-400' : 'text-slate-500'}`}>
                  <AlertCircle size={12} className="text-amber-500" />
                  {item.escalated} Escalated
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
