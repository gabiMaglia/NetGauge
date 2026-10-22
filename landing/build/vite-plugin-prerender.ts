import fs from 'node:fs';
import path from 'node:path';
import type { Plugin } from 'vite';
import { DEFAULT_LANG, LANGS, LANG_PATH, type Lang } from '../src/lang.ts';
import {
  PREF_REDIRECT,
  langFromPath,
  renderBody,
  renderHead,
  renderRobots,
  renderSitemap,
} from './prerender.ts';

const HEAD = ['<!--ng:head-->', '<!--/ng:head-->'] as const;
const BODY = ['<!--ng:body-->', '<!--/ng:body-->'] as const;

/**
 * Prerender estático por idioma (/, /en/, /pt/) como plugin de Vite:
 * - `transformIndexHtml` inyecta head+markup del idioma (también en `vite dev`).
 * - `writeBundle` clona el index.html ya procesado (assets con hash) a /en/ y
 *   /pt/ reemplazando solo los bloques marcados, y emite sitemap.xml y robots.txt.
 */
export function prerender(opts: { siteUrl: string }): Plugin {
  let root = process.cwd();
  const landing = () => fs.readFileSync(path.join(root, 'src/landing.html'), 'utf8');
  const block = (marks: readonly [string, string], inner: string) => `${marks[0]}${inner}${marks[1]}`;
  const replaceBlock = (html: string, marks: readonly [string, string], inner: string) => {
    const a = html.indexOf(marks[0]);
    const b = html.indexOf(marks[1]);
    if (a < 0 || b < 0) throw new Error(`prerender: faltan los marcadores ${marks[0]} en index.html`);
    return html.slice(0, a) + block(marks, inner) + html.slice(b + marks[1].length);
  };
  const setLang = (html: string, lang: Lang) => html.replace(/<html lang="[a-z-]+"/, `<html lang="${lang}"`);

  return {
    name: 'ng-prerender',
    configResolved(c) {
      root = c.root;
    },
    transformIndexHtml: {
      order: 'pre',
      handler(html, ctx) {
        const lang = langFromPath(ctx.originalUrl ?? ctx.path ?? '/');
        let out = html
          .replace('<!--ng:pref-redirect-->', () => `<script>${PREF_REDIRECT}</script>`)
          .replace(HEAD[0] + HEAD[1], () => block(HEAD, renderHead(lang, opts.siteUrl)))
          .replace(BODY[0] + BODY[1], () => block(BODY, renderBody(landing(), lang)));
        out = setLang(out, lang);
        return out;
      },
    },
    writeBundle(options) {
      const dist = options.dir ?? path.join(root, 'dist');
      const base = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
      for (const lang of LANGS) {
        if (lang === DEFAULT_LANG) continue;
        let html = replaceBlock(base, HEAD, renderHead(lang, opts.siteUrl));
        html = replaceBlock(html, BODY, renderBody(landing(), lang));
        html = setLang(html, lang);
        const dir = path.join(dist, LANG_PATH[lang]);
        fs.mkdirSync(dir, { recursive: true });
        fs.writeFileSync(path.join(dir, 'index.html'), html);
      }
      fs.writeFileSync(
        path.join(dist, 'sitemap.xml'),
        renderSitemap(opts.siteUrl, new Date().toISOString().slice(0, 10)),
      );
      fs.writeFileSync(path.join(dist, 'robots.txt'), renderRobots(opts.siteUrl));
    },
  };
}
