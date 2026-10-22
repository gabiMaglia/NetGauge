/** Idiomas y rutas de la landing. Módulo mínimo: lo usan el runtime y el build. */

export type Lang = 'es' | 'en' | 'pt';

export const LANGS: Lang[] = ['es', 'en', 'pt'];
export const DEFAULT_LANG: Lang = 'es';
export const LANG_STORAGE_KEY = 'netgauge-lang';

/** Ruta pública de cada idioma (ES es la raíz y el x-default). */
export const LANG_PATH: Record<Lang, string> = { es: '/', en: '/en/', pt: '/pt/' };
/** Locale de Open Graph por idioma. */
export const OG_LOCALE: Record<Lang, string> = { es: 'es_LA', en: 'en_US', pt: 'pt_BR' };
