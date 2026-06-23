# NetLeak — Landing page

Landing one-page de NetLeak (ticket T-015). React + Vite + TypeScript, sin
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

- `src/components/` — un componente por sección de la landing (Header, Hero,
  Features, Privacy, Download, Faq, etc.), cada uno con su CSS Module.
- `src/hooks/` — lógica reutilizable: detección de SO (`useDetectedOS`),
  `prefers-reduced-motion`, reveal-on-scroll y el sparkline decorativo.
- `src/data/` — contenido (`content.ts`) y coordenadas/links del repo
  (`constants.ts`). Mover acá cualquier copy nuevo en vez de hardcodearlo en
  los componentes.
- `public/screenshots/` — placeholders para futuras capturas reales de la app
  (no existen capturas reales todavía, ver handoff T-015).

## Notas

- Los 3 botones de descarga (`DownloadButtons`) siempre apuntan a
  `releases/latest` del repo. El auto-detect de SO solo resalta una opción,
  nunca oculta las otras dos (no se puede distinguir Mac Intel de Apple
  Silicon de forma fiable desde el navegador).
- Las screenshots de la ventana de la app son placeholders (`ScreenshotPlaceholder`).
  Reemplazar por capturas reales cuando estén disponibles.
