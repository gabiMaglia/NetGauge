import styles from './ScreenshotPlaceholder.module.css';

interface ScreenshotPlaceholderProps {
  /** Texto alternativo descriptivo: usado tal cual como `alt` (accesibilidad). */
  alt: string;
  tabs?: string[];
  className?: string;
}

/**
 * Placeholder visual de la ventana de la app (no existen screenshots reales todavía,
 * ver handoff T-015). Simula la ventana dark con pestañas "Global / Por aplicación / Conexiones".
 */
export function ScreenshotPlaceholder({ alt, tabs, className }: ScreenshotPlaceholderProps) {
  return (
    <figure className={`${styles.frame} ${className ?? ''}`} role="img" aria-label={alt}>
      <div className={styles.titlebar} aria-hidden="true">
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.dot} />
      </div>
      {tabs && (
        <div className={styles.tabs} aria-hidden="true">
          {tabs.map((tab, index) => (
            <span key={tab} className={`${styles.tab} ${index === 0 ? styles.tabActive : ''}`}>
              {tab}
            </span>
          ))}
        </div>
      )}
      <div className={styles.body} aria-hidden="true">
        <div className={styles.barGroup}>
          {Array.from({ length: 8 }, (_, i) => (
            <span key={i} className={styles.bar} style={{ height: `${20 + ((i * 11) % 60)}%` }} />
          ))}
        </div>
        <p className={styles.caption}>Placeholder visual — captura real pendiente</p>
      </div>
    </figure>
  );
}
