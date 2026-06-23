import { useEffect, useState } from 'react';

function getInitialPreference(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** Respeta `prefers-reduced-motion` del sistema para apagar animaciones decorativas. */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(getInitialPreference);

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener('change', handler);
    return () => query.removeEventListener('change', handler);
  }, []);

  return reduced;
}
