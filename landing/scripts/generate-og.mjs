/**
 * Regenera og-image.png (1200x630), favicon-32.png y apple-touch-icon.png en
 * public/ renderizando las plantillas de scripts/ con Chrome headless.
 * Uso: `npm run og` (CHROME_PATH para otro binario; `sips` de macOS redimensiona).
 */
import { execFileSync } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const pub = path.join(here, '..', 'public');
const chrome = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const tmp = mkdtempSync(path.join(tmpdir(), 'ng-og-'));

function shot(template, query, out, w, h, transparent = false) {
  const url = pathToFileURL(path.join(here, template)).href + query;
  const args = [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
    '--force-device-scale-factor=1', `--window-size=${w},${h}`, '--virtual-time-budget=3000',
    ...(transparent ? ['--default-background-color=00000000'] : []),
    `--screenshot=${out}`, url,
  ];
  execFileSync(chrome, args, { stdio: 'ignore' });
}

shot('og-template.html', '', path.join(pub, 'og-image.png'), 1200, 630);

// Chrome no baja de ~500px de ventana: se renderiza a 512 y sips reduce.
const big = path.join(tmp, 'icon-512.png');
shot('icon-template.html', '', big, 512, 512, true);
execFileSync('sips', ['-z', '32', '32', big, '--out', path.join(pub, 'favicon-32.png')], { stdio: 'ignore' });
const bigSq = path.join(tmp, 'icon-sq-512.png');
shot('icon-template.html', '?square=1', bigSq, 512, 512);
execFileSync('sips', ['-z', '180', '180', bigSq, '--out', path.join(pub, 'apple-touch-icon.png')], { stdio: 'ignore' });
console.log('og-image.png, favicon-32.png y apple-touch-icon.png actualizados en public/');
