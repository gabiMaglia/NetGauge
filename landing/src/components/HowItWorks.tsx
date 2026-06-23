import { Section } from './Section';
import { STEPS } from '../data/content';
import styles from './HowItWorks.module.css';

/** Cómo funciona (sección 6): 3 pasos. */
export function HowItWorks() {
  return (
    <Section id="como-funciona" ariaLabel="Cómo funciona trafficMe" className={styles.section}>
      <div className="container">
        <h2 className={styles.heading}>Cómo funciona</h2>
        <ol className={styles.steps}>
          {STEPS.map((step) => (
            <li key={step.number} className={styles.step}>
              <span className={styles.number} aria-hidden="true">
                {step.number}
              </span>
              <h3 className={styles.title}>{step.title}</h3>
              <p className={styles.description}>{step.description}</p>
            </li>
          ))}
        </ol>
      </div>
    </Section>
  );
}
