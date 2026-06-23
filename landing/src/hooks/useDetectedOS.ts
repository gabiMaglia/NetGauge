import { useState } from 'react';
import type { OS } from '../data/constants';

function detectOS(): OS {
  if (typeof navigator === 'undefined') return 'unknown';
  const p = navigator.userAgent.toLowerCase();

  if (p.includes('win')) return 'windows';
  if (p.includes('mac')) {
    // No podemos distinguir Intel de Apple Silicon de forma fiable desde el navegador.
    // Resaltamos Apple Silicon por ser el caso más común en hardware reciente,
    // pero los 3 botones quedan siempre visibles y accionables.
    return 'mac-arm';
  }
  return 'unknown';
}

/**
 * Detecta el SO del visitante para RESALTAR el botón correspondiente.
 * Nunca oculta los demás: el navegador no distingue Mac Intel de Apple
 * Silicon de forma fiable, así que en Mac solo resaltamos "mac" en general
 * y dejamos que la persona elija entre Apple Silicon / Intel.
 */
export function useDetectedOS(): OS {
  const [os] = useState<OS>(detectOS);
  return os;
}
