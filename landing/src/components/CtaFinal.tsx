import { GITHUB_URL } from '../data/constants';
import { Section } from './Section';
import styles from './CtaFinal.module.css';

/** CTA final (sección 12). */
export function CtaFinal() {
  return (
    <Section ariaLabel="Llamado a la acción final" className={styles.section}>
      <div className={`container ${styles.inner}`}>
        <h2 className={styles.heading}>Tomá el control de tu red — gratis.</h2>
        <div className={styles.ctaRow}>
          <a href="#descargar" className={styles.primaryCta}>
            Descargar
          </a>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.secondaryCta}
          >
            Ver en GitHub
          </a>
        </div>
      </div>
    </Section>
  );
}
