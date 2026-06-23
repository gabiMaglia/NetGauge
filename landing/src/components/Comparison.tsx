import { Section } from './Section';
import { COMPARISON_ROWS } from '../data/content';
import styles from './Comparison.module.css';

/** Comparativa (sección 9): tabla simple, sin nombrar competidores. */
export function Comparison() {
  return (
    <Section ariaLabel="Comparativa" className={styles.section}>
      <div className="container">
        <h2 className={styles.heading}>trafficMe en números simples</h2>
        <table className={styles.table}>
          <caption className="visually-hidden">
            Características principales de trafficMe
          </caption>
          <tbody>
            {COMPARISON_ROWS.map((row) => (
              <tr key={row.label}>
                <th scope="row" className={styles.label}>
                  {row.label}
                </th>
                <td className={styles.value}>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}
