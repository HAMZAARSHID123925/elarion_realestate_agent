'use client';

import React, { useState, Suspense } from 'react';
import { MessageSquare } from 'lucide-react';
import { useConversations } from '@/lib/hooks/use-conversations';
import { ConversationSummary } from '@/lib/types';
import FilterBar from '@/components/conversations/filter-bar';
import ConversationsTable from '@/components/conversations/conversations-table';
import ConversationDrawer from '@/components/conversations/conversation-drawer';

// Inner page — wrapped in Suspense to satisfy useSearchParams() requirement in Next.js 15
function ConversationsPageInner() {
  const {
    items, total, loading, error,
    filters, totalPages,
    setFilters, resetFilters, refetch,
  } = useConversations();

  const [selectedId, setSelectedId] = useState<string | null>(null);

  const handleRowClick = (conv: ConversationSummary) => {
    setSelectedId(conv.conversation_id);
  };

  const handleDrawerClose = () => setSelectedId(null);

  // After marking reviewed, refresh the table row's status visually
  const handleReviewed = () => refetch();

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-12">
      {/* ── Page Header ─────────────────────────────────────────────── */}
      <div>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-teal-50 flex items-center justify-center">
            <MessageSquare size={20} className="text-teal-600" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Conversations</h1>
            <p className="text-sm text-slate-500 font-medium mt-0.5">
              Every interaction handled by TenantFlow.
              {!loading && total > 0 && (
                <span className="ml-2 font-bold text-slate-700">{total} total</span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* ── Filter Bar ──────────────────────────────────────────────── */}
      <FilterBar
        filters={filters}
        onApply={(partial) => setFilters(partial)}
        onReset={resetFilters}
      />

      {/* ── Data Table ──────────────────────────────────────────────── */}
      <ConversationsTable
        items={items}
        total={total}
        loading={loading}
        error={error}
        page={filters.page}
        totalPages={totalPages}
        onPageChange={(p) => setFilters({ page: p })}
        onRowClick={handleRowClick}
      />

      {/* ── Detail Drawer ────────────────────────────────────────────── */}
      <ConversationDrawer
        conversationId={selectedId}
        onClose={handleDrawerClose}
        onReviewed={handleReviewed}
      />
    </div>
  );
}

// Next.js 15 requires Suspense around useSearchParams()
export default function ConversationsPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <ConversationsPageInner />
    </Suspense>
  );
}
