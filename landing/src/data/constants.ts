/**
 * Coordenadas del repo y links externos.
 * Fuente: src/version.py (raíz del repo) y engram/03_backlog.md §T-015.
 * NO hardcodear URLs de assets de release: no están confirmadas (ver ADR-001 / handoff T-015).
 */
export const GITHUB_OWNER = 'gabiMaglia';
export const GITHUB_REPO = 'trafficMe';
export const GITHUB_URL = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}`;
export const RELEASES_LATEST_URL = `${GITHUB_URL}/releases/latest`;
export const KOFI_URL = 'https://ko-fi.com/gabrielmaglia';
export const LICENSE_URL = `${GITHUB_URL}/blob/main/LICENSE`;

export type OS = 'windows' | 'mac-arm' | 'mac-intel' | 'unknown';

export interface DownloadOption {
  id: OS;
  label: string;
  sublabel: string;
}

export const DOWNLOAD_OPTIONS: DownloadOption[] = [
  { id: 'windows', label: 'Windows 10/11 (x64)', sublabel: 'Instalador .exe' },
  { id: 'mac-arm', label: 'macOS Apple Silicon (M1–M4)', sublabel: 'Instalador .dmg' },
  { id: 'mac-intel', label: 'macOS Intel', sublabel: 'Instalador .dmg' },
];
