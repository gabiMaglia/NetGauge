import { Section } from './Section';
import styles from './Problem.module.css';

/** Problema (sección 4): copy exacto del brief. */
export function Problem() {
  return (
    <Section ariaLabel="El problema que resuelve NetLeak">
      <div className={`container ${styles.inner}`}>
        <p className={styles.text}>
          El medidor de tu sistema te da un total, no el culpable. NetLeak te muestra
          el ranking de apps que consumen — ahora y en tu historial.
        </p>
      </div>
    </Section>
  );
}
