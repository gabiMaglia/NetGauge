/**
 * i18n de la landing (T-020). Diccionario ES/EN/PT(BR) + runtime de aplicación
 * sobre el DOM ya inyectado (`landing.html` vía `dangerouslySetInnerHTML`).
 *
 * Enfoque: nodos anotados con `data-i18n="clave"` (texto plano, vía
 * `textContent`) o `data-i18n-html="clave"` (HTML interno controlado, vía
 * `innerHTML`, para los casos con `<span>/<b>` embebidos sin cambiar el
 * layout). El diccionario es la única fuente de copy por idioma.
 */

export type Lang = 'es' | 'en' | 'pt';

export const LANGS: Lang[] = ['es', 'en', 'pt'];
export const DEFAULT_LANG: Lang = 'es';
const STORAGE_KEY = 'netgauge-lang';

/** Labels del botón de descarga auto-detectado por SO, por idioma. */
export const osLabels: Record<Lang, Record<string, { label: string; sub: string }>> = {
  es: {
    windows: { label: 'Descargar para Windows', sub: 'Windows 10/11 · 64-bit' },
    'mac-arm': { label: 'Descargar para macOS', sub: 'Apple Silicon · M1–M4' },
    'mac-intel': { label: 'Descargar para macOS', sub: 'Mac con Intel' },
    linux: { label: 'Descargar gratis', sub: 'Windows y macOS' },
    other: { label: 'Descargar gratis', sub: 'Windows y macOS' },
  },
  en: {
    windows: { label: 'Download for Windows', sub: 'Windows 10/11 · 64-bit' },
    'mac-arm': { label: 'Download for macOS', sub: 'Apple Silicon · M1–M4' },
    'mac-intel': { label: 'Download for macOS', sub: 'Intel Mac' },
    linux: { label: 'Download for free', sub: 'Windows and macOS' },
    other: { label: 'Download for free', sub: 'Windows and macOS' },
  },
  pt: {
    windows: { label: 'Baixar para Windows', sub: 'Windows 10/11 · 64-bit' },
    'mac-arm': { label: 'Baixar para macOS', sub: 'Apple Silicon · M1–M4' },
    'mac-intel': { label: 'Baixar para macOS', sub: 'Mac com Intel' },
    linux: { label: 'Baixar gratis', sub: 'Windows e macOS' },
    other: { label: 'Baixar gratis', sub: 'Windows e macOS' },
  },
};

/** `<title>` y meta description por idioma. */
export const meta: Record<Lang, { title: string; description: string }> = {
  es: {
    title: 'NetGauge — Monitor de consumo de red por aplicación, gratis y open source',
    description:
      'Mirá cuánto consume cada app en Windows y Mac, gratis y privado. NetGauge es un monitor de red por aplicación, de código abierto, sin telemetría.',
  },
  en: {
    title: 'NetGauge — Free, open-source per-app network usage monitor',
    description:
      'See exactly how much each app consumes on Windows and Mac, free and private. NetGauge is an open-source, per-app network monitor with no telemetry.',
  },
  pt: {
    title: 'NetGauge — Monitor de consumo de rede por aplicativo, gratuito e open source',
    description:
      'Veja quanto cada app consome no Windows e no Mac, gratuito e privado. NetGauge é um monitor de rede por aplicativo, de código aberto, sem telemetria.',
  },
};

type Dict = Record<string, string>;

