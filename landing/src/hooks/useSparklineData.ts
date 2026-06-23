import { useEffect, useState } from 'react';
import { usePrefersReducedMotion } from './usePrefersReducedMotion';

const POINTS = 24;

function randomWalk(prev: number[]): number[] {
  const last = prev[prev.length - 1] ?? 50;
  const next = Math.max(10, Math.min(95, last + (Math.random() - 0.5) * 22));
  return [...prev.slice(1), next];
}

/**
 * Serie decorativa que simula actividad de ancho de banda para el motivo
 * visual "sparkline" del hero. Es puramente estético (sin datos reales:
 * la landing no consume la app). Se congela si `prefers-reduced-motion`.
 */
export function useSparklineData(): number[] {
  const reducedMotion = usePrefersReducedMotion();
  const [data, setData] = useState<number[]>(() =>
    Array.from({ length: POINTS }, (_, i) => 40 + Math.sin(i / 2) * 20 + 20),
  );

  useEffect(() => {
    if (reducedMotion) return;
    const interval = setInterval(() => {
      setData((prev) => randomWalk(prev));
    }, 1400);
    return () => clearInterval(interval);
  }, [reducedMotion]);

  return data;
}
