import { isMobile, readGlRenderer, suggestMacChip, type Platform } from './platform.ts';
import { fetchReleaseLinks } from './releases.ts';
import type { RuntimeStrings } from './types.ts';

const $$ = <T extends HTMLElement>(root: ParentNode, sel: string) =>
  Array.from(root.querySelectorAll<T>(sel));

function setLabel(root: ParentNode, label: string, sub: string): void {
  $$(root, '[data-os-label]').forEach((el) => (el.textContent = label));
  $$(root, '[data-os-sub]').forEach((el) => (el.textContent = sub));
}

/** CTA principal según SO (escritorio). En móvil lo toma `share.ts`. */
export function setupDownloads(root: HTMLElement, platform: Platform, rt: RuntimeStrings): void {
  const primaries = $$<HTMLAnchorElement>(root, '[data-os-primary]');

  if (platform === 'windows') {
    setLabel(root, rt.os.windows.label, rt.os.windows.sub);
    // El CTA principal ya es Windows: se oculta el botón secundario duplicado.
    $$(root, '[data-hide-win]').forEach((el) => (el.hidden = true));
  } else if (platform === 'mac') {
    setLabel(root, rt.os.mac.label, rt.os.mac.sub);
    // No se adivina el chip: el CTA lleva a los botones Intel / Apple Silicon.
    primaries.forEach((a) => {
      a.setAttribute('href', '#descargar-botones');
      a.removeAttribute('target');
    });
    const chip = suggestMacChip(readGlRenderer());
    if (chip) {
      const btn = root.querySelector<HTMLElement>(`[data-dl="${chip}"]`);
      btn?.setAttribute('data-suggested', '');
      btn?.setAttribute('data-suggest-label', `· ${rt.suggested}`);
    }
  }

  if (isMobile(platform)) return; // el aviso de "elegí en tu PC" no necesita enlaces directos

  void fetchReleaseLinks().then((links) => {
    if (!links) return;
    (['win', 'mac-arm', 'mac-intel'] as const).forEach((k) => {
      const href = links[k];
      if (href) $$<HTMLAnchorElement>(root, `[data-dl="${k}"]`).forEach((a) => a.setAttribute('href', href));
    });
    if (platform === 'windows' && links.win) primaries.forEach((a) => a.setAttribute('href', links.win!));
    if (links.win && links['mac-arm'] && links['mac-intel'])
      $$(root, '[data-dl-hint]').forEach((el) => (el.hidden = true));
  });
}