const es: Dict = {
  'nav.features': 'Funciones',
  'nav.how': 'Cómo funciona',
  'nav.privacy': 'Privacidad',
  'nav.faq': 'FAQ',
  'nav.cta': 'Descargar gratis',

  'hero.badge': 'Monitor de red · Open source',
  'hero.title':
    'Sabé qué app se está <span style="color:var(--acc,#22d3ee);position:relative;white-space:nowrap">comiendo</span> tu internet.',
  'hero.subtitle':
    'Monitor de consumo de red por aplicación, en tiempo real. Gratis, de código abierto y privado: <span style="color:#cdddee;font-weight:600">tus datos nunca salen de tu equipo</span>. Windows y Mac.',
  'hero.viewGithub': 'Ver en GitHub',
  'hero.tag1': 'Gratis',
  'hero.tag2': 'Open source (MIT)',
  'hero.tag3': 'Sin telemetría',
  'hero.tag4': 'Windows + macOS',

  'mock.tabGlobal': '● Global',
  'mock.tabPerApp': 'Por aplicación',
  'mock.tabConnections': 'Conexiones',
  'mock.download': '▼ Bajada',
  'mock.upload': '▲ Subida',
  'mock.total': 'Σ Total',
  'mock.bandwidth': 'Ancho de banda · 2 min',
  'mock.peak': 'PICO 11.7 MB/s',
  'mock.dailyLimit': 'Límite diario · hoy',
  'mock.monthlyLimit': 'Límite mensual · ciclo',

  'trust.label': 'VERIFICABLE:',
  'trust.mit': 'Licencia MIT',
  'trust.github': 'Código en GitHub',
  'trust.windows': '⊞ Windows 10/11',
  'trust.macos': ' macOS Intel + Apple Silicon',
  'trust.local': '100% local',

  'problem.label': 'El problema',
  'problem.title':
    'El medidor de tu sistema te da un total.<br><span style="color:#5b7290">No el culpable.</span>',
  'problem.body':
    'NetGauge te muestra el <span style="color:#cdddee;font-weight:600">ranking de apps</span> que consumen — ahora y en tu historial.',
  'problem.beforeLabel': 'Lo que ves hoy',
  'problem.beforeCaption': 'Datos usados este mes',
  'problem.beforeMystery': '¿De dónde salió? Misterio.',
  'problem.afterLabel': 'Lo que ves con NetGauge',

  'features.label': 'Funciones',
  'features.title': 'Todo lo que tu red estaba escondiendo',
  'features.subtitle': 'Medición real por proceso. Nada de estimaciones.',
  'features.f1.title': 'Consumo por aplicación',
  'features.f1.body': 'Mirá exactamente cuánto gastó cada programa. Ranking claro, de mayor a menor.',
  'features.f2.title': 'Velocidad en tiempo real',
  'features.f2.body':
    'Subida y bajada al instante (<span style="color:#38bdf8;font-weight:700">↓</span>/<span style="color:#34d399;font-weight:700">↑</span>) con un gráfico de los últimos 2 minutos.',
  'features.f3.title': 'Cuotas con alertas',
  'features.f3.body':
    'Poné un tope diario o mensual. Te <span style="color:#cdddee;font-weight:600">avisa al 80% y al 100%</span> — nunca corta la conexión.',
  'features.f4.title': 'Historial completo',
  'features.f4.body':
    'Sesión, día, semana o mes. Todo guardado <span style="color:#cdddee;font-weight:600">local</span> en tu equipo.',
  'features.f5.title': 'Privacidad real',
  'features.f5.body':
    'Sin telemetría. VirusTotal y GeoIP son opcionales y vienen <span style="color:#cdddee;font-weight:600">apagados</span>.',
  'features.f6.title': 'Informes en un clic',
  'features.f6.body':
    'Exportá a <span style="color:#cdddee;font-weight:600">CSV, Excel o PDF</span> cuando lo necesites.',

  'how.label': 'Cómo funciona',
  'how.title': 'Listo en tres pasos',
  'how.s1.title': 'Descargá e instalá',
  'how.s1.body': 'Bajá el instalador para Windows o Mac. Liviano y sin vueltas.',
  'how.s2.title': 'Vive en tu bandeja',
  'how.s2.body': 'Queda en la bandeja del sistema con un mini-gráfico. Siempre a mano, nunca molesto.',
  'how.s3.title': 'Mirá, controlá y exportá',
  'how.s3.body': 'Abrí el panel para ver el detalle, poné cuotas y exportá informes cuando quieras.',

  'privacy.badge': 'PRIVACIDAD',
  'privacy.title': 'Tus datos son tuyos.<br>En serio.',
  'privacy.body':
    'Todo el historial vive <span style="color:#cdddee;font-weight:600">local</span> en tu equipo. NetGauge no manda nada a ningún servidor. Las únicas funciones que usan internet son <span style="color:#cdddee;font-weight:600">opcionales y vienen apagadas</span>.',
  'privacy.bullet1': '<b style="color:#eaf2fb;font-weight:700">Historial 100% local.</b> Nada sube a la nube.',
  'privacy.bullet2':
    '<b style="color:#eaf2fb;font-weight:700">VirusTotal y GeoIP apagados.</b> Vos decidís si los prendés.',
  'privacy.bullet3':
    'Y si los prendés, solo viaja <b style="color:#eaf2fb;font-weight:700">un hash o una IP</b> — nunca tus archivos.',
  'privacy.card.sub': 'en tu equipo',
  'privacy.card.detail': '0 servidores · 0 cuentas',

  'advanced.label': 'Para power users',
  'advanced.title': 'Mirá debajo del capó',
  'advanced.subtitle': 'Cada conexión, identificada. Cada anomalía, avisada.',
  'advanced.connTitle': 'Conexiones activas por app',
  'advanced.connBody': 'IP, puerto, país y proveedor de cada conexión. <span style="color:#7e93ab">GeoIP opcional.</span>',
  'advanced.connHeaders': '<span>App · IP</span><span>Puerto</span><span>País</span>',
  'advanced.trustTitle': 'Índice de confianza',
  'advanced.trustBody':
    'Verifica la firma Authenticode de cada ejecutable. <span style="display:inline-flex;align-items:center;gap:5px;background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.25);border-radius:6px;padding:2px 7px;font-size:11px;font-weight:700;color:#7cc3f5;font-family:\'JetBrains Mono\',monospace;vertical-align:middle">⊞ Solo Windows</span>',
  'advanced.signed':
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Firmado',
  'advanced.unsigned': '⚠ Sin firma',
  'advanced.anomalyTitle': 'Alertas de anomalías',
  'advanced.anomalyBody': 'Te avisa ante movimientos raros antes de que se hagan un problema.',
  'advanced.anomaly1': 'Pico <b style="color:#fbbf24">≥3×</b> el promedio de una app',
  'advanced.anomaly2': 'App <b style="color:#fbbf24">nueva</b> usando la red',

  'compare.label': 'Comparativa',
  'compare.title': 'Por qué NetGauge',
  'compare.others': 'Otros monitores',
  'compare.r1.label': 'Precio',
  'compare.r1.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Gratis',
  'compare.r1.them': 'Pago o freemium',
  'compare.r2.label': 'Código abierto',
  'compare.r2.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Sí · MIT',
  'compare.r2.them': 'Casi nunca',
  'compare.r3.label': 'Telemetría',
  'compare.r3.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Cero',
  'compare.r3.them': 'A veces',
  'compare.r4.label': 'Windows + macOS',
  'compare.r4.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Ambos',
  'compare.r4.them': 'Según el caso',
  'compare.r5.label': 'Desglose por aplicación',
  'compare.r5.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Sí',
  'compare.r5.them': 'Limitado',

  'download.label': 'Descargar',
  'download.title': 'Descargá NetGauge — gratis.',
  'download.subtitle': 'Sin cuentas, sin pagos. Elegí tu sistema y listo.',
  'download.win': 'Windows 10/11 <span style="color:#62788f;font-family:\'JetBrains Mono\',monospace;font-size:12px">(x64)</span>',
  'download.macArm': 'macOS <span style="color:#62788f;font-family:\'JetBrains Mono\',monospace;font-size:12px">Apple Silicon</span>',
  'download.macIntel': 'macOS <span style="color:#62788f;font-family:\'JetBrains Mono\',monospace;font-size:12px">Intel</span>',
  'download.allReleases': 'Todas las versiones en GitHub Releases ↗',
  'download.acc.summary': '¿Tu sistema muestra un aviso al instalar? Es esperable.',
  'download.acc.toggle': 'abrir ▾',
  'download.acc.body':
    'El instalador todavía <b style="color:#cdddee">no está firmado</b>, así que Windows o Mac pueden mostrar un aviso. Es por la falta de firma, <b style="color:#cdddee">no por riesgo</b>: el código es abierto y lo podés revisar.',
  'download.acc.win': '"Más información" → <b style="color:#eaf2fb">Ejecutar de todas formas</b>',
  'download.acc.mac': 'Click derecho en la app → <b style="color:#eaf2fb">Abrir</b>',

  'faq.label': 'Preguntas',
  'faq.title': 'Lo que te estás preguntando',
  'faq.q1.q': '¿Es gratis?',
  'faq.q1.a': 'Sí, 100% gratis y de código abierto (licencia MIT). Sin cuentas, sin pagos y sin versión "pro".',
  'faq.q2.q': '¿Manda mis datos a algún lado?',
  'faq.q2.a':
    'No. Todo el historial vive local en tu equipo. Las únicas funciones que usan internet (reputación VirusTotal y geolocalización de IPs) son opcionales y vienen apagadas; si las prendés, solo viaja un hash o una IP, nunca tus archivos.',
  'faq.q3.q': '¿Por qué me avisa el sistema al abrirlo?',
  'faq.q3.a':
    'Porque el instalador todavía no está firmado. Es por la falta de firma, no por riesgo: el código es abierto y lo podés revisar. En Windows: "Más información" → Ejecutar de todas formas. En Mac: click derecho → Abrir.',
  'faq.q4.q': '¿Necesito permisos de administrador?',
  'faq.q4.a': 'Para leer el tráfico de red, en la primera ejecución puede pedir permisos elevados. Nada más que eso.',
  'faq.q5.q': '¿Anda en Mac con chip M?',
  'faq.q5.a': 'Sí. Hay un build nativo para Apple Silicon (M1–M4) y otro para Mac con Intel.',
  'faq.q6.q': '¿Corta el internet al llegar a la cuota?',
  'faq.q6.a':
    'No. La cuota te <b style="color:#cdddee">avisa</b> al 80% y al 100%, pero nunca bloquea ni corta la conexión. Vos decidís qué hacer.',

  'cta.title': 'Tomá el control de tu red.<br><span style="color:var(--acc,#22d3ee)">Gratis.</span>',
  'cta.subtitle': 'Open source, sin telemetría y 100% local. Lo instalás en un minuto.',
  'cta.download': 'Descargar gratis',
  'cta.github': 'Ver en GitHub',

  'footer.tagline': 'El monitor de consumo de red por aplicación. Gratis, open source y privado.',
  'footer.noTelemetry': 'Sin telemetría',
  'footer.local': '100% local',
  'footer.project': 'Proyecto',
  'footer.releases': 'Releases',
  'footer.license': 'Licencia MIT',
  'footer.more': 'Más',
  'footer.privacy': 'Privacidad',
  'footer.faq': 'FAQ',
  'footer.kofi': '☕ Invitar un café',
  'footer.copyright': '© 2026 NetGauge · Licencia MIT',
  'footer.madeWith': 'Hecho con software libre (Qt / PySide6)',
};

