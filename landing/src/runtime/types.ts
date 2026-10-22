import type { Lang } from '../lang.ts';

/** Cadenas por idioma que el prerender embebe en `#ng-rt`. */
export interface RuntimeStrings {
  lang: Lang;
  os: Record<'windows' | 'mac' | 'other', { label: string; sub: string }>;
  suggested: string;
  share: { cta: string; sub: string; copied: string; subject: string; text: string };
}
