import { useEffect, useRef } from 'react';
import { usePrefersReducedMotion } from './usePrefersReducedMotion';

/**
 * Devuelve un ref para aplicar a un contenedor: agrega la clase `is-visible`
 * cuando entra en viewport (animación sutil de fade/slide vía CSS).
 * Si el usuario prefiere menos movimiento, se marca visible de entrada y no observa.
 */
export function useRevealOnScroll<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (reducedMotion) {
      el.classList.add('is-visible');
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [reducedMotion]);

  return ref;
}
