import { Section } from './Section';
import { FEATURES } from '../data/content';
import styles from './Features.module.css';

/** Features (sección 5): grid de 6 con ícono, copy verificado contra src/. */
export function Features() {
  return (
    <Section id="funciones" ariaLabel="Funciones de trafficMe">
      <div className="container">
        <h2 className={styles.heading}>Todo lo que necesitás para entender tu red</h2>
        <ul className={styles.grid}>
          {FEATURES.map((feature) => (
            <li key={feature.title} className={styles.card}>
              <span className={styles.icon} aria-hidden="true">
                {feature.icon}
              </span>
              <h3 className={styles.title}>{feature.title}</h3>
              <p className={styles.description}>{feature.description}</p>
            </li>
          ))}
        </ul>
      </div>
    </Section>
  );
}
