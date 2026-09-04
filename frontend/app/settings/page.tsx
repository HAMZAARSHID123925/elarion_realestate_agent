'use client';

import React from 'react';
import { Settings, Shield, Bell, Key, Database, Sliders } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center text-teal-600 shadow-sm">
          <Settings size={22} />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">System Settings</h1>
          <p className="text-sm text-slate-500 font-medium mt-0.5">
            Configure platform parameters, model credentials, security keys, and channel webhooks.
          </p>
        </div>
      </div>

      {/* Settings Sections */}
      <div className="space-y-6">
        {/* Security & Authentication */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
          <div className="flex items-center gap-2.5 mb-4">
            <Shield size={18} className="text-teal-600" />
            <h3 className="font-bold text-slate-900 text-base">Security & Authentication</h3>
          </div>
          <div className="space-y-4 max-w-2xl text-xs">
            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <div>
                <span className="font-semibold text-slate-700 block">JWT Token Expiry</span>
                <span className="text-slate-400">Configured via JWT_ACCESS_TOKEN_EXPIRE_MINUTES</span>
              </div>
              <span className="font-mono bg-slate-100 px-2.5 py-1 rounded text-slate-700">60 minutes</span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <div>
                <span className="font-semibold text-slate-700 block">API Rate Limiting</span>
                <span className="text-slate-400">Protects endpoints against brute-force and spam</span>
              </div>
              <span className="font-mono bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded border border-emerald-200">
                Enabled (100 req/min)
              </span>
            </div>
          </div>
        </div>

        {/* Database & Pool Settings */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
          <div className="flex items-center gap-2.5 mb-4">
            <Database size={18} className="text-teal-600" />
            <h3 className="font-bold text-slate-900 text-base">Database Connection Pool</h3>
          </div>
          <div className="space-y-4 max-w-2xl text-xs">
            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <div>
                <span className="font-semibold text-slate-700 block">Engine & Target</span>
                <span className="text-slate-400">PostgreSQL (Serverless Neon Pool)</span>
              </div>
              <span className="font-mono bg-slate-100 px-2.5 py-1 rounded text-slate-700">Neon Cloud</span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <div>
                <span className="font-semibold text-slate-700 block">Pool Pool Size & Idle Timeout</span>
                <span className="text-slate-400">Managed via database.pool.AsyncConnectionPool</span>
              </div>
              <span className="font-mono bg-slate-100 px-2.5 py-1 rounded text-slate-700">max_size=5, idle=120s</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
