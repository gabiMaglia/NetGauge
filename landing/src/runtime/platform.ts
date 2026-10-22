export type Platform = 'ios' | 'android' | 'windows' | 'mac' | 'other';

interface NavLike {
  userAgent?: string;
  platform?: string;
  maxTouchPoints?: number;
}

/** Heurística de SO. Solo decide qué CTA mostrar; los botones explícitos siempre están. */
export function detectPlatform(nav: NavLike): Platform {
  const ua = nav.userAgent ?? '';
  const plat = nav.platform ?? '';
  if (/Android/i.test(ua)) return 'android';
  if (/iPhone|iPad|iPod/i.test(ua)) return 'ios';
  // iPadOS 13+ se presenta como Macintosh; la pantalla táctil lo delata.
  if (/Mac/i.test(plat + ua) && (nav.maxTouchPoints ?? 0) > 1) return 'ios';
  if (/Win/i.test(plat + ua)) return 'windows';
  if (/Mac/i.test(plat + ua)) return 'mac';
  return 'other';
}

export const isMobile = (p: Platform): boolean => p === 'ios' || p === 'android';

/** Chip sugerido solo si el renderer WebGL lo dice explícitamente; si no, null (no se adivina). */
export function suggestMacChip(renderer: string): 'mac-arm' | 'mac-intel' | null {
  if (/Apple M\d/i.test(renderer)) return 'mac-arm';
  if (/Intel|AMD|Radeon/i.test(renderer)) return 'mac-intel';
  return null;
}

export function readGlRenderer(): string {
  try {
    const gl = document.createElement('canvas').getContext('webgl');
    const ext = gl?.getExtension('WEBGL_debug_renderer_info');
    return gl && ext ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) || '') : '';
  } catch {
    return '';
  }
}
