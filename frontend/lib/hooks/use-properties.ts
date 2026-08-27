'use client';

import { useState, useEffect, useCallback } from 'react';
import { PropertyDashboardCard, PropertyFilters } from '@/lib/types';
import { apiClient } from '@/lib/api-client';
import { useDebounce } from './use-debounce';

export const DEFAULT_PROPERTY_FILTERS: PropertyFilters = {
  search: '',
  status: '',
  property_type: '',
  city: '',
};

interface UsePropertiesReturn {
  items: PropertyDashboardCard[];
  total: number;
  loading: boolean;
  error: string | null;
  filters: PropertyFilters;
  cities: string[];
  setFilters: (f: Partial<PropertyFilters>) => void;
  resetFilters: () => void;
  refetch: () => void;
}

/**
 * Encapsulates all data-fetching logic for the Properties Dashboard page.
 * Fetches property cards with real conversation stats from PostgreSQL.
 */
export function useProperties(): UsePropertiesReturn {
  const [filters, setFiltersState] = useState<PropertyFilters>(DEFAULT_PROPERTY_FILTERS);
  const [items, setItems] = useState<PropertyDashboardCard[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cities, setCities] = useState<string[]>([]);

  // Debounce search input so we don't fire on every keystroke
  const debouncedSearch = useDebounce(filters.search, 350);

  // Fetch cities for filter dropdown
  useEffect(() => {
    apiClient.getCities()
      .then(setCities)
      .catch(() => setCities([]));
  }, []);

  const fetchProperties = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (debouncedSearch)      params.search        = debouncedSearch;
      if (filters.status)       params.status         = filters.status;
      if (filters.property_type) params.property_type  = filters.property_type;
      if (filters.city)          params.city           = filters.city;

      const res = await apiClient.getPropertyDashboardCards(params);
      setItems(res.items);
      setTotal(res.total);
    } catch (err: any) {
      console.error('[useProperties] fetch error:', err);
      setError('Failed to load properties. Make sure the backend server is running on port 8080.');
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, filters.status, filters.property_type, filters.city]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  const setFilters = useCallback((partial: Partial<PropertyFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...partial }));
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_PROPERTY_FILTERS);
  }, []);

  return {
    items,
    total,
    loading,
    error,
    filters,
    cities,
    setFilters,
    resetFilters,
    refetch: fetchProperties,
  };
}
