import { useEffect, useRef } from 'react';
import landingHtml from './landing.html?raw';

/**
 * Landing NetLeak — render pixel-perfect del diseño hi-fi
 * `design_handoff_netLeak_panel/NetLeak Landing.dc.html` (T-018).
 *
 * El markup se inyecta verbatim (extraído byte a byte del diseño) y este
 * componente porta el comportamiento del runtime original: detección de SO,
 * contadores, reveal al entrar y hover (atributo `style-hover`).
 */

/** ¿Mac con Apple Silicon? Heurística por renderer de WebGL (igual que el diseño). */
function isAppleSilicon(): boolean {
  try {
    const c = document.createElement('canvas');
    const gl = (c.getContext('webgl') ||
      c.getContext('experimental-webgl')) as WebGLRenderingContext | null;
    if (!gl) return true;
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    const r = ext ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) || '') : '';
    if (/Intel/i.test(r)) return false;
    return true;
  } catch {
    return true;
  }
}

/** Ajusta el botón de descarga al SO detectado (sin ocultar los explícitos). */
function detectOS(root: HTMLElement): void {
  let os = 'other';
  try {
    const ua = navigator.userAgent || '';
    const plat = (navigator.platform || '') + ' ' + ua;
    if (/Win/i.test(plat)) os = 'windows';
    else if (/Mac/i.test(plat) && !/iPhone|iPad/i.test(ua))
      os = isAppleSilicon() ? 'mac-arm' : 'mac-intel';
    else if (/Linux|X11/i.test(plat)) os = 'linux';
  } catch {
    /* noop */
  }
  const map: Record<string, { label: string; sub: string }> = {
    windows: { label: 'Descargar para Windows', sub: 'Windows 10/11 · 64-bit' },
    'mac-arm': { label: 'Descargar para macOS', sub: 'Apple Silicon · M1–M4' },
    'mac-intel': { label: 'Descargar para macOS', sub: 'Mac con Intel' },
    linux: { label: 'Descargar gratis', sub: 'Windows y macOS' },
    other: { label: 'Descargar gratis', sub: 'Windows y macOS' },
  };
  const m = map[os] || map.other;
  root.querySelectorAll<HTMLElement>('[data-os-label]').forEach((el) => {
    el.textContent = m.label;
  });
  root.querySelectorAll<HTMLElement>('[data-os-sub]').forEach((el) => {
    el.textContent = m.sub;
  });
}

/** Anima los números `data-count` de 0 al objetivo (ease-out cúbico, 1.4s). */
function runCounters(root: HTMLElement): void {
  root.querySelectorAll<HTMLElement>('[data-count]').forEach((el) => {
    const target = parseFloat(el.getAttribute('data-count') || '0') || 0;
    const dec = parseInt(el.getAttribute('data-dec') || '0', 10);
    const dur = 1400;
    const start = performance.now();
    const step = (now: number) => {
      const p = Math.min(1, (now - start) / dur);
      const e = 1 - Math.pow(1 - p, 3);
      el.textContent = (target * e).toFixed(dec);
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target.toFixed(dec);
    };
    requestAnimationFrame(step);
  });
}

/** Entrada `tmRise` con delay por elemento. El contenido es visible por defecto. */
function runReveal(root: HTMLElement): void {
  const reduce =
    window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) return;
  root.querySelectorAll<HTMLElement>('[data-reveal]').forEach((el) => {
    const marked = el as HTMLElement & { __rev?: boolean };
    if (marked.__rev) return;
    marked.__rev = true;
    const d = parseInt(el.getAttribute('data-reveal-delay') || '0', 10);
    el.style.animation = `tmRise .6s cubic-bezier(.2,.7,.2,1) ${d}ms both`;
    const onEnd = (e: AnimationEvent) => {
      if (e.target !== el || e.animationName !== 'tmRise') return;
      el.removeEventListener('animationend', onEnd);
      el.style.animation = '';
      el.style.transform = '';
    };
    el.addEventListener('animationend', onEnd);
  });
}

/** Hover declarativo del diseño: el atributo `style-hover` se suma al `style` base. */
function bindHovers(root: HTMLElement): void {
  root.querySelectorAll<HTMLElement>('[style-hover]').forEach((el) => {
    const hover = el.getAttribute('style-hover');
    if (!hover) return;
    const base = el.getAttribute('style') || '';
    el.addEventListener('mouseenter', () => el.setAttribute('style', `${base};${hover}`));
    el.addEventListener('mouseleave', () => el.setAttribute('style', base));
  });
}

export default function App() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const init = root as HTMLElement & { __init?: boolean };
    if (init.__init) return; // evita doble binding bajo StrictMode (dev)
    init.__init = true;
    detectOS(root);
    runCounters(root);
    runReveal(root);
    bindHovers(root);
  }, []);

  return <div ref={ref} dangerouslySetInnerHTML={{ __html: landingHtml }} />;
}
