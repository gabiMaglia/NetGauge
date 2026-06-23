import { GITHUB_URL } from '../data/constants';
import styles from './Header.module.css';

const NAV_LINKS = [
  { href: '#funciones', label: 'Funciones' },
  { href: '#como-funciona', label: 'Cómo funciona' },
  { href: '#privacidad', label: 'Privacidad' },
  { href: '#faq', label: 'FAQ' },
];

/** Header sticky: logo + nav + CTA primario (sección 1 del brief). */
export function Header() {
  return (
    <header className={styles.header}>
      <div className={`container ${styles.inner}`}>
        <a href="#top" className={styles.logo} aria-label="trafficMe — ir al inicio">
          <img src="/favicon.svg" alt="" width={28} height={28} aria-hidden="true" />
          <span>trafficMe</span>
        </a>

        <nav className={styles.nav} aria-label="Navegación principal">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href} className={styles.navLink}>
              {link.label}
            </a>
          ))}
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.navLink}
          >
            GitHub
          </a>
        </nav>

        <a href="#descargar" className={styles.cta}>
          Descargar gratis
        </a>
      </div>
    </header>
  );
}