const en: Dict = {
  'nav.features': 'Features',
  'nav.how': 'How it works',
  'nav.privacy': 'Privacy',
  'nav.faq': 'FAQ',
  'nav.cta': 'Download free',

  'hero.badge': 'Network monitor · Open source',
  'hero.title':
    'Find out which app is <span style="color:var(--acc,#22d3ee);position:relative;white-space:nowrap">eating</span> your internet.',
  'hero.subtitle':
    'Real-time, per-app network usage monitor. Free, open source and private: <span style="color:#cdddee;font-weight:600">your data never leaves your machine</span>. Windows and Mac.',
  'hero.viewGithub': 'View on GitHub',
  'hero.tag1': 'Free',
  'hero.tag2': 'Open source (MIT)',
  'hero.tag3': 'No telemetry',
  'hero.tag4': 'Windows + macOS',

  'mock.tabGlobal': '● Global',
  'mock.tabPerApp': 'Per app',
  'mock.tabConnections': 'Connections',
  'mock.download': '▼ Download',
  'mock.upload': '▲ Upload',
  'mock.total': 'Σ Total',
  'mock.bandwidth': 'Bandwidth · 2 min',
  'mock.peak': 'PEAK 11.7 MB/s',
  'mock.dailyLimit': 'Daily limit · today',
  'mock.monthlyLimit': 'Monthly limit · cycle',

  'trust.label': 'VERIFIABLE:',
  'trust.mit': 'MIT License',
  'trust.github': 'Code on GitHub',
  'trust.windows': '⊞ Windows 10/11',
  'trust.macos': ' macOS Intel + Apple Silicon',
  'trust.local': '100% local',

  'problem.label': 'The problem',
  'problem.title':
    'Your system meter gives you a total.<br><span style="color:#5b7290">Not the culprit.</span>',
  'problem.body':
    'NetGauge shows you the <span style="color:#cdddee;font-weight:600">ranking of apps</span> consuming bandwidth — right now and in your history.',
  'problem.beforeLabel': 'What you see today',
  'problem.beforeCaption': 'Data used this month',
  'problem.beforeMystery': 'Where did it go? A mystery.',
  'problem.afterLabel': 'What you see with NetGauge',

  'features.label': 'Features',
  'features.title': 'Everything your network was hiding',
  'features.subtitle': 'Real per-process measurement. No estimates.',
  'features.f1.title': 'Per-app usage',
  'features.f1.body': 'See exactly how much each program used. Clear ranking, highest to lowest.',
  'features.f2.title': 'Real-time speed',
  'features.f2.body':
    'Instant upload and download (<span style="color:#38bdf8;font-weight:700">↓</span>/<span style="color:#34d399;font-weight:700">↑</span>) with a chart of the last 2 minutes.',
  'features.f3.title': 'Quotas with alerts',
  'features.f3.body':
    'Set a daily or monthly cap. It <span style="color:#cdddee;font-weight:600">warns you at 80% and 100%</span> — it never cuts your connection.',
  'features.f4.title': 'Full history',
  'features.f4.body':
    'Session, day, week or month. All stored <span style="color:#cdddee;font-weight:600">locally</span> on your machine.',
  'features.f5.title': 'Real privacy',
  'features.f5.body':
    'No telemetry. VirusTotal and GeoIP are optional and ship <span style="color:#cdddee;font-weight:600">turned off</span>.',
  'features.f6.title': 'One-click reports',
  'features.f6.body':
    'Export to <span style="color:#cdddee;font-weight:600">CSV, Excel or PDF</span> whenever you need to.',

  'how.label': 'How it works',
  'how.title': 'Ready in three steps',
  'how.s1.title': 'Download and install',
  'how.s1.body': 'Get the installer for Windows or Mac. Lightweight, no hassle.',
  'how.s2.title': 'Lives in your tray',
  'how.s2.body': 'Sits in the system tray with a mini chart. Always at hand, never in the way.',
  'how.s3.title': 'Watch, control and export',
  'how.s3.body': 'Open the panel to see details, set quotas and export reports whenever you want.',

  'privacy.badge': 'PRIVACY',
  'privacy.title': 'Your data is yours.<br>Seriously.',
  'privacy.body':
    'All your history lives <span style="color:#cdddee;font-weight:600">locally</span> on your machine. NetGauge sends nothing to any server. The only features that use the internet are <span style="color:#cdddee;font-weight:600">optional and ship turned off</span>.',
  'privacy.bullet1': '<b style="color:#eaf2fb;font-weight:700">100% local history.</b> Nothing goes to the cloud.',
  'privacy.bullet2':
    '<b style="color:#eaf2fb;font-weight:700">VirusTotal and GeoIP off by default.</b> You decide if you turn them on.',
  'privacy.bullet3':
    "If you do turn them on, only <b style=\"color:#eaf2fb;font-weight:700\">a hash or an IP</b> travels — never your files.",
  'privacy.card.sub': 'on your machine',
  'privacy.card.detail': '0 servers · 0 accounts',

  'advanced.label': 'For power users',
  'advanced.title': 'Look under the hood',
  'advanced.subtitle': 'Every connection, identified. Every anomaly, flagged.',
  'advanced.connTitle': 'Active connections per app',
  'advanced.connBody': 'IP, port, country and provider for every connection. <span style="color:#7e93ab">GeoIP optional.</span>',
  'advanced.connHeaders': '<span>App · IP</span><span>Port</span><span>Country</span>',
  'advanced.trustTitle': 'Trust index',
  'advanced.trustBody':
    'Checks the Authenticode signature of every executable. <span style="display:inline-flex;align-items:center;gap:5px;background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.25);border-radius:6px;padding:2px 7px;font-size:11px;font-weight:700;color:#7cc3f5;font-family:\'JetBrains Mono\',monospace;vertical-align:middle">⊞ Windows only</span>',
  'advanced.signed':
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Signed',
  'advanced.unsigned': '⚠ Unsigned',
  'advanced.anomalyTitle': 'Anomaly alerts',
  'advanced.anomalyBody': 'Warns you about unusual activity before it becomes a problem.',
  'advanced.anomaly1': 'Spike <b style="color:#fbbf24">≥3×</b> an app\'s average',
  'advanced.anomaly2': '<b style="color:#fbbf24">New</b> app using the network',

  'compare.label': 'Comparison',
  'compare.title': 'Why NetGauge',
  'compare.others': 'Other monitors',
  'compare.r1.label': 'Price',
  'compare.r1.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Free',
  'compare.r1.them': 'Paid or freemium',
  'compare.r2.label': 'Open source',
  'compare.r2.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Yes · MIT',
  'compare.r2.them': 'Almost never',
  'compare.r3.label': 'Telemetry',
  'compare.r3.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>None',
  'compare.r3.them': 'Sometimes',
  'compare.r4.label': 'Windows + macOS',
  'compare.r4.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Both',
  'compare.r4.them': 'Depends',
  'compare.r5.label': 'Per-app breakdown',
  'compare.r5.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Yes',
  'compare.r5.them': 'Limited',

  'download.label': 'Download',
  'download.title': 'Download NetGauge — free.',
  'download.subtitle': 'No accounts, no payments. Pick your system and go.',
  'download.win': 'Windows 10/11 <span style="color:#62788f;font-family:\'JetBrains Mono\',monospace;font-size:12px">(x64)</span>',
  'download.macArm': 'macOS <span style="color:#62788f;font-family:\'JetBrains Mono\',monospace;font-size:12px">Apple Silicon</span>',
  'download.macIntel': 'macOS <span style="color:#62788f;font-family:\'JetBrains Mono\',monospace;font-size:12px">Intel</span>',
  'download.allReleases': 'All versions on GitHub Releases ↗',
  'download.acc.summary': 'Does your system show a warning when installing? That\'s expected.',
  'download.acc.toggle': 'open ▾',
  'download.acc.body':
    'The installer isn\'t <b style="color:#cdddee">signed yet</b>, so Windows or Mac may show a warning. It\'s due to the lack of a signature, <b style="color:#cdddee">not a risk</b>: the code is open and you can review it.',
  'download.acc.win': '"More info" → <b style="color:#eaf2fb">Run anyway</b>',
  'download.acc.mac': 'Right-click the app → <b style="color:#eaf2fb">Open</b>',

  'faq.label': 'Questions',
  'faq.title': 'What you\'re probably wondering',
  'faq.q1.q': 'Is it free?',
  'faq.q1.a': 'Yes, 100% free and open source (MIT license). No accounts, no payments, no "pro" tier.',
  'faq.q2.q': 'Does it send my data anywhere?',
  'faq.q2.a':
    'No. All your history lives locally on your machine. The only features that use the internet (VirusTotal reputation and IP geolocation) are optional and ship turned off; if you turn them on, only a hash or an IP travels, never your files.',
  'faq.q3.q': 'Why does my system warn me when I open it?',
  'faq.q3.a':
    'Because the installer isn\'t signed yet. It\'s due to the lack of a signature, not a risk: the code is open and you can review it. On Windows: "More info" → Run anyway. On Mac: right-click → Open.',
  'faq.q4.q': 'Do I need admin permissions?',
  'faq.q4.a': 'To read network traffic, the first run may ask for elevated permissions. Nothing more than that.',
  'faq.q5.q': 'Does it run on Apple Silicon Macs?',
  'faq.q5.a': 'Yes. There\'s a native build for Apple Silicon (M1–M4) and another for Intel Macs.',
  'faq.q6.q': 'Does it cut my internet when I hit the quota?',
  'faq.q6.a':
    'No. The quota <b style="color:#cdddee">warns</b> you at 80% and 100%, but it never blocks or cuts the connection. You decide what to do.',

  'cta.title': 'Take control of your network.<br><span style="color:var(--acc,#22d3ee)">Free.</span>',
  'cta.subtitle': 'Open source, no telemetry and 100% local. Installs in a minute.',
  'cta.download': 'Download free',
  'cta.github': 'View on GitHub',

  'footer.tagline': 'The per-app network usage monitor. Free, open source and private.',
  'footer.noTelemetry': 'No telemetry',
  'footer.local': '100% local',
  'footer.project': 'Project',
  'footer.releases': 'Releases',
  'footer.license': 'MIT License',
  'footer.more': 'More',
  'footer.privacy': 'Privacy',
  'footer.faq': 'FAQ',
  'footer.kofi': '☕ Buy me a coffee',
  'footer.copyright': '© 2026 NetGauge · MIT License',
  'footer.madeWith': 'Made with free software (Qt / PySide6)',
};

