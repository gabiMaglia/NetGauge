/**
 * Dominio público de la landing. Es la ÚNICA fuente: canonical, og:url,
 * og:image, hreflang y sitemap se derivan de acá. Para otro dominio:
 * `VITE_SITE_URL=https://mi-dominio.com npm run build` (ver README).
 */
export const DEFAULT_SITE_URL = 'https://www.gabrielmaglia.me/apps/netgauge';

export function resolveSiteUrl(env: Record<string, string | undefined>): string {
  const raw = (env.VITE_SITE_URL || DEFAULT_SITE_URL).trim();
  return raw.replace(/\/+$/, '');
}

/**
 * Subruta donde vive la landing (el portfolio la proxea en /apps/netgauge/).
 * Vite `base` y los links internos salen de acá; los archivos siguen en la raíz del deploy.
 */
export const BASE_PATH = '/apps/netgauge/';

/**
 * Host viejo del deploy. El portfolio lo proxea (rewrite) y Vercel le manda
 * `Host: net-gauge-brown.vercel.app`, así que un redirect de servidor por host
 * (vercel.json `has: host`) devolvería 308 al propio proxy y lo rompería.
 * Por eso la redirección es client-side (ver `legacyHostRedirect`): en el
 * navegador, vía proxy, `location.hostname` ya es www.gabrielmaglia.me.
 */
export const LEGACY_HOST = 'net-gauge-brown.vercel.app';
