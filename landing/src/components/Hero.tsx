import { GITHUB_URL } from '../data/constants';
import { DownloadButtons } from './DownloadButtons';
import { ScreenshotPlaceholder } from './ScreenshotPlaceholder';
import { Sparkline } from './Sparkline';
import styles from './Hero.module.css';

/** HERO (sección 2): copy exacto del brief, CTA primario/secundario y screenshot placeholder. */
export function Hero() {
  return (
    <section id="top" className={styles.hero} aria-label="Presentación de NetLeak">
      <div className={`container ${styles.grid}`}>
        <div className={styles.copy}>
          <Sparkline className={styles.sparkline} width={280} height={64} />
          <h1 className={styles.title}>Sabé qué app se está comiendo tu internet.</h1>
          <p className={styles.subtitle}>
            Monitor de consumo de red por aplicación, en tiempo real. Gratis, de código
            abierto y privado: tus datos nunca salen de tu equipo. Windows y Mac.
          </p>

          <div className={styles.ctaRow}>
            <a href="#descargar" className={styles.primaryCta}>
              Descargar gratis
            </a>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.secondaryCta}
            >
              Ver en GitHub
            </a>
          </div>

          <p className={styles.microline}>
            Gratis · Open source (MIT) · Sin telemetría · Windows + macOS
          </p>

          <div className={styles.heroDownloads}>
            <DownloadButtons variant="compact" />
          </div>
        </div>

        <ScreenshotPlaceholder
          className={styles.screenshot}
          alt="Ventana principal de NetLeak en modo oscuro, mostrando el consumo de red por aplicación"
          tabs={['Global', 'Por aplicación', 'Conexiones']}
        />
      </div>
    </section>
  );
}