const pt: Dict = {
  'nav.features': 'Funcionalidades',
  'nav.how': 'Como funciona',
  'nav.privacy': 'Privacidade',
  'nav.faq': 'FAQ',
  'nav.cta': 'Baixar gratis',

  'hero.badge': 'Monitor de rede · Open source',
  'hero.title':
    'Saiba qual app está <span style="color:var(--acc,#22d3ee);position:relative;white-space:nowrap">consumindo</span> sua internet.',
  'hero.subtitle':
    'Monitor de consumo de rede por aplicativo, em tempo real. Gratuito, de código aberto e privado: <span style="color:#cdddee;font-weight:600">seus dados nunca saem do seu computador</span>. Windows e Mac.',
  'hero.viewGithub': 'Ver no GitHub',
  'hero.tag1': 'Gratuito',
  'hero.tag2': 'Open source (MIT)',
  'hero.tag3': 'Sem telemetria',
  'hero.tag4': 'Windows + macOS',

  'mock.tabGlobal': '● Global',
  'mock.tabPerApp': 'Por aplicativo',
  'mock.tabConnections': 'Conexões',
  'mock.download': '▼ Download',
  'mock.upload': '▲ Upload',
  'mock.total': 'Σ Total',
  'mock.bandwidth': 'Largura de banda · 2 min',
  'mock.peak': 'PICO 11.7 MB/s',
  'mock.dailyLimit': 'Limite diário · hoje',
  'mock.monthlyLimit': 'Limite mensal · ciclo',

  'trust.label': 'VERIFICÁVEL:',
  'trust.mit': 'Licença MIT',
  'trust.github': 'Código no GitHub',
  'trust.windows': '⊞ Windows 10/11',
  'trust.macos': ' macOS Intel + Apple Silicon',
  'trust.local': '100% local',

  'problem.label': 'O problema',
  'problem.title':
    'O medidor do seu sistema te dá um total.<br><span style="color:#5b7290">Não o culpado.</span>',
  'problem.body':
    'O NetGauge mostra o <span style="color:#cdddee;font-weight:600">ranking de apps</span> que consomem — agora e no seu histórico.',
  'problem.beforeLabel': 'O que você vê hoje',
  'problem.beforeCaption': 'Dados usados este mês',
  'problem.beforeMystery': 'De onde veio? Mistério.',
  'problem.afterLabel': 'O que você vê com o NetGauge',

  'features.label': 'Funcionalidades',
  'features.title': 'Tudo que sua rede estava escondendo',
  'features.subtitle': 'Medição real por processo. Nada de estimativas.',
  'features.f1.title': 'Consumo por aplicativo',
  'features.f1.body': 'Veja exatamente quanto cada programa gastou. Ranking claro, do maior ao menor.',
  'features.f2.title': 'Velocidade em tempo real',
  'features.f2.body':
    'Upload e download instantâneos (<span style="color:#38bdf8;font-weight:700">↓</span>/<span style="color:#34d399;font-weight:700">↑</span>) com um gráfico dos últimos 2 minutos.',
  'features.f3.title': 'Cotas com alertas',
  'features.f3.body':
    'Defina um limite diário ou mensal. Ele <span style="color:#cdddee;font-weight:600">avisa em 80% e 100%</span> — nunca corta a conexão.',
  'features.f4.title': 'Histórico completo',
  'features.f4.body':
    'Sessão, dia, semana ou mês. Tudo salvo <span style="color:#cdddee;font-weight:600">localmente</span> no seu computador.',
  'features.f5.title': 'Privacidade real',
  'features.f5.body':
    'Sem telemetria. VirusTotal e GeoIP são opcionais e vêm <span style="color:#cdddee;font-weight:600">desativados</span>.',
  'features.f6.title': 'Relatórios em um clique',
  'features.f6.body':
    'Exporte para <span style="color:#cdddee;font-weight:600">CSV, Excel ou PDF</span> quando precisar.',

  'how.label': 'Como funciona',
  'how.title': 'Pronto em três passos',
  'how.s1.title': 'Baixe e instale',
  'how.s1.body': 'Baixe o instalador para Windows ou Mac. Leve e sem complicação.',
  'how.s2.title': 'Vive na sua bandeja',
  'how.s2.body': 'Fica na bandeja do sistema com um mini-gráfico. Sempre à mão, nunca incomoda.',
  'how.s3.title': 'Veja, controle e exporte',
  'how.s3.body': 'Abra o painel para ver detalhes, definir cotas e exportar relatórios quando quiser.',

  'privacy.badge': 'PRIVACIDADE',
  'privacy.title': 'Seus dados são seus.<br>De verdade.',
  'privacy.body':
    'Todo o histórico vive <span style="color:#cdddee;font-weight:600">localmente</span> no seu computador. O NetGauge não envia nada para nenhum servidor. As únicas funções que usam internet são <span style="color:#cdddee;font-weight:600">opcionais e vêm desativadas</span>.',
  'privacy.bullet1': '<b style="color:#eaf2fb;font-weight:700">Histórico 100% local.</b> Nada sobe para a nuvem.',
  'privacy.bullet2':
    '<b style="color:#eaf2fb;font-weight:700">VirusTotal e GeoIP desativados.</b> Você decide se ativa.',
  'privacy.bullet3':
    'E se você ativar, só viaja <b style="color:#eaf2fb;font-weight:700">um hash ou um IP</b> — nunca seus arquivos.',
  'privacy.card.sub': 'no seu computador',
  'privacy.card.detail': '0 servidores · 0 contas',

  'advanced.label': 'Para usuários avançados',
  'advanced.title': 'Veja por debaixo do capô',
  'advanced.subtitle': 'Cada conexão, identificada. Cada anomalia, avisada.',
  'advanced.connTitle': 'Conexões ativas por app',
  'advanced.connBody': 'IP, porta, país e provedor de cada conexão. <span style="color:#7e93ab">GeoIP opcional.</span>',
  'advanced.connHeaders': '<span>App · IP</span><span>Porta</span><span>País</span>',
  'advanced.trustTitle': 'Índice de confiança',
  'advanced.trustBody':
    'Verifica a assinatura Authenticode de cada executável. <span style="display:inline-flex;align-items:center;gap:5px;background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.25);border-radius:6px;padding:2px 7px;font-size:11px;font-weight:700;color:#7cc3f5;font-family:\'JetBrains Mono\',monospace;vertical-align:middle">⊞ Somente Windows</span>',
  'advanced.signed':
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Assinado',
  'advanced.unsigned': '⚠ Sem assinatura',
  'advanced.anomalyTitle': 'Alertas de anomalias',
  'advanced.anomalyBody': 'Avisa sobre movimentos estranhos antes que se tornem um problema.',
  'advanced.anomaly1': 'Pico <b style="color:#fbbf24">≥3×</b> a média de um app',
  'advanced.anomaly2': 'App <b style="color:#fbbf24">novo</b> usando a rede',

  'compare.label': 'Comparativo',
  'compare.title': 'Por que o NetGauge',
  'compare.others': 'Outros monitores',
  'compare.r1.label': 'Preço',
  'compare.r1.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Gratuito',
  'compare.r1.them': 'Pago ou freemium',
  'compare.r2.label': 'Código aberto',
  'compare.r2.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Sim · MIT',
  'compare.r2.them': 'Quase nunca',
  'compare.r3.label': 'Telemetria',
  'compare.r3.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Zero',
  'compare.r3.them': 'Às vezes',
  'compare.r4.label': 'Windows + macOS',
  'compare.r4.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Ambos',
  'compare.r4.them': 'Depende do caso',
  'compare.r5.label': 'Detalhamento por aplicativo',
  'compare.r5.us': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Sim',
  'compare.r5.them': 'Limitado',

  'download.label': 'Baixar',
  'download.title': 'Baixe o NetGauge — gratuito.',
  'download.subtitle': 'Sem contas, sem pagamentos. Escolha seu sistema e pronto.',
  'download.win': 'Windows 10/11 <span style="color:#62788f;font-family:\'JetBrains Mono\',monospace;font-size:12px">(x64)</span>',
  'download.macArm': 'macOS <span style="color:#62788f;font-family:\'JetBrains Mono\',monospace;font-size:12px">Apple Silicon</span>',
  'download.macIntel': 'macOS <span style="color:#62788f;font-family:\'JetBrains Mono\',monospace;font-size:12px">Intel</span>',
  'download.allReleases': 'Todas as versões no GitHub Releases ↗',
  'download.acc.summary': 'Seu sistema mostra um aviso ao instalar? É esperado.',
  'download.acc.toggle': 'abrir ▾',
  'download.acc.body':
    'O instalador ainda <b style="color:#cdddee">não está assinado</b>, então Windows ou Mac podem mostrar um aviso. É pela falta de assinatura, <b style="color:#cdddee">não por risco</b>: o código é aberto e você pode revisá-lo.',
  'download.acc.win': '"Mais informações" → <b style="color:#eaf2fb">Executar assim mesmo</b>',
  'download.acc.mac': 'Clique com o botão direito no app → <b style="color:#eaf2fb">Abrir</b>',

  'faq.label': 'Perguntas',
  'faq.title': 'O que você deve estar se perguntando',
  'faq.q1.q': 'É gratuito?',
  'faq.q1.a': 'Sim, 100% gratuito e de código aberto (licença MIT). Sem contas, sem pagamentos e sem versão "pro".',
  'faq.q2.q': 'Ele envia meus dados para algum lugar?',
  'faq.q2.a':
    'Não. Todo o histórico vive localmente no seu computador. As únicas funções que usam internet (reputação VirusTotal e geolocalização de IPs) são opcionais e vêm desativadas; se você as ativar, só viaja um hash ou um IP, nunca seus arquivos.',
  'faq.q3.q': 'Por que o sistema me avisa ao abrir?',
  'faq.q3.a':
    'Porque o instalador ainda não está assinado. É pela falta de assinatura, não por risco: o código é aberto e você pode revisá-lo. No Windows: "Mais informações" → Executar assim mesmo. No Mac: clique direito → Abrir.',
  'faq.q4.q': 'Preciso de permissões de administrador?',
  'faq.q4.a': 'Para ler o tráfego de rede, na primeira execução pode pedir permissões elevadas. Nada além disso.',
  'faq.q5.q': 'Funciona em Mac com chip M?',
  'faq.q5.a': 'Sim. Há um build nativo para Apple Silicon (M1–M4) e outro para Mac com Intel.',
  'faq.q6.q': 'Corta a internet ao chegar na cota?',
  'faq.q6.a':
    'Não. A cota <b style="color:#cdddee">avisa</b> em 80% e 100%, mas nunca bloqueia ou corta a conexão. Você decide o que fazer.',

  'cta.title': 'Assuma o controle da sua rede.<br><span style="color:var(--acc,#22d3ee)">Gratuito.</span>',
  'cta.subtitle': 'Open source, sem telemetria e 100% local. Você instala em um minuto.',
  'cta.download': 'Baixar gratis',
  'cta.github': 'Ver no GitHub',

  'footer.tagline': 'O monitor de consumo de rede por aplicativo. Gratuito, open source e privado.',
  'footer.noTelemetry': 'Sem telemetria',
  'footer.local': '100% local',
  'footer.project': 'Projeto',
  'footer.releases': 'Releases',
  'footer.license': 'Licença MIT',
  'footer.more': 'Mais',
  'footer.privacy': 'Privacidade',
  'footer.faq': 'FAQ',
  'footer.kofi': '☕ Pague um café',
  'footer.copyright': '© 2026 NetGauge · Licença MIT',
  'footer.madeWith': 'Feito com software livre (Qt / PySide6)',
};

