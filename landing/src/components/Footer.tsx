import { GITHUB_URL, KOFI_URL, LICENSE_URL, RELEASES_LATEST_URL } from '../data/constants';
import styles from './Footer.module.css';

/** Footer (sección 13): links + crédito a Qt/PySide6. */
export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.inner}`}>
        <nav className={styles.links} aria-label="Enlaces del pie de página">
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
          <a href={RELEASES_LATEST_URL} target="_blank" rel="noopener noreferrer">
            Releases
          </a>
          <a href={LICENSE_URL} target="_blank" rel="noopener noreferrer">
            Licencia MIT
          </a>
          <a href="#privacidad">Privacidad</a>
          <a href={KOFI_URL} target="_blank" rel="noopener noreferrer">
            ☕ Invitar un café
          </a>
        </nav>
        <p className={styles.credit}>Hecho con software libre (Qt/PySide6).</p>
      </div>
    </footer>
  );
}
