import { useState, useEffect } from 'react';

/**
 * Delays updating a value until after `delay` milliseconds have passed
 * since the last change. Use for search inputs to avoid firing an API
 * call on every keystroke.
 */
export function useDebounce<T>(value: T, delay = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
