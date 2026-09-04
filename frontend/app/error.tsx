'use client';

import React, { useEffect } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorBoundary({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error('Unhandled Application Error:', error);
  }, [error]);

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200/80 shadow-xl p-8 text-center animate-in fade-in zoom-in-95 duration-200">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600 mb-5 shadow-sm">
          <AlertTriangle size={28} />
        </div>

        <h2 className="text-xl font-bold text-slate-900 tracking-tight">
          Something went wrong
        </h2>
        <p className="text-sm text-slate-500 mt-2 mb-6 leading-relaxed">
          An unexpected error occurred while rendering this view. You can try refreshing the component or return to the overview dashboard.
        </p>

        {process.env.NODE_ENV !== 'production' && error.message && (
          <div className="mb-6 p-3.5 bg-slate-50 rounded-xl text-left border border-slate-200/70 overflow-hidden">
            <p className="text-xs font-mono text-slate-700 break-words line-clamp-3">
              {error.message}
            </p>
          </div>
        )}

        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => reset()}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold shadow-md shadow-teal-900/10 transition-all active:scale-[0.98]"
          >
            <RefreshCw size={15} />
            <span>Try Again</span>
          </button>

          <Link
            href="/overview"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold transition-all"
          >
            <Home size={15} />
            <span>Overview</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