export const dictionaries: Record<Lang, Dict> = { es, en, pt };

/** Detecta el idioma inicial: localStorage > navigator.language > default ES. */
export function detectInitialLang(): Lang {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && LANGS.includes(stored as Lang)) return stored as Lang;
  } catch {
    /* localStorage puede no estar disponible (modo privado, SSR, etc.) */
  }
  try {
    const nav = (navigator.language || '').toLowerCase();
    if (nav.startsWith('es')) return 'es';
    if (nav.startsWith('pt')) return 'pt';
    if (nav.startsWith('en')) return 'en';
  } catch {
    /* noop */
  }
  return DEFAULT_LANG;
}

export function persistLang(lang: Lang): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* noop */
  }
}

/** Aplica el diccionario del idioma a todos los nodos `data-i18n[-html]` del root. */
export function applyLang(root: HTMLElement, lang: Lang): void {
  const dict = dictionaries[lang];

  root.querySelectorAll<HTMLElement>('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (key && dict[key] !== undefined) el.textContent = dict[key];
  });

  root.querySelectorAll<HTMLElement>('[data-i18n-html]').forEach((el) => {
    const key = el.getAttribute('data-i18n-html');
    if (key && dict[key] !== undefined) el.innerHTML = dict[key];
  });

  // Switcher: estado visual + aria-pressed por idioma activo.
  root.querySelectorAll<HTMLElement>('[data-lang-btn]').forEach((btn) => {
    const isActive = btn.getAttribute('data-lang-btn') === lang;
    btn.setAttribute('aria-pressed', String(isActive));
    btn.style.background = isActive ? 'rgba(34,211,238,.14)' : 'transparent';
    btn.style.color = isActive ? '#22d3ee' : '#9db1c9';
  });

  document.documentElement.lang = lang;
  document.title = meta[lang].title;
  const descTag = document.querySelector('meta[name="description"]');
  if (descTag) descTag.setAttribute('content', meta[lang].description);
  const ogDesc = document.querySelector('meta[property="og:description"]');
  if (ogDesc) ogDesc.setAttribute('content', meta[lang].description);
  const twDesc = document.querySelector('meta[name="twitter:description"]');
  if (twDesc) twDesc.setAttribute('content', meta[lang].description);
  const ogTitle = document.querySelector('meta[property="og:title"]');
  if (ogTitle) ogTitle.setAttribute('content', meta[lang].title);
  const twTitle = document.querySelector('meta[name="twitter:title"]');
  if (twTitle) twTitle.setAttribute('content', meta[lang].title);
}

/** Bindea los 3 botones del switcher: click + Enter/Space (accesible por teclado). */
export function bindLangSwitcher(root: HTMLElement, onChange: (lang: Lang) => void): void {
  root.querySelectorAll<HTMLButtonElement>('[data-lang-btn]').forEach((btn) => {
    const lang = btn.getAttribute('data-lang-btn') as Lang | null;
    if (!lang || !LANGS.includes(lang)) return;
    btn.addEventListener('click', () => onChange(lang));
  });
}
