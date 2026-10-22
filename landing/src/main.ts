import './index.css';
import { runCounters, runReveal } from './runtime/effects.ts';
import { setupDownloads } from './runtime/downloads.ts';
import { setupLangSwitcher } from './runtime/lang.ts';
import { setupMenu } from './runtime/menu.ts';
import { detectPlatform } from './runtime/platform.ts';
import { setupShare } from './runtime/share.ts';
import type { RuntimeStrings } from './runtime/types.ts';

/**
 * La landing llega prerenderizada (build/prerender.ts) en el idioma de la ruta:
 * acá solo se mejora lo que depende del navegador. No hay framework en runtime.
 */
function init(): void {
  const root = document.getElementById('root');
  const raw = document.getElementById('ng-rt')?.textContent;
  if (!root || !raw) return;
  const rt = JSON.parse(raw) as RuntimeStrings;
  const platform = detectPlatform(navigator);

  setupMenu(root);
  setupLangSwitcher(root);
  setupDownloads(root, platform, rt);
  setupShare(root, platform, rt);
  runCounters(root);
  runReveal(root);
}

init();
