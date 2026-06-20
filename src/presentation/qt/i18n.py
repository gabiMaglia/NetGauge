"""Internacionalización simple: español, inglés y portugués.

Uso:  from .i18n import t, set_language
      set_language("en"); t("tab.global")  -> "Global"
      t("chart.peak", v="1.2 MB")           -> "peak 1.2 MB/s"
"""
from __future__ import annotations

LANGUAGES = {"es": "Español", "en": "English", "pt": "Português"}
_lang = "es"

_STR: dict[str, dict[str, str]] = {
    "es": {
        "brand.sub": "· Mes actual",
        "btn.about": "Acerca de", "btn.quota": "Cuota", "btn.settings": "Ajustes",
        "period.session": "Sesión", "period.day": "Día",
        "period.week": "Semana", "period.month": "Mes",
        "tab.global": "Global", "tab.apps": "Por aplicación",
        "tab.connections": "Conexiones",
        "card.download": "Bajada", "card.upload": "Subida", "card.total": "Σ Total",
        "card.pct_of_total": "{p}% del total", "card.period_usage": "consumo del período",
        "chart.title": "Ancho de banda en vivo", "chart.peak": "pico {v}/s",
        "legend.download": "Bajada", "legend.upload": "Subida",
        "quota.daily": "Límite diario · hoy", "quota.monthly": "Límite mensual · este ciclo",
        "quota.no_limit": "sin límite",
        "dlg.quota.title": "Configurar cuota",
        "dlg.quota.daily": "Límite diario (GB · 0 = sin límite)",
        "dlg.quota.monthly": "Límite mensual (GB · 0 = sin límite)",
        "dlg.quota.cycle_day": "Día de corte del ciclo (1–28)",
        "btn.cancel": "Cancelar", "btn.save": "Guardar", "btn.close": "Cerrar",
        "about.version": "versión {v}",
        "dlg.about.desc": "Monitor de consumo de red por aplicación para Windows. "
                          "Mide subida y bajada en tiempo real, lleva analíticas "
                          "históricas y te avisa al superar tus cuotas.",
        "dlg.about.made_by": "Hecho por {author} · Licencia MIT (software libre)",
        "dlg.about.support": "Si la app te resulta útil, podés invitarme un café ☕",
        "btn.kofi": "☕  Apoyar en Ko-fi",
        "tray.metrics": "Ver métricas", "tray.export": "Exportar informe ahora",
        "tray.about": "Acerca de", "tray.quit": "Salir",
        "tray.report_saved": "Informe guardado:\n{path}",
        "tray.report_empty": "Todavía no hay datos para exportar.",
        "tray.report_error": "No se pudo exportar: {err}",
        "dlg.settings.title": "Ajustes",
        "dlg.settings.language": "Idioma",
        "dlg.settings.retention": "Retención del histórico (días · 0 = nunca)",
        "dlg.settings.trust": "Índice de confianza local (firma/ubicación)",
        "dlg.settings.vt": "VirusTotal: reputación online (envía solo el hash)",
        "dlg.settings.vt_key": "API key de VirusTotal",
        "dlg.settings.vt_signup": "¿No tenés una API key? Conseguí la tuya gratis en VirusTotal",
        "dlg.settings.vt_led.untested": "Conexión con VirusTotal: sin probar",
        "dlg.settings.vt_led.testing": "Conexión con VirusTotal: probando…",
        "dlg.settings.vt_led.ok": "Conexión con VirusTotal: clave válida",
        "dlg.settings.vt_led.error": "Conexión con VirusTotal: clave inválida o sin conexión",
        "dlg.settings.geoip": "GeoIP: país/proveedor de IPs remotas (ip-api.com)",
        "dlg.settings.anomaly": "Alertas de anomalías (picos / apps nuevas en red)",
        "dlg.settings.privacy": "Privacidad: VirusTotal envía solo el hash SHA-256 "
                                "del ejecutable; GeoIP envía la IP remota a ip-api.com. "
                                "Nada más sale de tu equipo, y ambas están apagadas por "
                                "defecto.",
        "alert.scope.daily": "diaria", "alert.scope.monthly": "mensual",
        "alert.quota.title": "Cuota {scope}",
        "alert.quota.body": "Alcanzaste el {pct}% de tu cuota {scope} "
                            "({used} de {limit}).",
        "alert.spike.title": "Actividad de red inusual",
        "alert.spike.body": "Pico de tráfico: {rate}/s (≈{x}× el promedio reciente).",
        "alert.newapp.title": "App nueva usando la red",
        "alert.newapp.body": "{app} empezó a enviar datos ({sent}).",
        "alert.update.title": "Hay una versión nueva",
        "alert.update.body": "trafficMe {v} está disponible. Descargala en {url}",
        "mode.etw": "ETW · por app", "mode.global": "Global",
        "mode.etw_tip": "Captura por proceso activa (ETW, como admin).",
        "mode.nettop": "nettop · por app",
        "mode.nettop_tip": "Captura por proceso activa (nettop, best-effort).",
        "mode.global_tip": "Sin desglose por app: medición global (psutil). "
                           "Ejecutá como Administrador para activar ETW.",
        "conn.empty": "No hay conexiones activas.",
        "conn.subtitle": "Conexiones de red activas por aplicación (vía psutil).",
        "conn.hide_localhost": "Ocultar localhost",
        "trust.level.trusted": "Confiable", "trust.level.unknown": "Sin datos",
        "trust.level.caution": "Precaución", "trust.level.suspicious": "Sospechoso",
        "trust.title": "Índice de confianza",
        "trust.signed": "Firmado y válido", "trust.signed_by": "Firmado por {signer}",
        "trust.unsigned": "Sin firma digital",
        "trust.invalid_sig": "Firma inválida o alterada",
        "trust.location_ok": "En ubicación de sistema",
        "trust.location_bad": "Corre desde una ubicación temporal/atípica",
        "trust.no_metadata": "Sin metadata del editor",
        "trust.system_file": "Componente de Windows (firmado por catálogo)",
        "trust.vt_clean": "VirusTotal: {m}/{n} — limpio",
        "trust.vt_detected": "VirusTotal: {m}/{n} motores lo marcan",
    },
    "en": {
        "brand.sub": "· Current month",
        "btn.about": "About", "btn.quota": "Quota", "btn.settings": "Settings",
        "period.session": "Session", "period.day": "Day",
        "period.week": "Week", "period.month": "Month",
        "tab.global": "Global", "tab.apps": "Per application",
        "tab.connections": "Connections",
        "card.download": "Download", "card.upload": "Upload", "card.total": "Σ Total",
        "card.pct_of_total": "{p}% of total", "card.period_usage": "usage this period",
        "chart.title": "Live bandwidth", "chart.peak": "peak {v}/s",
        "legend.download": "Download", "legend.upload": "Upload",
        "quota.daily": "Daily limit · today", "quota.monthly": "Monthly limit · this cycle",
        "quota.no_limit": "no limit",
        "dlg.quota.title": "Configure quota",
        "dlg.quota.daily": "Daily limit (GB · 0 = no limit)",
        "dlg.quota.monthly": "Monthly limit (GB · 0 = no limit)",
        "dlg.quota.cycle_day": "Billing cycle start day (1–28)",
        "btn.cancel": "Cancel", "btn.save": "Save", "btn.close": "Close",
        "about.version": "version {v}",
        "dlg.about.desc": "Per-application network usage monitor for Windows. "
                          "Measures upload and download in real time, keeps "
                          "historical analytics and alerts you when you exceed quotas.",
        "dlg.about.made_by": "Made by {author} · MIT License (free software)",
        "dlg.about.support": "If you find the app useful, you can buy me a coffee ☕",
        "btn.kofi": "☕  Support on Ko-fi",
        "tray.metrics": "Show metrics", "tray.export": "Export report now",
        "tray.about": "About", "tray.quit": "Quit",
        "tray.report_saved": "Report saved:\n{path}",
        "tray.report_empty": "No data to export yet.",
        "tray.report_error": "Could not export: {err}",
        "dlg.settings.title": "Settings",
        "dlg.settings.language": "Language",
        "dlg.settings.retention": "History retention (days · 0 = never)",
        "dlg.settings.trust": "Local trust index (signature/location)",
        "dlg.settings.vt": "VirusTotal: online reputation (sends only the hash)",
        "dlg.settings.vt_key": "VirusTotal API key",
        "dlg.settings.vt_signup": "Don't have an API key? Get yours for free on VirusTotal",
        "dlg.settings.vt_led.untested": "VirusTotal connection: not tested",
        "dlg.settings.vt_led.testing": "VirusTotal connection: testing…",
        "dlg.settings.vt_led.ok": "VirusTotal connection: key valid",
        "dlg.settings.vt_led.error": "VirusTotal connection: invalid key or connection error",
        "dlg.settings.geoip": "GeoIP: country/provider of remote IPs (ip-api.com)",
        "dlg.settings.anomaly": "Anomaly alerts (spikes / new apps on network)",
        "dlg.settings.privacy": "Privacy: VirusTotal sends only the executable's "
                                "SHA-256 hash; GeoIP sends the remote IP to ip-api.com. "
                                "Nothing else leaves your machine, and both are off by "
                                "default.",
        "alert.scope.daily": "daily", "alert.scope.monthly": "monthly",
        "alert.quota.title": "{scope} quota",
        "alert.quota.body": "You reached {pct}% of your {scope} quota "
                            "({used} of {limit}).",
        "alert.spike.title": "Unusual network activity",
        "alert.spike.body": "Traffic spike: {rate}/s (≈{x}× the recent average).",
        "alert.newapp.title": "New app using the network",
        "alert.newapp.body": "{app} started sending data ({sent}).",
        "alert.update.title": "A new version is available",
        "alert.update.body": "trafficMe {v} is available. Download it at {url}",
        "mode.etw": "ETW · per app", "mode.global": "Global",
        "mode.etw_tip": "Per-process capture active (ETW, as admin).",
        "mode.nettop": "nettop · per app",
        "mode.nettop_tip": "Per-process capture active (nettop, best-effort).",
        "mode.global_tip": "No per-app breakdown: global measurement (psutil). "
                           "Run as Administrator to enable ETW.",
        "conn.empty": "No active connections.",
        "conn.subtitle": "Active network connections per application (via psutil).",
        "conn.hide_localhost": "Hide localhost",
        "trust.level.trusted": "Trusted", "trust.level.unknown": "Unknown",
        "trust.level.caution": "Caution", "trust.level.suspicious": "Suspicious",
        "trust.title": "Trust index",
        "trust.signed": "Signed and valid", "trust.signed_by": "Signed by {signer}",
        "trust.unsigned": "Not digitally signed",
        "trust.invalid_sig": "Invalid or altered signature",
        "trust.location_ok": "In a system location",
        "trust.location_bad": "Runs from a temporary/atypical location",
        "trust.no_metadata": "No publisher metadata",
        "trust.system_file": "Windows component (catalog-signed)",
        "trust.vt_clean": "VirusTotal: {m}/{n} — clean",
        "trust.vt_detected": "VirusTotal: {m}/{n} engines flag it",
    },
    "pt": {
        "brand.sub": "· Mês atual",
        "btn.about": "Sobre", "btn.quota": "Cota", "btn.settings": "Ajustes",
        "period.session": "Sessão", "period.day": "Dia",
        "period.week": "Semana", "period.month": "Mês",
        "tab.global": "Global", "tab.apps": "Por aplicativo",
        "tab.connections": "Conexões",
        "card.download": "Download", "card.upload": "Upload", "card.total": "Σ Total",
        "card.pct_of_total": "{p}% do total", "card.period_usage": "consumo do período",
        "chart.title": "Largura de banda ao vivo", "chart.peak": "pico {v}/s",
        "legend.download": "Download", "legend.upload": "Upload",
        "quota.daily": "Limite diário · hoje", "quota.monthly": "Limite mensal · este ciclo",
        "quota.no_limit": "sem limite",
        "dlg.quota.title": "Configurar cota",
        "dlg.quota.daily": "Limite diário (GB · 0 = sem limite)",
        "dlg.quota.monthly": "Limite mensal (GB · 0 = sem limite)",
        "dlg.quota.cycle_day": "Dia de início do ciclo (1–28)",
        "btn.cancel": "Cancelar", "btn.save": "Salvar", "btn.close": "Fechar",
        "about.version": "versão {v}",
        "dlg.about.desc": "Monitor de consumo de rede por aplicativo para Windows. "
                          "Mede upload e download em tempo real, mantém análises "
                          "históricas e avisa quando você ultrapassa as cotas.",
        "dlg.about.made_by": "Feito por {author} · Licença MIT (software livre)",
        "dlg.about.support": "Se o app for útil, você pode me pagar um café ☕",
        "btn.kofi": "☕  Apoiar no Ko-fi",
        "tray.metrics": "Ver métricas", "tray.export": "Exportar relatório agora",
        "tray.about": "Sobre", "tray.quit": "Sair",
        "tray.report_saved": "Relatório salvo:\n{path}",
        "tray.report_empty": "Ainda não há dados para exportar.",
        "tray.report_error": "Não foi possível exportar: {err}",
        "dlg.settings.title": "Ajustes",
        "dlg.settings.language": "Idioma",
        "dlg.settings.retention": "Retenção do histórico (dias · 0 = nunca)",
        "dlg.settings.trust": "Índice de confiança local (assinatura/local)",
        "dlg.settings.vt": "VirusTotal: reputação online (envia só o hash)",
        "dlg.settings.vt_key": "Chave de API do VirusTotal",
        "dlg.settings.vt_signup": "Não tem uma chave de API? Consiga a sua gratuitamente no VirusTotal",
        "dlg.settings.vt_led.untested": "Conexão com o VirusTotal: não testada",
        "dlg.settings.vt_led.testing": "Conexão com o VirusTotal: testando…",
        "dlg.settings.vt_led.ok": "Conexão com o VirusTotal: chave válida",
        "dlg.settings.vt_led.error": "Conexão com o VirusTotal: chave inválida ou sem conexão",
        "dlg.settings.geoip": "GeoIP: país/provedor de IPs remotas (ip-api.com)",
        "dlg.settings.anomaly": "Alertas de anomalias (picos / apps novos na rede)",
        "dlg.settings.privacy": "Privacidade: o VirusTotal envia só o hash SHA-256 "
                                "do executável; o GeoIP envia o IP remoto ao ip-api.com. "
                                "Nada mais sai do seu equipamento, e ambos vêm "
                                "desligados por padrão.",
        "alert.scope.daily": "diária", "alert.scope.monthly": "mensal",
        "alert.quota.title": "Cota {scope}",
        "alert.quota.body": "Você atingiu {pct}% da sua cota {scope} "
                            "({used} de {limit}).",
        "alert.spike.title": "Atividade de rede incomum",
        "alert.spike.body": "Pico de tráfego: {rate}/s (≈{x}× a média recente).",
        "alert.newapp.title": "Novo app usando a rede",
        "alert.newapp.body": "{app} começou a enviar dados ({sent}).",
        "alert.update.title": "Há uma versão nova",
        "alert.update.body": "trafficMe {v} está disponível. Baixe em {url}",
        "mode.etw": "ETW · por app", "mode.global": "Global",
        "mode.etw_tip": "Captura por processo ativa (ETW, como admin).",
        "mode.nettop": "nettop · por app",
        "mode.nettop_tip": "Captura por processo ativa (nettop, best-effort).",
        "mode.global_tip": "Sem detalhe por app: medição global (psutil). "
                           "Execute como Administrador para ativar o ETW.",
        "conn.empty": "Não há conexões ativas.",
        "conn.subtitle": "Conexões de rede ativas por aplicativo (via psutil).",
        "conn.hide_localhost": "Ocultar localhost",
        "trust.level.trusted": "Confiável", "trust.level.unknown": "Sem dados",
        "trust.level.caution": "Atenção", "trust.level.suspicious": "Suspeito",
        "trust.title": "Índice de confiança",
        "trust.signed": "Assinado e válido", "trust.signed_by": "Assinado por {signer}",
        "trust.unsigned": "Sem assinatura digital",
        "trust.invalid_sig": "Assinatura inválida ou alterada",
        "trust.location_ok": "Em local de sistema",
        "trust.location_bad": "Roda a partir de um local temporário/atípico",
        "trust.no_metadata": "Sem metadados do editor",
        "trust.system_file": "Componente do Windows (assinado por catálogo)",
        "trust.vt_clean": "VirusTotal: {m}/{n} — limpo",
        "trust.vt_detected": "VirusTotal: {m}/{n} motores o marcam",
    },
}


