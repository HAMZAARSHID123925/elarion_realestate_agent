'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Sparkles, 
  Users, 
  BarChart3, 
  Building2, 
  Workflow, 
  Settings, 
  Plug, 
  HelpCircle,
  Plus
} from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Overview', href: '/overview', icon: LayoutDashboard },
  { name: 'Conversations', href: '/conversations', icon: MessageSquare },
  { name: 'Automations', href: '/automations', icon: Sparkles },
  { name: 'Agent Activity', href: '/agent-activity', icon: Users },
  { name: 'Reports', href: '/reports', icon: BarChart3 },
  { name: 'Properties', href: '/properties', icon: Building2 },
  { name: 'Agents & Workflows', href: '/agents-workflows', icon: Workflow },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-[#1E293B] text-slate-300 flex flex-col h-screen sticky top-0 border-r border-slate-800 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center font-bold text-white text-lg justify-center shadow-lg shadow-emerald-500/20">
            TF
          </div>
          <div>
            <h1 className="font-bold text-white text-base tracking-tight leading-none">TenantFlow.ai</h1>
            <span className="text-xs text-slate-400 font-medium">AI Operations Layer</span>
          </div>
        </div>
      </div>

      {/* New Automation Button */}
      <div className="p-4">
        <button className="w-full bg-teal-600 hover:bg-teal-500 text-white font-medium text-sm py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 transition-all shadow-md shadow-teal-900/20 active:scale-[0.98]">
          <Plus size={18} />
          <span>New Automation</span>
        </button>
      </div>

      {/* Main Navigation Links */}
      <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-[#0F172A] text-emerald-400 border-l-4 border-emerald-400 font-semibold pl-2'
                  : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
              }`}
            >
              <Icon size={19} className={isActive ? 'text-emerald-400' : 'text-slate-400'} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom Secondary Nav */}
      <div className="p-3 border-t border-slate-800/60 space-y-1">
        <Link
          href="/integrations"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800/60 hover:text-white transition-colors"
        >
          <Plug size={18} />
          <span>Integrations</span>
        </Link>
        <Link
          href="/help"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800/60 hover:text-white transition-colors"
        >
          <HelpCircle size={18} />
          <span>Help</span>
        </Link>
      </div>
    </aside>
  );
}
