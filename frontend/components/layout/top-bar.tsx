'use client';

import React from 'react';
import { Search, Bell, SlidersHorizontal, User } from 'lucide-react';

export default function TopBar() {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between sticky top-0 z-10">
      {/* Page Context Breadcrumb / Title */}
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-bold text-slate-800 tracking-tight">Overview</h2>
      </div>

      {/* Right Controls: Search Operations, Notifications, User Profile */}
      <div className="flex items-center gap-4">
        {/* Search Operations Input */}
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search operations..."
            className="w-64 bg-slate-50 text-slate-800 placeholder-slate-400 text-sm pl-9 pr-4 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
          />
        </div>

        <button className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors relative">
          <Bell size={19} />
          <span className="w-2 h-2 bg-emerald-500 rounded-full absolute top-1.5 right-1.5" />
        </button>

        <button className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors">
          <SlidersHorizontal size={19} />
        </button>

        <div className="h-6 w-[1px] bg-slate-200 mx-1" />

        {/* User Profile Avatar */}
        <div className="flex items-center gap-3 cursor-pointer">
          <div className="w-8 h-8 rounded-full bg-slate-800 text-white font-medium text-xs flex items-center justify-center border border-slate-200 shadow-sm">
            John
          </div>
        </div>
      </div>
    </header>
  );
}
