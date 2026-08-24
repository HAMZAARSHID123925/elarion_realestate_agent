'use client';

import React, { useEffect, useState, useRef } from 'react';
import { X, CheckCircle2, Building2, Hash, Calendar, Workflow } from 'lucide-react';
import { ConversationDetail, ConversationMessage } from '@/lib/types';
import { apiClient } from '@/lib/api-client';
import { getSenderToken } from '@/lib/design-tokens';
import UrgencyBadge from './urgency-badge';
import StatusBadge from './status-badge';
import ChannelBadge from './channel-badge';

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatTime(iso: string) {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function formatDateLong(iso: string) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric'
  });
}

// ── Message Bubble ────────────────────────────────────────────────────────────
function MessageBubble({ msg }: { msg: ConversationMessage }) {
  const token = getSenderToken(msg.sender_type as 'tenant' | 'ai' | 'system');
  const isSystem = msg.sender_type === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <div className={`px-4 py-1.5 rounded-full text-[11px] font-medium ${token.bubbleBg} ${token.bubbleText}`}>
          {msg.system_event || msg.content}
        </div>
      </div>
    );
  }

  const isAI = msg.sender_type === 'ai';
  return (
    <div className={`flex flex-col ${isAI ? 'items-end' : 'items-start'}`}>
      <span className={`text-[10px] font-bold mb-1 px-2 py-0.5 rounded ${token.nameBadgeBg}`}>
        {msg.sender_name}
      </span>
      <div className={`max-w-[85%] px-3 py-2.5 rounded-xl rounded-${isAI ? 'tr' : 'tl'}-sm text-sm ${token.bubbleBg} ${token.bubbleText}`}>
        {msg.content}
      </div>
      <span className="text-[10px] text-slate-400 mt-1 px-1">{formatTime(msg.timestamp)}</span>
    </div>
  );
}

// ── Main Drawer ───────────────────────────────────────────────────────────────
interface ConversationDrawerProps {
  conversationId: string | null;
  onClose: () => void;
  onReviewed?: () => void;
}

export default function ConversationDrawer({
  conversationId, onClose, onReviewed
}: ConversationDrawerProps) {
  const [detail, setDetail]         = useState<ConversationDetail | null>(null);
  const [loading, setLoading]       = useState(false);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewed, setReviewed]     = useState(false);
  const transcriptRef               = useRef<HTMLDivElement>(null);

  // Fetch full detail when a conversation is selected
  useEffect(() => {
    if (!conversationId) { setDetail(null); return; }
    setLoading(true);
    setReviewed(false);
    apiClient.getConversationDetail(conversationId)
      .then((d) => { setDetail(d); setReviewed(d.is_reviewed); })
      .catch((err) => console.error('[ConversationDrawer] fetch error:', err))
      .finally(() => setLoading(false));
  }, [conversationId]);

  // Auto-scroll transcript to bottom when messages load
  useEffect(() => {
    if (detail?.messages?.length && transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [detail?.messages]);

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  const handleMarkReviewed = async () => {
    if (!detail || reviewed) return;
    setReviewLoading(true);
    try {
      await apiClient.markConversationReviewed(detail.conversation_id);
      setReviewed(true);
      if (onReviewed) onReviewed();
    } catch (err) {
      console.error('[ConversationDrawer] review error:', err);
    } finally {
      setReviewLoading(false);
    }
  };

  const isOpen = Boolean(conversationId);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/30 backdrop-blur-sm z-40 transition-opacity duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Drawer Panel */}
      <aside
        className={`fixed top-0 right-0 h-full w-[480px] max-w-[95vw] bg-white shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between p-5 border-b border-slate-200 flex-shrink-0">
          {loading || !detail ? (
            <div className="space-y-2 flex-1">
              <div className="h-5 bg-slate-100 rounded w-2/3 animate-pulse" />
              <div className="h-4 bg-slate-100 rounded w-1/3 animate-pulse" />
            </div>
          ) : (
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base font-bold text-slate-900 truncate">{detail.contact_name}</h2>
                <span className="text-xs text-slate-400 font-mono">{detail.conversation_id}</span>
              </div>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <ChannelBadge channel={detail.channel} size="sm" />
                <UrgencyBadge urgency={detail.urgency || 'Normal'} size="sm" />
                <StatusBadge status={detail.status} size="sm" />
                {reviewed && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded">
                    <CheckCircle2 size={10} /> Reviewed
                  </span>
                )}
              </div>
            </div>
          )}
          <button
            id="drawer-close-btn"
            onClick={onClose}
            className="ml-3 p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors flex-shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* ── Meta Info ───────────────────────────────────────────────── */}
        {detail && !loading && (
          <div className="px-5 py-3 border-b border-slate-100 flex-shrink-0 grid grid-cols-2 gap-x-6 gap-y-2">
            {detail.property_name && (
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <Building2 size={13} className="text-slate-400 flex-shrink-0" />
                <span>{detail.property_name}</span>
              </div>
            )}
            {detail.unit_number && (
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <Hash size={13} className="text-slate-400 flex-shrink-0" />
                <span>Unit {detail.unit_number}</span>
              </div>
            )}
            {detail.workflow_triggered && (
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <Workflow size={13} className="text-slate-400 flex-shrink-0" />
                <span>{detail.workflow_triggered}</span>
              </div>
            )}
            {detail.created_at && (
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <Calendar size={13} className="text-slate-400 flex-shrink-0" />
                <span>{formatDateLong(detail.created_at)}</span>
              </div>
            )}
          </div>
        )}

        {/* ── Transcript ──────────────────────────────────────────────── */}
        <div
          ref={transcriptRef}
          className="flex-1 overflow-y-auto px-5 py-4 space-y-3 bg-slate-50/50"
        >
          {loading ? (
            [...Array(5)].map((_, i) => (
              <div key={i} className={`flex ${i % 2 === 0 ? 'justify-start' : 'justify-end'}`}>
                <div className={`h-10 bg-slate-100 rounded-xl animate-pulse ${i % 2 === 0 ? 'w-2/3' : 'w-1/2'}`} />
              </div>
            ))
          ) : !detail?.messages?.length ? (
            <div className="text-center py-12">
              <p className="text-sm text-slate-400">No messages in this conversation yet.</p>
            </div>
          ) : (
            detail.messages.map((msg) => (
              <MessageBubble key={msg.message_id} msg={msg} />
            ))
          )}
        </div>

        {/* ── Footer Action ────────────────────────────────────────────── */}
        <div className="p-4 border-t border-slate-200 flex-shrink-0">
          <button
            id="drawer-review-btn"
            onClick={handleMarkReviewed}
            disabled={reviewed || reviewLoading || loading || !detail}
            className={`w-full py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all ${
              reviewed
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 cursor-default'
                : 'bg-teal-600 hover:bg-teal-500 text-white shadow-sm active:scale-[0.98] disabled:opacity-50'
            }`}
          >
            <CheckCircle2 size={16} />
            {reviewLoading ? 'Marking…' : reviewed ? 'Already Reviewed' : 'Mark as Reviewed'}
          </button>
        </div>
      </aside>
    </>
  );
}
