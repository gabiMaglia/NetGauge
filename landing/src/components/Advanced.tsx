import { Section } from './Section';
import { ADVANCED_POINTS } from '../data/content';
import styles from './Advanced.module.css';

/**
 * Avanzado/seguridad (sección 8). El "Índice de confianza" se marca explícitamente
 * como Windows-only (Authenticode) — regla de contenido VERDAD, no presentarlo
 * como multiplataforma.
 */
export function Advanced() {
  return (
    <Section ariaLabel="Funciones avanzadas y de seguridad">
      <div className="container">
        <h2 className={styles.heading}>Para quien quiere ver más</h2>
        <ul className={styles.grid}>
          {ADVANCED_POINTS.map((point) => (
            <li key={point.title} className={styles.card}>
              <h3 className={styles.title}>
                {point.title}
                {point.title.includes('Windows') && (
                  <span className={styles.tag}>Solo Windows</span>
                )}
              </h3>
              <p className={styles.description}>{point.description}</p>
            </li>
          ))}
        </ul>
      </div>
    </Section>
  );
}
