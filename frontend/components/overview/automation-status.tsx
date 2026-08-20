'use client';

import React from 'react';

export default function AutomationStatus() {
  const automations = [
    { name: 'Maintenance Triage', status: 'Active', badge: 'bg-slate-100 text-slate-600' },
    { name: 'Resident Support', status: 'Active', badge: 'bg-slate-100 text-slate-600' },
    { name: 'Rent Collection', status: 'Learning', badge: 'bg-amber-50 text-amber-600' }
  ];

  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
      <h3 className="text-base font-bold text-slate-900 tracking-tight">
        Automation Status
      </h3>

      <div className="space-y-3">
        {automations.map((item, idx) => (
          <div key={idx} className="flex items-center justify-between text-xs py-1">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${item.status === 'Active' ? 'bg-emerald-500' : 'bg-amber-400'}`} />
              <span className="font-semibold text-slate-800">{item.name}</span>
            </div>
            <span className={`px-2.5 py-0.5 rounded-full font-medium text-[11px] ${item.badge}`}>
              {item.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
