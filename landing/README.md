# NetGauge — Landing page

Landing one-page de NetGauge (ticket T-015). React + Vite + TypeScript, sin
dependencias externas más allá del stack base. Vive en `/landing` y no toca
nada del resto del repo (`src/`, workflows, instaladores).

## Requisitos

- Node.js 20+
- npm 10+

## Desarrollo

```bash
cd landing
npm install
npm run dev
```

Abre en `http://localhost:5173` por defecto.

## Build de producción

```bash
npm run build
```

Genera `dist/` listo para servir como sitio estático (sin SSR, sin backend).
El hosting final se define en un ticket aparte; por ahora el build es local.

## Lint

```bash
npm run lint
```

## Estructura

Desde T-018 el markup de la landing se porta pixel-perfect como HTML estático
(no por componentes), inyectado verbatim en el DOM:

- `src/landing.html` — markup completo de la landing (todas las secciones),
  importado como string crudo (`?raw`) e inyectado vía
  `dangerouslySetInnerHTML` en `App.tsx`. Es la única fuente del layout/estilos
  inline; no se reescribe a JSX para mantener la fidelidad 1:1 con el diseño.
- `src/App.tsx` — runtime que se monta sobre `landing.html`: detección de SO
  (auto-resalta el botón de descarga sin ocultar los otros), contadores
  animados (`data-count`), reveal-on-scroll (`data-reveal`, respeta
  `prefers-reduced-motion`), hover declarativo (`style-hover`) e inicialización
  de i18n.
- `src/i18n.ts` — diccionario ES/EN/PT (T-020) + runtime de aplicación: detecta
  idioma inicial (`localStorage` > `navigator.language` > default ES),
  persiste la elección, actualiza `<html lang>`/`<title>`/meta description, y
  aplica el diccionario a todo nodo `data-i18n="clave"` (texto plano) o
  `data-i18n-html="clave"` (HTML interno controlado, para `<span>/<b>`
  embebidos sin romper el layout). También resuelve los labels del botón de
  descarga auto-detectado (`data-os-label`/`data-os-sub`) por idioma.
- `public/favicon.svg` — ícono de la app (3 barras ascendentes, gradiente azul
  `#3b82f6`→`#60a5fa`; T-021). El mismo mark se repite inline en
  `landing.html` (header, titlebar del mock, footer).

Para sumar/editar copy: agregar la clave en los 3 idiomas dentro de
`src/i18n.ts` y anotar el nodo correspondiente en `landing.html` con
`data-i18n`/`data-i18n-html`. No agregar texto sin su anotación: rompe el
switcher de idioma.

## Notas

- Los 3 botones de descarga siempre apuntan a `releases/latest` del repo.
  El auto-detect de SO solo resalta una opción, nunca oculta las otras dos
  (no se puede distinguir Mac Intel de Apple Silicon de forma fiable desde
  el navegador).
- Reglas de contenido que no deben violarse en ningún idioma: la cuota
  *avisa*, nunca bloquea ni corta la conexión; la privacidad es exacta
  (historial local; VirusTotal/GeoIP opt-in y apagados por defecto; solo se
  envía un hash o una IP, nunca archivos); el "índice de confianza"
  (Authenticode) es **solo Windows**.
