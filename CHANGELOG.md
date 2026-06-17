# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/);
versionado [SemVer](https://semver.org/lang/es/).

## [1.7.1] - 2026-06-17
### Added
- Metadata del editor embebida en el `.exe` (CompanyName/FileDescription).
- CI con GitHub Actions (pytest en windows-latest en cada push/PR).
### Changed
- App renombrada a **trafficMe** de punta a punta (exe, carpeta de instalación,
  tarea programada, carpeta de datos `%LOCALAPPDATA%\trafficMe`).
### Fixed
- Flecha (chevron) de los dropdowns rota.
- El gráfico de ancho de banda no se ocultaba en ventanas de poco alto.

## [1.7.0] - 2026-06-17
### Added
- **Chrome nativo de Windows**: resize desde esquinas + Aero Snap (Win+flechas,
  arrastrar al borde), maximizar nativo.
- Tab Global scrollable; % de cuota visible al pasar el límite.

## [1.5.0] - 2026-06-17
### Added
- Aviso de actualizaciones vía GitHub Releases (chequeo en segundo plano).
- Indicador de modo de captura (ETW / Global) en la barra de título.
- Maximizar/restaurar y persistencia de posición/tamaño de la ventana.
- Pipeline de firma de código (`build/sign.cmd`, listo para certificado).

## [1.4.0] - 2026-06-17
### Changed
- **Migración de PyQt6 (GPL) a PySide6 (LGPL)** para permitir distribución
  gratuita y comercial / closed-source.
### Added
- Suite de tests con pytest (dominio + aplicación + infraestructura).

## [1.3.0] - 2026-06-17
### Added
- GeoIP/ASN (país/proveedor de IPs remotas, opt-in) en Conexiones.
- Mini-gráfico (sparkline) en el ícono del tray.
- Alertas de anomalías (picos de tráfico, apps nuevas en la red).
### Changed
- Conexiones con reconciliación in-place; versión de esquema en la DB;
  disclosure de privacidad; formato de números por idioma.

## [1.2.0] - 2026-06-17
### Added
- Reputación VirusTotal (opt-in, por hash SHA-256).

## [1.1.0] - 2026-06-17
### Added
- Multi-idioma (es/en/pt) con cambio en vivo.
- Índice de confianza local por app (firma Authenticode embebida y por catálogo,
  ubicación, metadata).
- Conexiones activas por aplicación.
- Retención del histórico configurable.

## [1.0.0] - 2026-06-17
### Added
- Versión inicial: consumo por app (ETW) o global (psutil), velocidad en vivo,
  cuotas diaria/mensual con alertas, historial en SQLite, informe CSV, tray,
  tema claro/oscuro, instalador Inno Setup.
