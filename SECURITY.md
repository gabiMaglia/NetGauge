# Política de seguridad

## Versiones soportadas

Se corrigen vulnerabilidades solo en la **última versión publicada** en
[GitHub Releases](https://github.com/gabiMaglia/NetGauge/releases/latest).

## Cómo reportar una vulnerabilidad

Por favor **no abras un issue público** para temas de seguridad.

1. **Preferido:** reporte privado de GitHub
   <https://github.com/gabiMaglia/NetGauge/security/advisories/new>
   (pestaña *Security* → *Report a vulnerability*).
2. **Alternativa:** email a **gab.maglia@gmail.com** con el asunto
   `[NetGauge security]`.

Incluí, si podés: versión de NetGauge, sistema operativo, pasos para reproducir
e impacto esperado.

## Qué esperar

- Acuse de recibo en un plazo razonable (es un proyecto personal, sin SLA formal).
- Coordinamos la divulgación: primero el fix en un release, después el detalle público.
- Se da crédito en el CHANGELOG si lo querés.

## Alcance y límites conocidos

Estos puntos **ya son conocidos y están documentados**; no hace falta reportarlos
(sí cualquier forma de explotarlos más allá de lo descrito):

- La API key de VirusTotal se guarda en **texto plano** en `settings.json`
  (ver sección *Privacidad* del [README](README.md)).
- GeoIP usa `http://ip-api.com` (plan gratuito, sin cifrado en tránsito).
- Los binarios **no están firmados** (SmartScreen / Gatekeeper avisan al abrirlos).
  Verificá la integridad con el archivo `SHA256SUMS` adjunto a cada release.
- En Windows la app corre elevada (administrador) para usar ETW.
