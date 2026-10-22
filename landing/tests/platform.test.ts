import test from 'node:test';
import assert from 'node:assert/strict';
import { detectPlatform, isMobile, suggestMacChip } from '../src/runtime/platform.ts';

test('Android e iPhone se detectan como móviles', () => {
  const android = detectPlatform({ userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) Chrome/126', platform: 'Linux armv8l', maxTouchPoints: 5 });
  const iphone = detectPlatform({ userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) Safari/604', platform: 'iPhone', maxTouchPoints: 5 });
  assert.equal(android, 'android');
  assert.equal(iphone, 'ios');
  assert.ok(isMobile(android) && isMobile(iphone));
});

test('iPadOS que se reporta como Macintosh se trata como móvil', () => {
  const ipad = detectPlatform({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605', platform: 'MacIntel', maxTouchPoints: 5 });
  assert.equal(ipad, 'ios');
});

test('un Mac real (sin pantalla táctil) y Windows no son móviles', () => {
  const mac = detectPlatform({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605', platform: 'MacIntel', maxTouchPoints: 0 });
  const win = detectPlatform({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126', platform: 'Win32', maxTouchPoints: 0 });
  assert.equal(mac, 'mac');
  assert.equal(win, 'windows');
  assert.ok(!isMobile(mac) && !isMobile(win));
});

test('el chip de Mac solo se sugiere si el renderer lo dice explícito', () => {
  assert.equal(suggestMacChip('ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)'), 'mac-arm');
  assert.equal(suggestMacChip('ANGLE (Intel Inc., Intel(R) Iris(TM) Plus Graphics)'), 'mac-intel');
  assert.equal(suggestMacChip('Apple GPU'), null);
  assert.equal(suggestMacChip(''), null);
});
