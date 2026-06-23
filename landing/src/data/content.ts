import type { AccordionItemData } from '../components/Accordion';

export interface Feature {
  icon: string;
  title: string;
  description: string;
}

/** Features reales verificados contra src/ (ver handoff 2026-06-22, no inventados). */
export const FEATURES: Feature[] = [
  {
    icon: '📊',
    title: 'Consumo por aplicación',
    description: 'Ranking en vivo de qué app está usando tu red, no solo un total genérico.',
  },
  {
    icon: '⚡',
    title: 'Velocidad en tiempo real',
    description: 'Subida y bajada (↑/↓) con gráfico de los últimos 2 minutos.',
  },
  {
    icon: '🔔',
    title: 'Cuotas con alertas',
    description: 'Te avisa al 80% y al 100% de tu cuota. No corta tu conexión.',
  },
  {
    icon: '🗂️',
    title: 'Historial completo',
    description: 'Por sesión, día, semana o mes. Todo guardado localmente en tu equipo.',
  },
  {
    icon: '🔒',
    title: 'Privacidad real',
    description: 'Sin telemetría. VirusTotal y GeoIP son opcionales y vienen apagados.',
  },
  {
    icon: '📄',
    title: 'Informes en un clic',
    description: 'Exportá tu consumo a CSV, Excel o PDF cuando lo necesites.',
  },
];

export interface Step {
  number: string;
  title: string;
  description: string;
}

export const STEPS: Step[] = [
  { number: '1', title: 'Descargá e instalá', description: 'Elegí tu sistema operativo y corré el instalador.' },
  { number: '2', title: 'Vive en tu bandeja', description: 'trafficMe queda discreto en la bandeja del sistema, midiendo en segundo plano.' },
  { number: '3', title: 'Mirá, controlá y exportá', description: 'Abrí la ventana cuando quieras ver el detalle o exportar un informe.' },
];

export interface AdvancedPoint {
  title: string;
  description: string;
}

export const ADVANCED_POINTS: AdvancedPoint[] = [
  {
    title: 'Conexiones activas por app',
    description: 'IP, puerto, país y proveedor de cada conexión. La geolocalización de IP es opt-in (apagada por defecto).',
  },
  {
    title: 'Índice de confianza (Windows)',
    description: 'Verifica la firma Authenticode del ejecutable en Windows. Es una función exclusiva de Windows, no multiplataforma.',
  },
  {
    title: 'Alertas de anomalías',
    description: 'Te avisa si una app tiene un pico de tráfico 3 veces mayor a su promedio, o si una app nueva empieza a usar la red.',
  },
];

export interface ComparisonRow {
  label: string;
  value: string;
}

export const COMPARISON_ROWS: ComparisonRow[] = [
  { label: 'Precio', value: 'Gratis' },
  { label: 'Código abierto', value: 'Sí' },
  { label: 'Telemetría', value: 'No' },
  { label: 'Windows + Mac', value: 'Sí' },
  { label: 'Desglose por aplicación', value: 'Sí' },
];

export const TRUST_BADGES: string[] = [
  'MIT License',
  'GitHub',
  'Windows 10/11',
  'macOS Intel + Apple Silicon',
  '100% local',
];

export const FAQ_ITEMS: AccordionItemData[] = [
  {
    question: '¿Es gratis?',
    answer: 'Sí, trafficMe es gratis y de código abierto (licencia MIT). No hay versión paga ni funciones bloqueadas.',
  },
  {
    question: '¿Manda mis datos?',
    answer: 'No. Tu historial de consumo se guarda localmente en tu equipo. Las únicas funciones que usan internet (reputación VirusTotal y geolocalización de IPs) son opcionales y vienen apagadas por defecto; cuando las activás, solo envían un hash o una IP, nunca tus archivos.',
  },
  {
    question: '¿Por qué me avisa el sistema al abrirlo?',
    answer: 'El instalador todavía no está firmado digitalmente, así que Windows o macOS pueden mostrar una advertencia. Es por la falta de firma, no por riesgo: el código es abierto y lo podés revisar en GitHub.',
  },
  {
    question: '¿Necesito admin?',
    answer: 'En algunos casos el sistema operativo puede pedir permisos elevados para instalar o para que la app pueda medir el tráfico de red de otras aplicaciones.',
  },
  {
    question: '¿Anda en Mac con chip M?',
    answer: 'Sí, hay instalador nativo para Apple Silicon (M1–M4) y otro para Mac con procesador Intel.',
  },
  {
    question: '¿Corta el internet al llegar a la cuota?',
    answer: 'No. La cuota te avisa al 80% y al 100% de uso, pero nunca corta ni bloquea tu conexión.',
  },
];
