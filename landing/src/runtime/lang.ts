import { LANGS, LANG_STORAGE_KEY, type Lang } from '../lang.ts';

/**
 * Los links del switcher son <a href="/en/"> reales (rastreables, funcionan sin JS).
 * El JS solo recuerda la preferencia y conserva el #ancla al cambiar de idioma.
 */
export function setupLangSwitcher(root: HTMLElement): void {
  root.querySelectorAll<HTMLAnchorElement>('[data-lang-link]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const lang = a.getAttribute('data-lang-link') as Lang;
      if (!LANGS.includes(lang)) return;
      try {
        localStorage.setItem(LANG_STORAGE_KEY, lang);
      } catch {
        /* modo privado: se navega igual */
      }
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
      e.preventDefault();
      location.assign(a.getAttribute('href')! + location.hash);
    });
  });
}
