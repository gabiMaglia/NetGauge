import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { LANGS } from '../src/lang.ts';
import { fillI18n, langFromPath, renderBody, renderHead, renderRobots, renderSitemap } from '../build/prerender.ts';

const landing = fs.readFileSync(new URL('../src/landing.html', import.meta.url), 'utf8');
const SITE = 'https://netgauge.app';

test('langFromPath: raíz = ES, /en/ y /pt/ por prefijo', () => {
  assert.equal(langFromPath('/'), 'es');
  assert.equal(langFromPath('/en/'), 'en');
  assert.equal(langFromPath('/pt/index.html?x=1'), 'pt');
  assert.equal(langFromPath('/otra/'), 'es');
});

test('cada clave data-i18n del markup existe en los 3 idiomas (fillI18n lanza si falta)', () => {
  for (const lang of LANGS) assert.doesNotThrow(() => fillI18n(landing, lang));
});

test('el markup prerenderizado no deja atributos data-i18n sueltos', () => {
  for (const lang of LANGS) assert.doesNotMatch(fillI18n(landing, lang), /data-i18n/);
});

test('el copy de privacidad menciona GitHub y no promete "ningún servidor"', () => {
  for (const lang of LANGS) {
    const html = renderBody(landing, lang);
    assert.match(html, /GitHub/);
    assert.doesNotMatch(html, /ningún servidor|any server|nenhum servidor|nunca salen de tu equipo/);
    assert.match(html, /PRIVACY\.md/);
  }
});

test('la descripción de macOS firmado/Windows sin firmar está en los 3 idiomas', () => {
  assert.match(renderBody(landing, 'es'), /notarizado por Apple/);
  assert.match(renderBody(landing, 'en'), /notarized by Apple/);
  assert.match(renderBody(landing, 'pt'), /notarizado pela Apple/);
  for (const lang of LANGS) assert.doesNotMatch(renderBody(landing, lang), /click derecho|Right-click|botão direito/i);
});

test('head: canonical, hreflang x4, og:url/image absolutos y locale por idioma', () => {
  const head = renderHead('en', SITE);
  assert.match(head, /<link rel="canonical" href="https:\/\/netgauge\.app\/en\/" \/>/);
  for (const l of ['es', 'en', 'pt', 'x-default']) assert.match(head, new RegExp(`hreflang="${l}"`));
  assert.match(head, /og:url" content="https:\/\/netgauge\.app\/en\/"/);
  assert.match(head, /og:image" content="https:\/\/netgauge\.app\/og-image\.png"/);
  assert.match(head, /og:locale" content="en_US"/);
  assert.match(head, /summary_large_image/);
});

test('sitemap con alternates y robots con la URL absoluta', () => {
  const xml = renderSitemap(SITE, '2026-01-01');
  assert.equal((xml.match(/<url>/g) ?? []).length, 3);
  assert.match(xml, /hreflang="x-default" href="https:\/\/netgauge\.app\/"/);
  assert.match(renderRobots(SITE), /Sitemap: https:\/\/netgauge\.app\/sitemap\.xml/);
});

test('SITE_URL personalizado se propaga a todo', () => {
  const head = renderHead('pt', 'https://example.org');
  assert.doesNotMatch(head, /netgauge\.app/);
  assert.match(head, /https:\/\/example\.org\/pt\//);
});
