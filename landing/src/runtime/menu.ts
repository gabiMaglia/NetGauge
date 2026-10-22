/** Menú hamburguesa (<880px): aria-expanded, Esc, cierre al elegir ancla y foco gestionado. */
export function setupMenu(root: HTMLElement): void {
  const btn = root.querySelector<HTMLButtonElement>('[data-menu-btn]');
  const panel = root.querySelector<HTMLElement>('[data-mobile-nav]');
  const header = root.querySelector<HTMLElement>('.ng-header');
  if (!btn || !panel || !header) return;

  const isOpen = () => btn.getAttribute('aria-expanded') === 'true';
  const set = (open: boolean) => {
    btn.setAttribute('aria-expanded', String(open));
    panel.hidden = !open;
  };
  const close = (returnFocus: boolean) => {
    if (!isOpen()) return;
    set(false);
    if (returnFocus) btn.focus();
  };

  btn.addEventListener('click', () => {
    if (isOpen()) return close(true);
    set(true);
    panel.querySelector<HTMLElement>('a')?.focus();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close(true);
  });
  // Elegir un enlace cierra el menú; el ancla se encarga de mover el foco/scroll.
  panel.addEventListener('click', (e) => {
    if ((e.target as HTMLElement).closest('a')) close(false);
  });
  // Tab hacia afuera del header o click fuera: se cierra sin robar el foco.
  header.addEventListener('focusout', (e) => {
    const next = e.relatedTarget as Node | null;
    if (next && !header.contains(next)) close(false);
  });
  document.addEventListener('click', (e) => {
    if (!header.contains(e.target as Node)) close(false);
  });
  window.matchMedia('(min-width: 881px)').addEventListener('change', (e) => {
    if (e.matches) close(false);
  });
}
