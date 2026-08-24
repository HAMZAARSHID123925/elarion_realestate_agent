'use client';

import React from 'react';
import { MessageSquare, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { ConversationSummary } from '@/lib/types';
import { PAGE_SIZE } from '@/lib/hooks/use-conversations';
import UrgencyBadge from './urgency-badge';
import StatusBadge from './status-badge';
import ChannelBadge from './channel-badge';

// ── Helpers ──────────────────────────────────────────────────────────────────
function formatDateTime(iso: string) {
  if (!iso) return { date: '—', time: '' };
  const d = new Date(iso);
  return {
    date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    time: d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
  };
}

// ── Skeleton row ─────────────────────────────────────────────────────────────
function SkeletonRow() {
  return (
    <tr className="border-b border-slate-100">
      {[...Array(9)].map((_, i) => (
        <td key={i} className="px-4 py-3.5">
          <div className="h-4 bg-slate-100 rounded-md animate-pulse" style={{ width: `${60 + (i % 3) * 20}%` }} />
        </td>
      ))}
    </tr>
  );
}

// ── Props ─────────────────────────────────────────────────────────────────────
interface ConversationsTableProps {
  items: ConversationSummary[];
  total: number;
  loading: boolean;
  error: string | null;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onRowClick: (conversation: ConversationSummary) => void;
}

// ── Pagination component ──────────────────────────────────────────────────────
function Pagination({ page, totalPages, total, onPageChange }: {
  page: number; totalPages: number; total: number; onPageChange: (p: number) => void;
}) {
  const from = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const to   = Math.min(page * PAGE_SIZE, total);

  // Show at most 5 page numbers
  const getPageNumbers = () => {
    if (totalPages <= 5) return Array.from({ length: totalPages }, (_, i) => i + 1);
    const pages: (number | '…')[] = [];
    if (page <= 3) {
      pages.push(1, 2, 3, 4, '…', totalPages);
    } else if (page >= totalPages - 2) {
      pages.push(1, '…', totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
    } else {
      pages.push(1, '…', page - 1, page, page + 1, '…', totalPages);
    }
    return pages;
  };

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
      <p className="text-xs text-slate-500 font-medium">
        Showing <span className="font-bold text-slate-700">{from}–{to}</span> of{' '}
        <span className="font-bold text-slate-700">{total}</span> entries
      </p>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          <ChevronLeft size={14} />
        </button>

        {getPageNumbers().map((p, idx) =>
          p === '…' ? (
            <span key={`ellipsis-${idx}`} className="px-2 text-slate-400 text-sm">…</span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p as number)}
              className={`w-8 h-8 rounded-lg text-xs font-semibold transition-all ${
                p === page
                  ? 'bg-teal-600 text-white shadow-sm'
                  : 'border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {p}
            </button>
          )
        )}

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page === totalPages}
          className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

// ── Main Table ────────────────────────────────────────────────────────────────
export default function ConversationsTable({
  items, total, loading, error, page, totalPages, onPageChange, onRowClick
}: ConversationsTableProps) {

  if (error) {
    return (
      <div className="bg-white border border-red-200 rounded-xl p-12 text-center">
        <div className="text-red-400 text-4xl mb-3">⚠️</div>
        <p className="font-semibold text-slate-800 mb-1">Backend Unreachable</p>
        <p className="text-sm text-slate-500 max-w-md mx-auto">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      {/* Horizontal scroll wrapper — columns stay readable on any viewport */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-sm">
          {/* ── Column Headers ─────────────────────────────────────────── */}
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              {[
                'Date & Time',
                'Property / Unit',
                'Contact',
                'Channel',
                'Intent',
                'Urgency',
                'Workflow',
                'Status',
                'Action',
              ].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>

          {/* ── Rows ───────────────────────────────────────────────────── */}
          <tbody className="divide-y divide-slate-100">
            {loading
              ? [...Array(PAGE_SIZE)].map((_, i) => <SkeletonRow key={i} />)
              : items.length === 0
              ? (
                <tr>
                  <td colSpan={9} className="py-16 text-center">
                    <MessageSquare size={40} className="mx-auto text-slate-300 mb-3" />
                    <p className="font-semibold text-slate-500">No conversations found</p>
                    <p className="text-xs text-slate-400 mt-1">Try adjusting your filters or send a test message through the pipeline.</p>
                  </td>
                </tr>
              )
              : items.map((conv) => {
                const dt = formatDateTime(conv.last_message_at || conv.created_at);
                return (
                  <tr
                    key={conv.conversation_id}
                    onClick={() => onRowClick(conv)}
                    className="hover:bg-slate-50/80 cursor-pointer transition-colors group"
                  >
                    {/* Date & Time */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <div className="font-bold text-slate-800 text-xs">{dt.date}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{dt.time}</div>
                    </td>

                    {/* Property / Unit */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <div className="font-semibold text-slate-800 text-xs">{conv.property_name || '—'}</div>
                      {conv.unit_number && (
                        <div className="text-[11px] text-teal-600 font-medium mt-0.5">Unit {conv.unit_number}</div>
                      )}
                    </td>

                    {/* Contact */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-600 text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                          {conv.contact_name?.charAt(0) ?? '?'}
                        </div>
                        <span className="text-xs font-medium text-slate-800">{conv.contact_name}</span>
                      </div>
                    </td>

                    {/* Channel */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <ChannelBadge channel={conv.channel} size="sm" />
                    </td>

                    {/* Intent */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <span className="text-xs text-slate-600">{conv.intent || '—'}</span>
                    </td>

                    {/* Urgency */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <UrgencyBadge urgency={conv.urgency || 'Normal'} size="sm" />
                    </td>

                    {/* Workflow */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <span className="text-xs text-slate-500">{conv.workflow_triggered || '—'}</span>
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <StatusBadge status={conv.status} size="sm" />
                    </td>

                    {/* Action */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <button
                        onClick={(e) => { e.stopPropagation(); onRowClick(conv); }}
                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-teal-600 hover:text-teal-700 transition-colors"
                      >
                        <Eye size={13} />
                        View
                      </button>
                    </td>
                  </tr>
                );
              })
            }
          </tbody>
        </table>
      </div>

      {/* ── Pagination ──────────────────────────────────────────────────── */}
      {!loading && total > 0 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
}
