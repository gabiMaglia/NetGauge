import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { BASE_PATH, DEFAULT_SITE_URL } from '../site.config.ts';
import { LEGACY_HOST } from '../site.config.ts';
import { legacyHostRedirect, applyBase, langFromPath, prefRedirect, renderBody } from '../build/prerender.ts';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const landing = fs.readFileSync(path.join(root, 'src/landing.html'), 'utf8');

test('config: base y dominio canónico bajo gabrielmaglia.me/apps/netgauge', () => {
  assert.equal(BASE_PATH, '/apps/netgauge/');
  assert.equal(DEFAULT_SITE_URL, 'https://www.gabrielmaglia.me/apps/netgauge');
});

test('langFromPath entiende la base', () => {
  assert.equal(langFromPath('/apps/netgauge/en/', BASE_PATH), 'en');
  assert.equal(langFromPath('/apps/netgauge/pt/x', BASE_PATH), 'pt');
  assert.equal(langFromPath('/apps/netgauge/', BASE_PATH), 'es');
});

test('links del switcher y redirect de preferencia llevan la base', () => {
  const body = renderBody(landing, 'en', BASE_PATH);
  for (const p of ['', 'en/', 'pt/']) assert.match(body, new RegExp(`href="/apps/netgauge/${p}" hreflang`));
  assert.doesNotMatch(body, /href="\/(en\/|pt\/)?"/);
  assert.equal(applyBase('<a href="//cdn.x/y">', BASE_PATH), '<a href="//cdn.x/y">');
  const r = prefRedirect(BASE_PATH);
  assert.match(r, /'\/apps\/netgauge\/en\/'/);
  assert.match(r, /location\.pathname==='\/apps\/netgauge\/'/);
});

// Build real: ningún asset sale sin base ni queda netgauge.app (falla en rojo si se quita `base`).
test('build: assets, fuentes, favicon e idiomas bajo la base; 0 netgauge.app', () => {
  execFileSync(process.execPath, ['node_modules/vite/bin/vite.js', 'build', '--outDir', 'dist-test', '--emptyOutDir'], {
    cwd: root,
    stdio: 'pipe',
    env: { ...process.env, VITE_SITE_URL: '' },
  });
  const out = path.join(root, 'dist-test');
  try {
    const files: string[] = [];
    const walk = (d: string) =>
      fs.readdirSync(d, { withFileTypes: true }).forEach((e) => {
        const f = path.join(d, e.name);
        if (e.isDirectory()) walk(f);
        else files.push(f);
      });
    walk(out);
    for (const f of files.filter((f) => /\.(html|css|js|xml|txt)$/.test(f))) {
      const txt = fs.readFileSync(f, 'utf8');
      assert.doesNotMatch(txt, /netgauge\.app/, `netgauge.app en ${f}`);
    }
    for (const page of ['index.html', 'en/index.html', 'pt/index.html']) {
      const html = fs.readFileSync(path.join(out, page), 'utf8');
      const refs = [...html.matchAll(/\s(?:href|src)="(\/[^"]*)"/g)].map((m) => m[1]).filter((u) => !u.startsWith('//'));
      assert.ok(refs.length > 5, `${page}: se esperaban refs`);
      for (const u of refs) assert.ok(u.startsWith('/apps/netgauge/'), `${page}: ${u} sin base`);
      assert.match(html, /rel="canonical" href="https:\/\/www\.gabrielmaglia\.me\/apps\/netgauge\//);
    }
    for (const css of files.filter((f) => f.endsWith('.css'))) {
      for (const m of fs.readFileSync(css, 'utf8').matchAll(/url\(([^)]+)\)/g)) {
        const u = m[1].replace(/['"]/g, '');
        if (!u.startsWith('data:')) assert.ok(u.startsWith('/apps/netgauge/'), `css: ${u} sin base`);
      }
    }
    const sm = fs.readFileSync(path.join(out, 'sitemap.xml'), 'utf8');
    assert.equal((sm.match(/<loc>https:\/\/www\.gabrielmaglia\.me\/apps\/netgauge\//g) ?? []).length, 3);
    assert.match(fs.readFileSync(path.join(out, 'robots.txt'), 'utf8'), /gabrielmaglia\.me\/apps\/netgauge\/sitemap\.xml/);
  } finally {
    fs.rmSync(out, { recursive: true, force: true });
  }
});

test('host viejo: redirect client-side a la URL canónica preservando path, sin tocar otros hosts', () => {
  const code = legacyHostRedirect(LEGACY_HOST, DEFAULT_SITE_URL, BASE_PATH);
  const run = (hostname: string, pathname: string) => {
    let to = '';
    new Function('location', code)({ hostname, pathname, search: '?a=1', hash: '#x', replace: (u: string) => (to = u) });
    return to;
  };
  assert.equal(run(LEGACY_HOST, '/en/'), 'https://www.gabrielmaglia.me/apps/netgauge/en/?a=1#x');
  assert.equal(run(LEGACY_HOST, '/'), 'https://www.gabrielmaglia.me/apps/netgauge/?a=1#x');
  assert.equal(run('www.gabrielmaglia.me', '/apps/netgauge/en/'), ''); // vía proxy: sin loop
  assert.equal(run('localhost', '/'), '');
});
