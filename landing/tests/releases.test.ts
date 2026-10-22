import test from 'node:test';
import assert from 'node:assert/strict';
import { pickAssets } from '../src/runtime/releases.ts';

const base = 'https://github.com/gabiMaglia/NetGauge/releases/download/v2.0.1/';
const asset = (name: string) => ({ name, browser_download_url: base + name });

test('clasifica los assets reales de la release', () => {
  const links = pickAssets([
    asset('NetGauge-2.0.1-arm64.dmg'),
    asset('NetGauge-2.0.1-x86_64.dmg'),
    asset('NetGauge-Setup-2.0.1-x64.exe'),
  ]);
  assert.match(links.win ?? '', /Setup-2\.0\.1-x64\.exe$/);
  assert.match(links['mac-arm'] ?? '', /arm64\.dmg$/);
  assert.match(links['mac-intel'] ?? '', /x86_64\.dmg$/);
});

test('ignora URLs que no son del repo y archivos desconocidos', () => {
  const links = pickAssets([
    { name: 'evil.exe', browser_download_url: 'https://evil.example/evil.exe' },
    asset('checksums.txt'),
  ]);
  assert.deepEqual(links, {});
});
