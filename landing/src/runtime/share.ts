import { isMobile, type Platform } from './platform.ts';
import type { RuntimeStrings } from './types.ts';

let toastTimer: number | undefined;

function toast(root: ParentNode, msg: string): void {
  const el = root.querySelector<HTMLElement>('[data-toast]');
  if (!el) return;
  el.textContent = msg;
  el.setAttribute('data-show', '');
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => el.removeAttribute('data-show'), 3500);
}

/**
 * En celulares y tablets (no hay build para ellos) el CTA principal pasa a
 * "Enviame el link": Web Share → portapapeles con aviso → mailto (el href base).
 */
export function setupShare(root: HTMLElement, platform: Platform, rt: RuntimeStrings): void {
  if (!isMobile(platform)) return;

  const canonical = document.querySelector<HTMLLinkElement>('link[rel="canonical"]')?.href ?? location.origin + '/';
  const url = `${canonical}#descargar`;
  const mailto = `mailto:?subject=${encodeURIComponent(rt.share.subject)}&body=${encodeURIComponent(`${rt.share.text}\n${url}`)}`;

  root.querySelectorAll<HTMLElement>('[data-os-label]').forEach((el) => (el.textContent = rt.share.cta));
  root.querySelectorAll<HTMLElement>('[data-os-sub]').forEach((el) => (el.textContent = rt.share.sub));
  root.querySelectorAll<HTMLElement>('[data-mobile-note]').forEach((el) => (el.hidden = false));

  root.querySelectorAll<HTMLAnchorElement>('[data-os-primary]').forEach((a) => {
    a.setAttribute('href', mailto);
    a.removeAttribute('target');
    a.addEventListener('click', async (e) => {
      e.preventDefault();
      if (navigator.share) {
        try {
          await navigator.share({ title: rt.share.subject, text: rt.share.text, url });
          return;
        } catch (err) {
          if ((err as DOMException).name === 'AbortError') return; // el usuario canceló
        }
      }
      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(url);
          toast(root, rt.share.copied);
          return;
        } catch {
          /* sin permiso de portapapeles: cae al mailto */
        }
      }
      location.href = mailto;
    });
  });
}
