import { Section } from './Section';
import { TRUST_BADGES } from '../data/content';
import styles from './TrustBar.module.css';

/** Barra de confianza (sección 3): badges de licencia, plataformas y privacidad. */
export function TrustBar() {
  return (
    <Section ariaLabel="Indicadores de confianza" className={styles.wrapper}>
      <div className="container">
        <ul className={styles.list}>
          {TRUST_BADGES.map((badge) => (
            <li key={badge} className={styles.badge}>
              {badge}
            </li>
          ))}
        </ul>
      </div>
    </Section>
  );
}
