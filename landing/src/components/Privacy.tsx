import { Section } from './Section';
import styles from './Privacy.module.css';

/**
 * Privacidad (sección 7, destacada). Copy fiel a las reglas de contenido VERDAD:
 * historial local, VT/GeoIP opt-in y apagados, solo hash o IP — nunca archivos.
 */
export function Privacy() {
  return (
    <Section id="privacidad" ariaLabel="Privacidad" className={styles.section}>
      <div className={`container ${styles.inner}`}>
        <h2 className={styles.heading}>Tus datos son tuyos. En serio.</h2>
        <ul className={styles.list}>
          <li>Tu historial de consumo se guarda localmente, en tu equipo.</li>
          <li>Nada se manda a ningún servidor por defecto.</li>
          <li>
            Las únicas funciones que usan internet —reputación de VirusTotal y
            geolocalización de IPs— son opcionales y vienen <strong>apagadas</strong> de
            fábrica.
          </li>
          <li>
            Cuando las activás, solo envían un hash o una dirección IP. Nunca tus
            archivos.
          </li>
        </ul>
      </div>
    </Section>
  );
}
