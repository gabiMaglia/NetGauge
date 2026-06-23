import { Section } from './Section';
import { Accordion } from './Accordion';
import { FAQ_ITEMS } from '../data/content';
import styles from './Faq.module.css';

/** FAQ (sección 11): acordeón accesible. */
export function Faq() {
  return (
    <Section id="faq" ariaLabel="Preguntas frecuentes" className={styles.section}>
      <div className="container">
        <h2 className={styles.heading}>Preguntas frecuentes</h2>
        <div className={styles.wrapper}>
          <Accordion items={FAQ_ITEMS} />
        </div>
      </div>
    </Section>
  );
}
