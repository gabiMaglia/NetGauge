/**
 * Copy ES/EN/PT de la landing. Es la única fuente de texto: el prerender
 * (build/prerender.ts) lo vuelca en el HTML estático de cada ruta; el runtime
 * del navegador no carga diccionarios, solo las pocas cadenas que `renderBody` embebe en `#ng-rt`.
 */

import type { Lang } from './lang.ts';

export type OsKey = 'windows' | 'mac' | 'other';

/** Labels del CTA principal según el SO detectado. En iOS/Android se usa `share.*`. */
export const osLabels: Record<Lang, Record<OsKey, { label: string; sub: string }>> = {
  es: {
    windows: { label: 'Descargar para Windows', sub: 'Windows 10/11 · 64-bit' },
    mac: { label: 'Descargar para macOS', sub: 'Elegí Intel o Apple Silicon ↓' },
    other: { label: 'Descargar gratis', sub: 'Windows y macOS' },
  },
  en: {
    windows: { label: 'Download for Windows', sub: 'Windows 10/11 · 64-bit' },
    mac: { label: 'Download for macOS', sub: 'Choose Intel or Apple Silicon ↓' },
    other: { label: 'Download for free', sub: 'Windows and macOS' },
  },
  pt: {
    windows: { label: 'Baixar para Windows', sub: 'Windows 10/11 · 64-bit' },
    mac: { label: 'Baixar para macOS', sub: 'Escolha Intel ou Apple Silicon ↓' },
    other: { label: 'Baixar grátis', sub: 'Windows e macOS' },
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
  'hero.live': 'EN VIVO',
  'hero.title':
    'Sabé qué app se está <span style="color:var(--acc,#458bf8);position:relative;white-space:nowrap">comiendo</span> tu internet.',
  'hero.subtitle':
    'Monitor de consumo de red por aplicación, en tiempo real. Gratis, de código abierto y privado: <span style="color:#cdddee;font-weight:600">tu historial de uso nunca sale de tu equipo</span>. Windows y Mac.',
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
  'trust.local': 'Historial 100% local',

  'problem.label': 'El problema',
  'problem.title':
    'El medidor de tu sistema te da un total.<br><span style="color:#7e93ab">No el culpable.</span>',
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
    'Sin telemetría ni cuentas. VirusTotal y GeoIP son opcionales y vienen <span style="color:#cdddee;font-weight:600">apagados</span>.',
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
    'Sin telemetría ni cuentas. Tu historial vive <span style="color:#cdddee;font-weight:600">local</span> en tu equipo. Solo consulta GitHub para avisarte de versiones nuevas (se puede apagar en Ajustes). <span style="color:#cdddee;font-weight:600">VirusTotal y GeoIP son opcionales y vienen apagados.</span>',
  'privacy.bullet1':
    '<b style="color:#eaf2fb;font-weight:700">Historial 100% local.</b> Nada sube a la nube.',
  'privacy.bullet2':
    '<b style="color:#eaf2fb;font-weight:700">Un solo aviso a GitHub.</b> Una consulta de solo lectura para saber si hay una versión nueva, sin datos de uso. Se apaga en Ajustes.',
  'privacy.bullet3':
    'VirusTotal y GeoIP vienen <b style="color:#eaf2fb;font-weight:700">apagados</b>. Si los prendés, viaja <b style="color:#eaf2fb;font-weight:700">el hash SHA-256</b> del ejecutable o <b style="color:#eaf2fb;font-weight:700">la IP remota</b> (GeoIP usa HTTP sin cifrar) — nunca tus archivos.',
  'privacy.card.sub': 'de tu historial, en tu equipo',
  'privacy.card.detail': 'Sin telemetría · 0 cuentas',

  'advanced.label': 'Para power users',
  'advanced.title': 'Mirá debajo del capó',
  'advanced.subtitle': 'Cada conexión, identificada. Cada anomalía, avisada.',
  'advanced.connTitle': 'Conexiones activas por app',
  'advanced.connBody':
    'IP, puerto, país y proveedor de cada conexión. <span style="color:#7e93ab">GeoIP opcional.</span>',
  'advanced.connHeaders': '<span>App · IP</span><span>Puerto</span><span>País</span>',
  'advanced.trustTitle': 'Índice de confianza',
  'advanced.trustBody':
    'Verifica la firma Authenticode de cada ejecutable. <span style="display:inline-flex;align-items:center;gap:5px;background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.25);border-radius:6px;padding:2px 7px;font-size:12px;font-weight:700;color:#7cc3f5;font-family:\'JetBrains Mono\',monospace;vertical-align:middle">⊞ Solo Windows</span>',
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
  'compare.r1.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Gratis',
  'compare.r1.them': 'Pago o freemium',
  'compare.r2.label': 'Código abierto',
  'compare.r2.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Sí · MIT',
  'compare.r2.them': 'Casi nunca',
  'compare.r3.label': 'Telemetría',
  'compare.r3.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Cero',
  'compare.r3.them': 'A veces',
  'compare.r4.label': 'Windows + macOS',
  'compare.r4.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Ambos',
  'compare.r4.them': 'Según el caso',
  'compare.r5.label': 'Desglose por aplicación',
  'compare.r5.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Sí',
  'compare.r5.them': 'Limitado',

  'download.label': 'Descargar',
  'download.title': 'Descargá NetGauge — gratis.',
  'download.subtitle': 'Sin cuentas, sin pagos. Elegí tu sistema y listo.',
  'download.win':
    'Windows 10/11 <span style="color:#7e93ab;font-family:\'JetBrains Mono\',monospace;font-size:12px">(x64)</span>',
  'download.macArm':
    'macOS <span style="color:#7e93ab;font-family:\'JetBrains Mono\',monospace;font-size:12px">Apple Silicon</span>',
  'download.macIntel':
    'macOS <span style="color:#7e93ab;font-family:\'JetBrains Mono\',monospace;font-size:12px">Intel</span>',
  'download.allReleases': 'Todas las versiones en GitHub Releases ↗',
  'download.acc.summary': 'Windows puede mostrar un aviso al instalar. Es esperable.',
  'download.acc.toggle': 'abrir ▾',
  'download.acc.body':
    'El instalador de Windows (.exe) <b style="color:#cdddee">todavía no está firmado</b>, así que SmartScreen puede mostrar un aviso. Es por la falta de firma, <b style="color:#cdddee">no por riesgo</b>: el código es abierto y lo podés revisar.',
  'download.acc.win':
    '"Más información" → <b style="color:#eaf2fb;font-weight:700">Ejecutar de todas formas</b>',
  'download.acc.mac':
    '<b style="color:#eaf2fb;font-weight:700">Firmado y notarizado por Apple</b> (desde la v2.0.2): el .dmg abre sin avisos.',

  'faq.label': 'Preguntas',
  'faq.title': 'Lo que te estás preguntando',
  'faq.q1.q': '¿Es gratis?',
  'faq.q1.a':
    'Sí, 100% gratis y de código abierto (licencia MIT). Sin cuentas, sin pagos y sin versión "pro".',
  'faq.q2.q': '¿Manda mis datos a algún lado?',
  'faq.q2.a':
    'No manda tu historial ni usa cuentas: no hay telemetría. Solo consulta GitHub para avisarte de versiones nuevas (se puede apagar en Ajustes). La reputación de VirusTotal y la geolocalización de IPs son opcionales y vienen apagadas; si las prendés, solo viaja un hash o una IP, nunca tus archivos. <a href="https://github.com/gabiMaglia/NetGauge/blob/main/PRIVACY.md" target="_blank" rel="noopener" class="ng-inline-link">Detalle completo en la política de privacidad ↗</a>',
  'faq.q3.q': '¿Por qué Windows me avisa al abrirlo?',
  'faq.q3.a':
    'En Windows el instalador (.exe) todavía no está firmado, así que SmartScreen puede mostrar un aviso: tocá "Más información" → "Ejecutar de todas formas". Es por la falta de firma, no por riesgo: el código es abierto y lo podés revisar (<a href="https://github.com/gabiMaglia/NetGauge#code-signing-policy" target="_blank" rel="noopener" class="ng-inline-link">Code signing policy</a>). En macOS el .dmg está firmado y notarizado por Apple (desde la v2.0.2) y abre sin avisos.',
  'faq.q4.q': '¿Necesito permisos de administrador?',
  'faq.q4.a':
    'Para leer el tráfico de red, en la primera ejecución puede pedir permisos elevados. Nada más que eso.',
  'faq.q5.q': '¿Anda en Mac con chip M?',
  'faq.q5.a': 'Sí. Hay un build nativo para Apple Silicon (M1–M4) y otro para Mac con Intel.',
  'faq.q6.q': '¿Corta el internet al llegar a la cuota?',
  'faq.q6.a':
    'No. La cuota te <b style="color:#cdddee">avisa</b> al 80% y al 100%, pero nunca bloquea ni corta la conexión. Vos decidís qué hacer.',

  'cta.title': 'Tomá el control de tu red.<br><span style="color:var(--acc,#458bf8)">Gratis.</span>',
  'cta.subtitle': 'Open source, sin telemetría ni cuentas. Lo instalás en un minuto.',
  'cta.download': 'Descargar gratis',
  'cta.github': 'Ver en GitHub',

  'footer.tagline': 'El monitor de consumo de red por aplicación. Gratis, open source y privado.',
  'footer.noTelemetry': 'Sin telemetría',
  'footer.local': 'Historial local',
  'footer.project': 'Proyecto',
  'footer.releases': 'Releases',
  'footer.license': 'Licencia MIT',
  'footer.more': 'Más',
  'footer.privacy': 'Privacidad',
  'footer.faq': 'FAQ',
  'footer.kofi': '☕ Invitar un café',
  'footer.copyright': '© 2026 NetGauge · Licencia MIT',
  'footer.madeWith': 'Hecho con software libre (Qt / PySide6)',

  'a11y.skip': 'Saltar al contenido',

  'nav.main': 'Principal',
  'nav.menu': 'Menú',

  'lang.group': 'Idioma',
  'lang.es': 'Español',
  'lang.en': 'English',
  'lang.pt': 'Português',

  'mock.alt':
    'Vista previa de NetGauge: velocidad de bajada y subida en vivo, gráfico de ancho de banda de los últimos 2 minutos y límites de consumo diario y mensual.',

  'privacy.link': 'Leer la política de privacidad completa ↗',

  'download.acc.winPolicy': 'Ver la Code signing policy ↗',
  'download.fallbackHint':
    'Si un botón te lleva a la página de GitHub Releases, elegí ahí el archivo de tu sistema.',
  'download.suggested': 'Sugerido',

  'footer.privacyPolicy': 'Política de privacidad ↗',
  'footer.nav': 'Enlaces del pie',

  'share.cta': 'Enviame el link',
  'share.sub': 'Para abrirlo en tu computadora',
  'share.note': 'NetGauge es para Windows y macOS; abrilo desde tu computadora.',
  'share.copied': 'Link copiado. Pegalo en tu computadora.',
  'share.subject': 'NetGauge: monitor de red por aplicación',
  'share.text': 'NetGauge mide cuánto consume cada app. Es para Windows y macOS, gratis y open source:',

  'noscript.text': 'Descargá NetGauge (Windows y macOS) desde',
  'noscript.link': 'GitHub Releases',

  'os.other.label': 'Descargar gratis',
  'os.other.sub': 'Windows y macOS',
};

const en: Dict = {
  'nav.features': 'Features',
  'nav.how': 'How it works',
  'nav.privacy': 'Privacy',
  'nav.faq': 'FAQ',
  'nav.cta': 'Download free',

  'hero.badge': 'Network monitor · Open source',
  'hero.live': 'LIVE',
  'hero.title':
    'Find out which app is <span style="color:var(--acc,#458bf8);position:relative;white-space:nowrap">eating</span> your internet.',
  'hero.subtitle':
    'Real-time, per-app network usage monitor. Free, open source and private: <span style="color:#cdddee;font-weight:600">your usage history never leaves your machine</span>. Windows and Mac.',
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
  'trust.local': '100% local history',

  'problem.label': 'The problem',
  'problem.title':
    'Your system meter gives you a total.<br><span style="color:#7e93ab">Not the culprit.</span>',
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
    'No telemetry, no accounts. VirusTotal and GeoIP are optional and ship <span style="color:#cdddee;font-weight:600">turned off</span>.',
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
    'No telemetry, no accounts. Your history lives <span style="color:#cdddee;font-weight:600">locally</span> on your machine. It only checks GitHub to tell you about new versions (you can turn that off in Settings). <span style="color:#cdddee;font-weight:600">VirusTotal and GeoIP are optional and ship turned off.</span>',
  'privacy.bullet1':
    '<b style="color:#eaf2fb;font-weight:700">100% local history.</b> Nothing goes to the cloud.',
  'privacy.bullet2':
    '<b style="color:#eaf2fb;font-weight:700">One GitHub check.</b> A read-only request to see if a newer version exists, with no usage data. Turn it off in Settings.',
  'privacy.bullet3':
    'VirusTotal and GeoIP ship <b style="color:#eaf2fb;font-weight:700">off</b>. If you turn them on, only <b style="color:#eaf2fb;font-weight:700">an executable\'s SHA-256 hash</b> or <b style="color:#eaf2fb;font-weight:700">a remote IP</b> is sent (GeoIP uses unencrypted HTTP) — never your files.',
  'privacy.card.sub': 'of your history, on your machine',
  'privacy.card.detail': 'No telemetry · 0 accounts',

  'advanced.label': 'For power users',
  'advanced.title': 'Look under the hood',
  'advanced.subtitle': 'Every connection, identified. Every anomaly, flagged.',
  'advanced.connTitle': 'Active connections per app',
  'advanced.connBody':
    'IP, port, country and provider for every connection. <span style="color:#7e93ab">GeoIP optional.</span>',
  'advanced.connHeaders': '<span>App · IP</span><span>Port</span><span>Country</span>',
  'advanced.trustTitle': 'Trust index',
  'advanced.trustBody':
    'Checks the Authenticode signature of every executable. <span style="display:inline-flex;align-items:center;gap:5px;background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.25);border-radius:6px;padding:2px 7px;font-size:12px;font-weight:700;color:#7cc3f5;font-family:\'JetBrains Mono\',monospace;vertical-align:middle">⊞ Windows only</span>',
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
  'compare.r1.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Free',
  'compare.r1.them': 'Paid or freemium',
  'compare.r2.label': 'Open source',
  'compare.r2.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Yes · MIT',
  'compare.r2.them': 'Almost never',
  'compare.r3.label': 'Telemetry',
  'compare.r3.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>None',
  'compare.r3.them': 'Sometimes',
  'compare.r4.label': 'Windows + macOS',
  'compare.r4.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Both',
  'compare.r4.them': 'Depends',
  'compare.r5.label': 'Per-app breakdown',
  'compare.r5.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Yes',
  'compare.r5.them': 'Limited',

  'download.label': 'Download',
  'download.title': 'Download NetGauge — free.',
  'download.subtitle': 'No accounts, no payments. Pick your system and go.',
  'download.win':
    'Windows 10/11 <span style="color:#7e93ab;font-family:\'JetBrains Mono\',monospace;font-size:12px">(x64)</span>',
  'download.macArm':
    'macOS <span style="color:#7e93ab;font-family:\'JetBrains Mono\',monospace;font-size:12px">Apple Silicon</span>',
  'download.macIntel':
    'macOS <span style="color:#7e93ab;font-family:\'JetBrains Mono\',monospace;font-size:12px">Intel</span>',
  'download.allReleases': 'All versions on GitHub Releases ↗',
  'download.acc.summary': 'Windows may show a warning when installing. That\'s expected.',
  'download.acc.toggle': 'open ▾',
  'download.acc.body':
    'The Windows installer (.exe) is <b style="color:#cdddee">not signed yet</b>, so SmartScreen may show a warning. It\'s due to the lack of a signature, <b style="color:#cdddee">not a risk</b>: the code is open and you can review it.',
  'download.acc.win': '"More info" → <b style="color:#eaf2fb;font-weight:700">Run anyway</b>',
  'download.acc.mac':
    '<b style="color:#eaf2fb;font-weight:700">Signed and notarized by Apple</b> (since v2.0.2): the .dmg opens with no warnings.',

  'faq.label': 'Questions',
  'faq.title': 'What you\'re probably wondering',
  'faq.q1.q': 'Is it free?',
  'faq.q1.a': 'Yes, 100% free and open source (MIT license). No accounts, no payments, no "pro" tier.',
  'faq.q2.q': 'Does it send my data anywhere?',
  'faq.q2.a':
    'It doesn\'t send your history and has no accounts or telemetry. It only checks GitHub to tell you about new versions (you can turn that off in Settings). VirusTotal reputation and IP geolocation are optional and off by default; if you turn them on, only a hash or an IP is sent, never your files. <a href="https://github.com/gabiMaglia/NetGauge/blob/main/PRIVACY.md" target="_blank" rel="noopener" class="ng-inline-link">Full details in the privacy policy ↗</a>',
  'faq.q3.q': 'Why does Windows warn me when I open it?',
  'faq.q3.a':
    'On Windows the installer (.exe) isn\'t signed yet, so SmartScreen may show a warning: click "More info" → "Run anyway". It\'s due to the lack of a signature, not a risk: the code is open and you can review it (<a href="https://github.com/gabiMaglia/NetGauge#code-signing-policy" target="_blank" rel="noopener" class="ng-inline-link">Code signing policy</a>). On macOS the .dmg is signed and notarized by Apple (since v2.0.2) and opens with no warnings.',
  'faq.q4.q': 'Do I need admin permissions?',
  'faq.q4.a':
    'To read network traffic, the first run may ask for elevated permissions. Nothing more than that.',
  'faq.q5.q': 'Does it run on Apple Silicon Macs?',
  'faq.q5.a': 'Yes. There\'s a native build for Apple Silicon (M1–M4) and another for Intel Macs.',
  'faq.q6.q': 'Does it cut my internet when I hit the quota?',
  'faq.q6.a':
    'No. The quota <b style="color:#cdddee">warns</b> you at 80% and 100%, but it never blocks or cuts the connection. You decide what to do.',

  'cta.title': 'Take control of your network.<br><span style="color:var(--acc,#458bf8)">Free.</span>',
  'cta.subtitle': 'Open source, no telemetry, no accounts. Installs in a minute.',
  'cta.download': 'Download free',
  'cta.github': 'View on GitHub',

  'footer.tagline': 'The per-app network usage monitor. Free, open source and private.',
  'footer.noTelemetry': 'No telemetry',
  'footer.local': 'Local history',
  'footer.project': 'Project',
  'footer.releases': 'Releases',
  'footer.license': 'MIT License',
  'footer.more': 'More',
  'footer.privacy': 'Privacy',
  'footer.faq': 'FAQ',
  'footer.kofi': '☕ Buy me a coffee',
  'footer.copyright': '© 2026 NetGauge · MIT License',
  'footer.madeWith': 'Made with free software (Qt / PySide6)',

  'a11y.skip': 'Skip to content',

  'nav.main': 'Main',
  'nav.menu': 'Menu',

  'lang.group': 'Language',
  'lang.es': 'Español',
  'lang.en': 'English',
  'lang.pt': 'Português',

  'mock.alt':
    'NetGauge preview: live download and upload speed, a 2-minute bandwidth chart and daily and monthly usage limits.',

  'privacy.link': 'Read the full privacy policy ↗',

  'download.acc.winPolicy': 'See the Code signing policy ↗',
  'download.fallbackHint':
    'If a button takes you to the GitHub Releases page, pick the file for your system there.',
  'download.suggested': 'Suggested',

  'footer.privacyPolicy': 'Privacy policy ↗',
  'footer.nav': 'Footer links',

  'share.cta': 'Send me the link',
  'share.sub': 'To open it on your computer',
  'share.note': 'NetGauge is for Windows and macOS; open it from your computer.',
  'share.copied': 'Link copied. Paste it on your computer.',
  'share.subject': 'NetGauge: per-app network monitor',
  'share.text': 'NetGauge shows how much each app uses. For Windows and macOS, free and open source:',

  'noscript.text': 'Download NetGauge (Windows and macOS) from',
  'noscript.link': 'GitHub Releases',

  'os.other.label': 'Download for free',
  'os.other.sub': 'Windows and macOS',
};

const pt: Dict = {
  'nav.features': 'Funcionalidades',
  'nav.how': 'Como funciona',
  'nav.privacy': 'Privacidade',
  'nav.faq': 'FAQ',
  'nav.cta': 'Baixar gratis',

  'hero.badge': 'Monitor de rede · Open source',
  'hero.live': 'AO VIVO',
  'hero.title':
    'Saiba qual app está <span style="color:var(--acc,#458bf8);position:relative;white-space:nowrap">consumindo</span> sua internet.',
  'hero.subtitle':
    'Monitor de consumo de rede por aplicativo, em tempo real. Gratuito, de código aberto e privado: <span style="color:#cdddee;font-weight:600">seu histórico de uso nunca sai do seu computador</span>. Windows e Mac.',
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
  'trust.local': 'Histórico 100% local',

  'problem.label': 'O problema',
  'problem.title':
    'O medidor do seu sistema te dá um total.<br><span style="color:#7e93ab">Não o culpado.</span>',
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
    'Sem telemetria nem contas. VirusTotal e GeoIP são opcionais e vêm <span style="color:#cdddee;font-weight:600">desativados</span>.',
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
    'Sem telemetria nem contas. Seu histórico fica <span style="color:#cdddee;font-weight:600">local</span> no seu computador. Só consulta o GitHub para avisar sobre versões novas (dá para desativar em Configurações). <span style="color:#cdddee;font-weight:600">VirusTotal e GeoIP são opcionais e vêm desativados.</span>',
  'privacy.bullet1':
    '<b style="color:#eaf2fb;font-weight:700">Histórico 100% local.</b> Nada sobe para a nuvem.',
  'privacy.bullet2':
    '<b style="color:#eaf2fb;font-weight:700">Uma consulta ao GitHub.</b> Uma requisição somente leitura para ver se há versão nova, sem dados de uso. Desative em Configurações.',
  'privacy.bullet3':
    'VirusTotal e GeoIP vêm <b style="color:#eaf2fb;font-weight:700">desativados</b>. Se você ativar, viaja <b style="color:#eaf2fb;font-weight:700">o hash SHA-256</b> do executável ou <b style="color:#eaf2fb;font-weight:700">o IP remoto</b> (o GeoIP usa HTTP sem criptografia) — nunca seus arquivos.',
  'privacy.card.sub': 'do seu histórico, no seu computador',
  'privacy.card.detail': 'Sem telemetria · 0 contas',

  'advanced.label': 'Para usuários avançados',
  'advanced.title': 'Veja por debaixo do capô',
  'advanced.subtitle': 'Cada conexão, identificada. Cada anomalia, avisada.',
  'advanced.connTitle': 'Conexões ativas por app',
  'advanced.connBody':
    'IP, porta, país e provedor de cada conexão. <span style="color:#7e93ab">GeoIP opcional.</span>',
  'advanced.connHeaders': '<span>App · IP</span><span>Porta</span><span>País</span>',
  'advanced.trustTitle': 'Índice de confiança',
  'advanced.trustBody':
    'Verifica a assinatura Authenticode de cada executável. <span style="display:inline-flex;align-items:center;gap:5px;background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.25);border-radius:6px;padding:2px 7px;font-size:12px;font-weight:700;color:#7cc3f5;font-family:\'JetBrains Mono\',monospace;vertical-align:middle">⊞ Somente Windows</span>',
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
  'compare.r1.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Gratuito',
  'compare.r1.them': 'Pago ou freemium',
  'compare.r2.label': 'Código aberto',
  'compare.r2.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Sim · MIT',
  'compare.r2.them': 'Quase nunca',
  'compare.r3.label': 'Telemetria',
  'compare.r3.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Zero',
  'compare.r3.them': 'Às vezes',
  'compare.r4.label': 'Windows + macOS',
  'compare.r4.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Ambos',
  'compare.r4.them': 'Depende do caso',
  'compare.r5.label': 'Detalhamento por aplicativo',
  'compare.r5.us':
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 6"/></svg>Sim',
  'compare.r5.them': 'Limitado',

  'download.label': 'Baixar',
  'download.title': 'Baixe o NetGauge — gratuito.',
  'download.subtitle': 'Sem contas, sem pagamentos. Escolha seu sistema e pronto.',
  'download.win':
    'Windows 10/11 <span style="color:#7e93ab;font-family:\'JetBrains Mono\',monospace;font-size:12px">(x64)</span>',
  'download.macArm':
    'macOS <span style="color:#7e93ab;font-family:\'JetBrains Mono\',monospace;font-size:12px">Apple Silicon</span>',
  'download.macIntel':
    'macOS <span style="color:#7e93ab;font-family:\'JetBrains Mono\',monospace;font-size:12px">Intel</span>',
  'download.allReleases': 'Todas as versões no GitHub Releases ↗',
  'download.acc.summary': 'O Windows pode mostrar um aviso ao instalar. É esperado.',
  'download.acc.toggle': 'abrir ▾',
  'download.acc.body':
    'O instalador do Windows (.exe) <b style="color:#cdddee">ainda não está assinado</b>, então o SmartScreen pode mostrar um aviso. É pela falta de assinatura, <b style="color:#cdddee">não por risco</b>: o código é aberto e você pode revisá-lo.',
  'download.acc.win':
    '"Mais informações" → <b style="color:#eaf2fb;font-weight:700">Executar assim mesmo</b>',
  'download.acc.mac':
    '<b style="color:#eaf2fb;font-weight:700">Assinado e notarizado pela Apple</b> (desde a v2.0.2): o .dmg abre sem avisos.',

  'faq.label': 'Perguntas',
  'faq.title': 'O que você deve estar se perguntando',
  'faq.q1.q': 'É gratuito?',
  'faq.q1.a':
    'Sim, 100% gratuito e de código aberto (licença MIT). Sem contas, sem pagamentos e sem versão "pro".',
  'faq.q2.q': 'Ele envia meus dados para algum lugar?',
  'faq.q2.a':
    'Não envia seu histórico nem usa contas: não há telemetria. Só consulta o GitHub para avisar sobre versões novas (dá para desativar em Configurações). A reputação do VirusTotal e a geolocalização de IPs são opcionais e vêm desativadas; se você as ativar, só viaja um hash ou um IP, nunca seus arquivos. <a href="https://github.com/gabiMaglia/NetGauge/blob/main/PRIVACY.md" target="_blank" rel="noopener" class="ng-inline-link">Detalhes completos na política de privacidade ↗</a>',
  'faq.q3.q': 'Por que o Windows me avisa ao abrir?',
  'faq.q3.a':
    'No Windows o instalador (.exe) ainda não está assinado, então o SmartScreen pode mostrar um aviso: clique em "Mais informações" → "Executar assim mesmo". É pela falta de assinatura, não por risco: o código é aberto e você pode revisá-lo (<a href="https://github.com/gabiMaglia/NetGauge#code-signing-policy" target="_blank" rel="noopener" class="ng-inline-link">Code signing policy</a>). No macOS o .dmg é assinado e notarizado pela Apple (desde a v2.0.2) e abre sem avisos.',
  'faq.q4.q': 'Preciso de permissões de administrador?',
  'faq.q4.a':
    'Para ler o tráfego de rede, na primeira execução pode pedir permissões elevadas. Nada além disso.',
  'faq.q5.q': 'Funciona em Mac com chip M?',
  'faq.q5.a': 'Sim. Há um build nativo para Apple Silicon (M1–M4) e outro para Mac com Intel.',
  'faq.q6.q': 'Corta a internet ao chegar na cota?',
  'faq.q6.a':
    'Não. A cota <b style="color:#cdddee">avisa</b> em 80% e 100%, mas nunca bloqueia ou corta a conexão. Você decide o que fazer.',

  'cta.title': 'Assuma o controle da sua rede.<br><span style="color:var(--acc,#458bf8)">Gratuito.</span>',
  'cta.subtitle': 'Open source, sem telemetria nem contas. Você instala em um minuto.',
  'cta.download': 'Baixar gratis',
  'cta.github': 'Ver no GitHub',

  'footer.tagline': 'O monitor de consumo de rede por aplicativo. Gratuito, open source e privado.',
  'footer.noTelemetry': 'Sem telemetria',
  'footer.local': 'Histórico local',
  'footer.project': 'Projeto',
  'footer.releases': 'Releases',
  'footer.license': 'Licença MIT',
  'footer.more': 'Mais',
  'footer.privacy': 'Privacidade',
  'footer.faq': 'FAQ',
  'footer.kofi': '☕ Pague um café',
  'footer.copyright': '© 2026 NetGauge · Licença MIT',
  'footer.madeWith': 'Feito com software livre (Qt / PySide6)',

  'a11y.skip': 'Ir para o conteúdo',

  'nav.main': 'Principal',
  'nav.menu': 'Menu',

  'lang.group': 'Idioma',
  'lang.es': 'Español',
  'lang.en': 'English',
  'lang.pt': 'Português',

  'mock.alt':
    'Prévia do NetGauge: velocidade de download e upload ao vivo, gráfico de largura de banda dos últimos 2 minutos e limites de consumo diário e mensal.',

  'privacy.link': 'Ler a política de privacidade completa ↗',

  'download.acc.winPolicy': 'Ver a Code signing policy ↗',
  'download.fallbackHint':
    'Se um botão levar você à página do GitHub Releases, escolha lá o arquivo do seu sistema.',
  'download.suggested': 'Sugerido',

  'footer.privacyPolicy': 'Política de privacidade ↗',
  'footer.nav': 'Links do rodapé',

  'share.cta': 'Me envie o link',
  'share.sub': 'Para abrir no seu computador',
  'share.note': 'O NetGauge é para Windows e macOS; abra-o no seu computador.',
  'share.copied': 'Link copiado. Cole no seu computador.',
  'share.subject': 'NetGauge: monitor de rede por aplicativo',
  'share.text': 'O NetGauge mostra quanto cada app consome. Para Windows e macOS, gratuito e open source:',

  'noscript.text': 'Baixe o NetGauge (Windows e macOS) em',
  'noscript.link': 'GitHub Releases',

  'os.other.label': 'Baixar grátis',
  'os.other.sub': 'Windows e macOS',
};

export const dictionaries: Record<Lang, Dict> = { es, en, pt };
