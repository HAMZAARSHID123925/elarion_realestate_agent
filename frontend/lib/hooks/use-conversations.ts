'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { ConversationSummary } from '@/lib/types';
import { apiClient } from '@/lib/api-client';
import { useDebounce } from './use-debounce';

export interface ConversationFilters {
  search: string;
  property_id: string;
  unit_id: string;
  channel: string;
  intent: string;
  urgency: string;
  status: string;
  date_range: string; // e.g. "7days" | "30days" | "today"
  page: number;
}

export const DEFAULT_FILTERS: ConversationFilters = {
  search: '',
  property_id: '',
  unit_id: '',
  channel: '',
  intent: '',
  urgency: '',
  status: '',
  date_range: '7days',
  page: 1,
};

export const PAGE_SIZE = 10;

interface UseConversationsReturn {
  items: ConversationSummary[];
  total: number;
  loading: boolean;
  error: string | null;
  filters: ConversationFilters;
  totalPages: number;
  setFilters: (f: Partial<ConversationFilters>) => void;
  resetFilters: () => void;
  refetch: () => void;
}

/**
 * Encapsulates all data-fetching logic for the Conversations page.
 * Reads/writes filters internally; components only consume the returned values.
 */
export function useConversations(): UseConversationsReturn {
  const searchParams = useSearchParams();

  // Initialize filters from URL params (supports bookmarking)
  const [filters, setFiltersState] = useState<ConversationFilters>({
    search: searchParams.get('search') || '',
    property_id: searchParams.get('property_id') || '',
    unit_id: searchParams.get('unit_id') || '',
    channel: searchParams.get('channel') || '',
    intent: searchParams.get('intent') || '',
    urgency: searchParams.get('urgency') || '',
    status: searchParams.get('status') || '',
    date_range: searchParams.get('date_range') || '7days',
    page: parseInt(searchParams.get('page') || '1', 10),
  });

  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce the search text so we don't fire on every keystroke
  const debouncedSearch = useDebounce(filters.search, 350);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {
        limit: String(PAGE_SIZE),
        offset: String((filters.page - 1) * PAGE_SIZE),
      };
      if (debouncedSearch)          params.search       = debouncedSearch;
      if (filters.property_id)      params.property_id  = filters.property_id;
      if (filters.unit_id)          params.unit_id      = filters.unit_id;
      if (filters.channel)          params.channel      = filters.channel;
      if (filters.intent)           params.intent       = filters.intent;
      if (filters.urgency)          params.urgency      = filters.urgency;
      if (filters.status)           params.status       = filters.status;

      // date_range → convert to date_from ISO string
      if (filters.date_range && filters.date_range !== 'all') {
        const now = new Date();
        const daysMap: Record<string, number> = {
          today: 0,
          '7days': 7,
          '30days': 30,
          '90days': 90,
        };
        const days = daysMap[filters.date_range];
        if (days !== undefined) {
          const from = new Date(now);
          from.setDate(from.getDate() - (days === 0 ? 0 : days));
          if (days === 0) {
            from.setHours(0, 0, 0, 0);
          }
          params.date_from = from.toISOString();
        }
      }

      const res = await apiClient.getConversations(params);
      setItems(res.items);
      setTotal(res.total);
    } catch (err: any) {
      console.error('[useConversations] fetch error:', err);
      setError('Failed to load conversations. Make sure the backend server is running on port 8080.');
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, filters.property_id, filters.unit_id, filters.channel, filters.intent, filters.urgency, filters.status, filters.date_range, filters.page]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const setFilters = useCallback((partial: Partial<ConversationFilters>) => {
    setFiltersState((prev) => ({
      ...prev,
      ...partial,
      // Whenever a filter changes (not page), reset to page 1
      page: 'page' in partial ? (partial.page ?? 1) : 1,
    }));
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_FILTERS);
  }, []);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return {
    items,
    total,
    loading,
    error,
    filters,
    totalPages,
    setFilters,
    resetFilters,
    refetch: fetch,
  };
}
