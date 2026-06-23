import { DOWNLOAD_OPTIONS, RELEASES_LATEST_URL } from '../data/constants';
import { useDetectedOS } from '../hooks/useDetectedOS';
import styles from './DownloadButtons.module.css';

interface DownloadButtonsProps {
  /** Variante compacta para el hero / CTA final (un solo botón resaltado + link a los demás). */
  variant?: 'full' | 'compact';
}

/**
 * Los 3 botones de descarga SIEMPRE están visibles (criterio de aceptación #4).
 * El auto-SO solo agrega la clase `is-detected` para resaltar, nunca oculta opciones.
 * Todos apuntan a releases/latest (no hay URLs de assets confirmadas).
 */
export function DownloadButtons({ variant = 'full' }: DownloadButtonsProps) {
  const detected = useDetectedOS();

  return (
    <div
      className={variant === 'compact' ? styles.compactGroup : styles.group}
      role="group"
      aria-label="Descargar NetLeak"
    >
      {DOWNLOAD_OPTIONS.map((option) => {
        const isDetected = option.id === detected;
        return (
          <a
            key={option.id}
            href={RELEASES_LATEST_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={`${styles.button} ${isDetected ? styles.detected : ''}`}
            aria-current={isDetected ? 'true' : undefined}
          >
            <span className={styles.label}>{option.label}</span>
            <span className={styles.sublabel}>{option.sublabel}</span>
            {isDetected && <span className={styles.badge}>Tu sistema</span>}
          </a>
        );
      })}
    </div>
  );
}
