import type { ReactNode } from 'react';
import { useRevealOnScroll } from '../hooks/useRevealOnScroll';
import styles from './Section.module.css';

interface SectionProps {
  id?: string;
  className?: string;
  ariaLabel?: string;
  children: ReactNode;
}

/** Wrapper de sección con animación sutil de aparición al hacer scroll (respeta reduced-motion). */
export function Section({ id, className, ariaLabel, children }: SectionProps) {
  const ref = useRevealOnScroll<HTMLElement>();

  return (
    <section
      id={id}
      ref={ref}
      aria-label={ariaLabel}
      className={`${styles.section} ${className ?? ''}`}
    >
      {children}
    </section>
  );
}
