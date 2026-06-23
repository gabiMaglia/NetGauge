import { useId, useState } from 'react';
import { Section } from './Section';
import { DownloadButtons } from './DownloadButtons';
import { GITHUB_URL, RELEASES_LATEST_URL } from '../data/constants';
import styles from './Download.module.css';

/**
 * Descarga (sección 10, ancla #descargar): 3 botones explícitos + link a Releases
 * + acordeón honesto sobre el instalador sin firmar (regla de contenido VERDAD).
 */
export function Download() {
  const [unsignedOpen, setUnsignedOpen] = useState(false);
  const panelId = useId();

  return (
    <Section id="descargar" ariaLabel="Descargar NetLeak">
      <div className="container">
        <h2 className={styles.heading}>Descargá NetLeak</h2>
        <p className={styles.subheading}>
          Elegí tu sistema. El navegador detecta el tuyo y lo resalta, pero los tres
          siempre están disponibles.
        </p>

        <DownloadButtons />

        <p className={styles.allVersions}>
          <a href={RELEASES_LATEST_URL} target="_blank" rel="noopener noreferrer">
            Todas las versiones en GitHub Releases
          </a>
        </p>

        <div className={styles.notice}>
          <button
            type="button"
            className={styles.noticeTrigger}
            aria-expanded={unsignedOpen}
            aria-controls={panelId}
            onClick={() => setUnsignedOpen((open) => !open)}
          >
            <span>¿Por qué Windows o Mac muestran una advertencia al instalar?</span>
            <span aria-hidden="true">{unsignedOpen ? '−' : '+'}</span>
          </button>
          <div id={panelId} hidden={!unsignedOpen} className={styles.noticePanel}>
            <p>
              El instalador todavía no está firmado digitalmente, así que Windows o
              macOS pueden mostrar un aviso. Es por la falta de firma, no por riesgo:
              el código es abierto y lo podés revisar en{' '}
              <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
                GitHub
              </a>
              .
            </p>
            <p>
              <strong>Windows:</strong> hacé clic en &quot;Más información&quot; y luego
              en &quot;Ejecutar de todas formas&quot;.
            </p>
            <p>
              <strong>Mac:</strong> hacé clic derecho sobre la app y elegí
              &quot;Abrir&quot;.
            </p>
          </div>
        </div>
      </div>
    </Section>
  );
}
