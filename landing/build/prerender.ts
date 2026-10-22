/**
 * Prerender de la landing: toma el markup (src/landing.html), vuelca el copy
 * del idioma y genera head/body/sitemap/robots. Sin DOM ni dependencias: el
 * markup tiene una forma controlada (nodos hoja con data-i18n*), así que un
 * escáner de etiquetas balanceadas alcanza y evita sumar jsdom al build.
 */
import { DEFAULT_LANG, LANGS, LANG_PATH, LANG_STORAGE_KEY, OG_LOCALE, type Lang } from '../src/lang.ts';
import { dictionaries, meta, osLabels } from '../src/i18n.ts';

const REPO = 'https://github.com/gabiMaglia/NetGauge';

const escText = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const escAttr = (s: string) => escText(s).replace(/"/g, '&quot;');

/** Idioma de una URL de la landing (`/en/…` → en; cualquier otra → ES). */
export function langFromPath(path: string): Lang {
  const seg = path.split(/[?#]/)[0].split('/').filter(Boolean)[0];
  return (LANGS as string[]).includes(seg ?? '') && seg !== DEFAULT_LANG ? (seg as Lang) : DEFAULT_LANG;
}

/** Índice del cierre `</tag>` que balancea la apertura ya consumida en `from`. */
function findClose(html: string, tag: string, from: number): { start: number; end: number } {
  const re = new RegExp(`<(/?)${tag}\\b[^>]*>`, 'gi');
  re.lastIndex = from;
  let depth = 1;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    if (m[1]) depth--;
    else if (!m[0].endsWith('/>')) depth++;
    if (depth === 0) return { start: m.index, end: m.index + m[0].length };
  }
  throw new Error(`landing.html: <${tag}> sin cierre`);
}

export function fillI18n(html: string, lang: Lang): string {
  const dict = dictionaries[lang];
  const need = (key: string) => {
    const v = dict[key];
    if (v === undefined) throw new Error(`i18n: falta la clave "${key}" en ${lang}`);
    return v;
  };

  // 1) contenido: data-i18n (texto) y data-i18n-html (HTML controlado)
  const open = /<([a-z][a-z0-9]*)\b[^>]*?\sdata-i18n(-html)?="([^"]+)"[^>]*>/gi;
  let out = '';
  let pos = 0;
  let m: RegExpExecArray | null;
  while ((m = open.exec(html))) {
    const [full, tag, isHtml, key] = m;
    const close = findClose(html, tag, m.index + full.length);
    const val = need(key);
    out += html.slice(pos, m.index);
    out += full.replace(/\sdata-i18n(-html)?="[^"]+"/, '');
    out += isHtml ? val : escText(val);
    pos = close.start; // el cierre original se copia en la próxima pasada
    open.lastIndex = close.start;
  }
  out += html.slice(pos);

  // 2) atributos: data-i18n-attr="aria-label:clave;title:clave"
  out = out.replace(/<[a-z][^>]*\sdata-i18n-attr="([^"]+)"[^>]*>/gi, (tagText, spec: string) => {
    let t = tagText.replace(/\sdata-i18n-attr="[^"]+"/, '');
    for (const pair of spec.split(';')) {
      const [name, key] = pair.split(':');
      const val = escAttr(need(key));
      const re = new RegExp(`(\\s${name}=)"[^"]*"`);
      t = re.test(t) ? t.replace(re, `$1"${val}"`) : t.replace(/\/?>$/, (e) => ` ${name}="${val}"${e}`);
    }
    return t;
  });

  // 3) switcher: marca el idioma de la página
  out = out.replace(new RegExp(`(data-lang-link="${lang}")`, 'g'), '$1 aria-current="true"');
  return out;
}

