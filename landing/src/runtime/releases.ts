export interface ReleaseLinks {
  win?: string;
  'mac-arm'?: string;
  'mac-intel'?: string;
}

const API = 'https://api.github.com/repos/gabiMaglia/NetGauge/releases/latest';
const DOWNLOAD_PREFIX = 'https://github.com/gabiMaglia/NetGauge/releases/download/';
const CACHE_KEY = 'ng-release-links';
const CACHE_MS = 5 * 60 * 1000;

interface Asset {
  name: string;
  browser_download_url: string;
}

/** Clasifica los assets de la release por nombre (.exe / .dmg arm64 / .dmg x86_64). */
export function pickAssets(assets: Asset[]): ReleaseLinks {
  const out: ReleaseLinks = {};
  for (const a of assets) {
    // Solo enlaces de descarga del propio repo: nunca se confía en una URL ajena.
    if (!a.browser_download_url?.startsWith(DOWNLOAD_PREFIX)) continue;
    const n = a.name.toLowerCase();
    if (n.endsWith('.exe')) out.win ??= a.browser_download_url;
    else if (n.endsWith('.dmg')) {
      if (/arm64|aarch64|apple/.test(n)) out['mac-arm'] ??= a.browser_download_url;
      else if (/x86_64|x64|intel|amd64/.test(n)) out['mac-intel'] ??= a.browser_download_url;
    }
  }
  return out;
}

function readCache(): ReleaseLinks | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const { t, links } = JSON.parse(raw) as { t: number; links: ReleaseLinks };
    return Date.now() - t < CACHE_MS ? links : null;
  } catch {
    return null;
  }
}

/**
 * Mejora progresiva: el HTML ya apunta a /releases/latest. Si la API responde,
 * los botones pasan a enlaces directos; si falla (red, rate limit), no pasa nada.
 */
export async function fetchReleaseLinks(): Promise<ReleaseLinks | null> {
  const cached = readCache();
  if (cached) return cached;
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 5000);
  try {
    const res = await fetch(API, { signal: ctl.signal, headers: { Accept: 'application/vnd.github+json' } });
    if (!res.ok) return null;
    const data = (await res.json()) as { assets?: Asset[] };
    const links = pickAssets(data.assets ?? []);
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify({ t: Date.now(), links }));
    } catch {
      /* sessionStorage puede no estar disponible */
    }
    return links;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}