# Separadores por idioma (es/pt: 1.234,5 · en: 1,234.5)
_DECIMAL = {"es": ",", "en": ".", "pt": ","}
_GROUP = {"es": ".", "en": ",", "pt": "."}


def fmt_number(value: float, decimals: int = 1, group: bool = True) -> str:
    """Formatea un número con separadores según el idioma actual."""
    s = f"{value:,.{decimals}f}"  # base: ',' miles, '.' decimal
    dec = _DECIMAL.get(_lang, ".")
    grp = _GROUP.get(_lang, ",")
    s = s.replace(",", "\x00").replace(".", dec).replace("\x00", grp if group else "")
    return s


def loc_bytes(num: float) -> str:
    """human_bytes con el separador decimal del idioma actual ('47,7 MB')."""
    from ...domain.models import human_bytes
    val, _, unit = human_bytes(num).partition(" ")
    return f"{val.replace('.', _DECIMAL.get(_lang, '.'))} {unit}"


def set_language(lang: str) -> None:
    global _lang
    if lang in _STR:
        _lang = lang


def current_language() -> str:
    return _lang


def t(key: str, **kw) -> str:
    table = _STR.get(_lang, _STR["en"])
    text = table.get(key) or _STR["en"].get(key, key)
    return text.format(**kw) if kw else text
