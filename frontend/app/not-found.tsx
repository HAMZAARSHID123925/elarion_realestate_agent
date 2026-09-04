import React from 'react';
import Link from 'next/link';
import { FileQuestion, ArrowLeft, Home } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200/80 shadow-xl p-8 text-center animate-in fade-in zoom-in-95 duration-200">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600 mb-5 shadow-sm">
          <FileQuestion size={28} />
        </div>

        <h2 className="text-xl font-bold text-slate-900 tracking-tight">
          Page Not Found
        </h2>
        <p className="text-sm text-slate-500 mt-2 mb-6 leading-relaxed">
          The page or operational resource you requested does not exist or has been moved.
        </p>

        <div className="flex items-center justify-center gap-3">
          <Link
            href="/overview"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold shadow-md shadow-teal-900/10 transition-all active:scale-[0.98]"
          >
            <Home size={16} />
            <span>Go to Dashboard</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
