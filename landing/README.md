# NetGauge — Landing page

Landing one-page de NetGauge. Vite + TypeScript, **sin framework en runtime**:
el HTML se prerenderiza por idioma en el build y el navegador solo mejora lo
que depende del dispositivo (~3 KB de JS gzip). Vive en `/landing` y no toca
nada del resto del repo (`src/`, workflows, instaladores).

## Requisitos

- Node.js 24+ (los tests y el build usan type-stripping nativo de TS)
- npm 10+

## Desarrollo, build y preview

```bash
cd landing
npm install
npm run dev        # http://localhost:5173  (también /en/ y /pt/)
npm run build      # tsc -b && vite build  → dist/
npm run preview    # sirve dist/ en http://localhost:4173
npm run lint
npm test           # node --test (sin dependencias extra)
```

Para verlo en local tal como sale a producción:
`npm run build && npm run preview` y abrir `http://localhost:4173/apps/netgauge/`,
`/apps/netgauge/en/` y `/apps/netgauge/pt/`.

## Dominio (SITE_URL)

La constante única vive en `site.config.ts` (`DEFAULT_SITE_URL`, hoy
`https://www.gabrielmaglia.me/apps/netgauge`) y se puede sobreescribir por entorno:

```bash
VITE_SITE_URL=https://otro-dominio.com npm run build
```

De ahí salen `canonical`, `hreflang`, `og:url`, `og:image` (absoluta),
`sitemap.xml` y `robots.txt`. Si el dominio final es otro, cambiá el default en
`site.config.ts` o definí `VITE_SITE_URL` en el CI/hosting y rebuild. Nada más
hardcodea el dominio.

### Base `/apps/netgauge/` y host viejo

La landing vive en `https://www.gabrielmaglia.me/apps/netgauge/`: el portfolio
hace un rewrite server-side a `net-gauge-brown.vercel.app` y los archivos siguen
en la raíz del deploy. Vite usa `base: BASE_PATH` (`site.config.ts`) y el
prerender reutiliza esa misma base para los links del switcher (`/en/`, `/pt/`)
y el redirect de preferencia. El test `tests/base.test.ts` buildea y falla si
algún asset/font/favicon no lleva la base o queda `netgauge.app`.

El host viejo redirige **client-side** (script inline en `<head>`, solo si
`location.hostname === 'net-gauge-brown.vercel.app'`). No se usó un redirect de
`vercel.json` por host porque el request proxeado llega a Vercel con
`Host: net-gauge-brown.vercel.app` y recibiría el 308, rompiendo el proxy.

## Rutas por idioma y prerender

Rutas estáticas `/` (ES, también `x-default`), `/en/` y `/pt/`. Cada una es
HTML ya renderizado (contenido, `<html lang>`, title, description, Open Graph,
Twitter, canonical y `hreflang`), generado en el build por un plugin propio de
Vite (`build/vite-plugin-prerender.ts`):

- `transformIndexHtml` inyecta head + markup del idioma (también en `vite dev`).
- `writeBundle` clona el `index.html` ya procesado (assets con hash) a
  `dist/en/` y `dist/pt/`, y emite `sitemap.xml` (con alternates) y `robots.txt`.
- `build/prerender.ts` vuelca el copy sobre `src/landing.html` con un escáner
  de etiquetas balanceadas: sin jsdom ni dependencias, y el build falla si
  falta una clave i18n.

El switcher de idioma son `<a href="/en/">` reales (rastreables, funcionan sin
JS). Al elegir uno se guarda la preferencia en `localStorage`; un script inline
mínimo en `<head>` solo redirige desde `/` a la ruta guardada, así los
buscadores (sin preferencia guardada) siempre ven ES en `/`.

## Estructura

- `src/landing.html` — markup completo de la landing (única fuente del layout).
  Los nodos de texto se anotan con `data-i18n="clave"` (texto plano),
  `data-i18n-html="clave"` (HTML interno controlado) o
  `data-i18n-attr="aria-label:clave"` (atributos). No agregar texto sin su
  anotación: el prerender no lo traduce.
- `src/i18n.ts` — copy ES/EN/PT (única fuente), `meta` por idioma y labels del
  CTA por SO. Solo lo usa el build; el navegador no carga diccionarios, recibe
  las pocas cadenas que necesita en `<script type="application/json" id="ng-rt">`.
- `src/lang.ts` — idiomas, rutas y claves compartidas build/runtime.
- `src/main.ts` + `src/runtime/` — mejoras en el navegador: menú móvil
  (`menu.ts`), detección de SO (`platform.ts`), CTA y enlaces de descarga
  (`downloads.ts`, `releases.ts`), "Enviame el link" en móviles (`share.ts`),
  contadores/reveal (`effects.ts`) y preferencia de idioma (`lang.ts`).
- `src/index.css` — fuentes self-hosted, hover/focus (`.hv-*`), header y reglas
  responsive. Los estilos base siguen inline en el markup; lo que cambia por
  viewport o estado gana con `!important` desde acá.
- `public/fonts/` — Plus Jakarta Sans (variable, 1 archivo) y JetBrains Mono
  (500/700), ambas SIL OFL (licencias incluidas). Sin Google Fonts.
- `public/og-image.png`, `favicon-32.png`, `apple-touch-icon.png` — se
  regeneran con `npm run og` (Chrome headless + `sips`, plantillas en `scripts/`).

Para sumar/editar copy: agregar la clave en los 3 idiomas dentro de
`src/i18n.ts` y anotar el nodo en `landing.html`.

## Descargas y detección de SO

- El HTML apunta a `releases/latest` (página de releases de GitHub). Al cargar,
  si la API de GitHub responde (`/releases/latest`, con timeout y caché de
  sesión), los botones pasan a enlaces directos al `.exe` y a cada `.dmg`; si
  falla o hay rate limit, siguen yendo a la página de releases y se muestra una
  línea aclaratoria. No hay dependencia de red para que la página funcione.
- Windows: el CTA principal enlaza al `.exe`. macOS: el CTA muestra "macOS"
  genérico y lleva a los botones Intel / Apple Silicon (no se autoselecciona la
  arquitectura; si el renderer WebGL lo dice explícito, se marca como
  "Sugerido"). Android, iPhone e iPad (incluido iPadOS que se reporta como
  Macintosh con `maxTouchPoints > 1`): el CTA pasa a "Enviame el link"
  (`navigator.share` → portapapeles con aviso → `mailto:`).
- Firma: macOS = `.dmg` firmado y notarizado por Apple (desde la v2.0.3);
  Windows = `.exe` sin firmar, SmartScreen puede avisar (enlace a la Code
  signing policy del README principal).

## Notas de contenido

Reglas que no deben violarse en ningún idioma: la cuota *avisa*, nunca bloquea
ni corta la conexión; la privacidad es exacta respecto de `PRIVACY.md` (sin
telemetría ni cuentas; solo consulta GitHub para avisar de versiones nuevas,
apagable en Ajustes; VirusTotal/GeoIP opt-in y apagados por defecto; GeoIP va
por HTTP sin cifrar; solo viaja un hash o una IP, nunca archivos); el "índice
de confianza" (Authenticode) es **solo Windows**.
