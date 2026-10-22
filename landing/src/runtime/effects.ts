const reduceMotion = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

/** Anima los números `data-count` de 0 al objetivo (ease-out cúbico, 1.4s). */
export function runCounters(root: HTMLElement): void {
  const reduce = reduceMotion();
  root.querySelectorAll<HTMLElement>('[data-count]').forEach((el) => {
    const target = parseFloat(el.getAttribute('data-count') || '0') || 0;
    const dec = parseInt(el.getAttribute('data-dec') || '0', 10);
    if (reduce) return; // el HTML ya trae el valor final
    const start = performance.now();
    const step = (now: number) => {
      const p = Math.min(1, (now - start) / 1400);
      el.textContent = (target * (1 - Math.pow(1 - p, 3))).toFixed(dec);
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target.toFixed(dec);
    };
    requestAnimationFrame(step);
  });
}

/** Entrada `tmRise` con delay por elemento. El contenido es visible por defecto. */
export function runReveal(root: HTMLElement): void {
  if (reduceMotion()) return;
  root.querySelectorAll<HTMLElement>('[data-reveal]').forEach((el) => {
    const d = parseInt(el.getAttribute('data-reveal-delay') || '0', 10);
    el.style.animation = `tmRise .6s cubic-bezier(.2,.7,.2,1) ${d}ms both`;
    const onEnd = (e: AnimationEvent) => {
      if (e.target !== el || e.animationName !== 'tmRise') return;
      el.removeEventListener('animationend', onEnd);
      el.style.animation = '';
    };
    el.addEventListener('animationend', onEnd);
  });
}