/** Cadenas que el navegador necesita en runtime (OS, compartir). Nada de diccionarios. */
function runtimeJson(lang: Lang): string {
  const d = dictionaries[lang];
  const data = {
    lang,
    os: osLabels[lang],
    suggested: d['download.suggested'],
    share: {
      cta: d['share.cta'],
      sub: d['share.sub'],
      copied: d['share.copied'],
      subject: d['share.subject'],
      text: d['share.text'],
    },
  };
  // `<` escapado para que ningún valor pueda cerrar el <script>
  return JSON.stringify(data).replace(/</g, '\\u003c');
}

export function renderBody(landingHtml: string, lang: Lang): string {
  const d = dictionaries[lang];
  const noscript =
    `<noscript><p style="margin:0;padding:16px 24px;background:#0a0f1a;color:#e6f0fa;font-family:system-ui,sans-serif;font-size:14px">` +
    `${escText(d['noscript.text'])} <a href="${REPO}/releases/latest" style="color:#7cc3f5">${escText(d['noscript.link'])}</a>.</p></noscript>`;
  return (
    fillI18n(landingHtml, lang) +
    `\n<script type="application/json" id="ng-rt">${runtimeJson(lang)}</script>\n${noscript}\n`
  );
}

export function pageUrl(siteUrl: string, lang: Lang): string {
  return siteUrl + LANG_PATH[lang];
}

export function renderHead(lang: Lang, siteUrl: string): string {
  const m = meta[lang];
  const url = pageUrl(siteUrl, lang);
  const image = `${siteUrl}/og-image.png`;
  const t = escAttr(m.title);
  const desc = escAttr(m.description);
  const alternates = LANGS.map(
    (l) => `<link rel="alternate" hreflang="${l}" href="${pageUrl(siteUrl, l)}" />`,
  ).join('\n    ');
  const otherLocales = LANGS.filter((l) => l !== lang)
    .map((l) => `<meta property="og:locale:alternate" content="${OG_LOCALE[l]}" />`)
    .join('\n    ');
  return `
    <title>${escText(m.title)}</title>
    <meta name="description" content="${desc}" />
    <link rel="canonical" href="${url}" />
    ${alternates}
    <link rel="alternate" hreflang="x-default" href="${pageUrl(siteUrl, DEFAULT_LANG)}" />

    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="NetGauge" />
    <meta property="og:title" content="${t}" />
    <meta property="og:description" content="${desc}" />
    <meta property="og:url" content="${url}" />
    <meta property="og:image" content="${image}" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta property="og:image:alt" content="${t}" />
    <meta property="og:locale" content="${OG_LOCALE[lang]}" />
    ${otherLocales}

    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="${t}" />
    <meta name="twitter:description" content="${desc}" />
    <meta name="twitter:image" content="${image}" />
    `;
}

/** Script inline mínimo: si el usuario eligió otro idioma antes, `/` lo lleva a su ruta. */
export const PREF_REDIRECT = `(function(){try{var l=localStorage.getItem('${LANG_STORAGE_KEY}');var p={en:'/en/',pt:'/pt/'}[l];if(p&&location.pathname==='/')location.replace(p+location.search+location.hash)}catch(e){}})()`;

export function renderSitemap(siteUrl: string, lastmod: string): string {
  const links = (): string =>
    [
      ...LANGS.map(
        (l) => `    <xhtml:link rel="alternate" hreflang="${l}" href="${pageUrl(siteUrl, l)}"/>`,
      ),
      `    <xhtml:link rel="alternate" hreflang="x-default" href="${pageUrl(siteUrl, DEFAULT_LANG)}"/>`,
    ].join('\n');
  const urls = LANGS.map(
    (l) => `  <url>\n    <loc>${pageUrl(siteUrl, l)}</loc>\n    <lastmod>${lastmod}</lastmod>\n${links()}\n  </url>`,
  ).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n${urls}\n</urlset>\n`;
}

export function renderRobots(siteUrl: string): string {
  return `User-agent: *\nAllow: /\n\nSitemap: ${siteUrl}/sitemap.xml\n`;
}
