/**
 * Dominio público de la landing. Es la ÚNICA fuente: canonical, og:url,
 * og:image, hreflang y sitemap se derivan de acá. Para otro dominio:
 * `VITE_SITE_URL=https://mi-dominio.com npm run build` (ver README).
 */
export const DEFAULT_SITE_URL = 'https://netgauge.app';

export function resolveSiteUrl(env: Record<string, string | undefined>): string {
  const raw = (env.VITE_SITE_URL || DEFAULT_SITE_URL).trim();
  return raw.replace(/\/+$/, '');
}
