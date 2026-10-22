# Licencias de terceros

NetGauge es software libre bajo licencia **MIT** (ver [LICENSE](LICENSE)).
Los binarios publicados incluyen los componentes de terceros de abajo, cada uno
bajo su propia licencia. Las versiones exactas son las resueltas al momento del
build (ver `requirements.txt` y el release correspondiente).

| Componente | Uso | Licencia | Sitio |
|---|---|---|---|
| PySide6 / Qt for Python (Qt) | Interfaz gráfica | **LGPL v3** (ver abajo) | https://www.qt.io/qt-for-python · https://code.qt.io/cgit/pyside/pyside-setup.git |
| psutil | Contadores de red, procesos, conexiones | BSD-3-Clause | https://github.com/giampaolo/psutil |
| pywintrace (módulo `etw`) — solo Windows | Captura ETW por proceso | BSD | https://github.com/fireeye/pywintrace |
| keyring | API key de VirusTotal en el almacén de credenciales del SO | MIT | https://github.com/jaraco/keyring |
| jaraco.classes (dep. de keyring) | Utilidades de clases | MIT | https://github.com/jaraco/jaraco.classes |
| jaraco.functools (dep. de keyring) | Utilidades de funciones | MIT | https://github.com/jaraco/jaraco.functools |
| jaraco.context (dep. de keyring) | Utilidades de context managers | MIT | https://github.com/jaraco/jaraco.context |
| more-itertools (dep. de jaraco) | Utilidades de iteración | MIT | https://github.com/more-itertools/more-itertools |
| pywin32-ctypes (dep. de keyring) — solo Windows | Acceso a Credential Manager sin pywin32 | BSD-3-Clause | https://github.com/enthought/pywin32-ctypes |
| reportlab | Exportar informes PDF | BSD | https://www.reportlab.com/opensource/ |
| openpyxl | Exportar informes Excel | MIT | https://foss.heptapod.net/openpyxl/openpyxl |
| Plus Jakarta Sans (fuentes) | Tipografía de la interfaz | SIL OFL 1.1 | https://github.com/tokotype/PlusJakartaSans |
| JetBrains Mono (fuentes) | Cifras monoespaciadas de la interfaz | SIL OFL 1.1 | https://github.com/JetBrains/JetBrainsMono |
| PyInstaller (solo build) | Empaquetado | GPL v2+ con excepción de bootloader | https://pyinstaller.org |
| Python (intérprete embebido) | Runtime | PSF License | https://docs.python.org/3/license.html |

La licencia completa de Plus Jakarta Sans está en `assets/fonts/OFL.txt`
(se distribuye junto a las fuentes dentro del bundle).
La de JetBrains Mono está en `assets/fonts/OFL-JetBrainsMono.txt`.

## PySide6 / Qt — aviso LGPL v3

NetGauge usa **PySide6 (Qt for Python)**, licenciado bajo la
**GNU Lesser General Public License v3** (https://www.gnu.org/licenses/lgpl-3.0.html).
NetGauge **no modifica** PySide6 ni Qt; se usan tal cual se publican en PyPI.

**Cómo obtener el código fuente de Qt / PySide6:**

- PySide6: https://code.qt.io/cgit/pyside/pyside-setup.git (y el sdist en https://pypi.org/project/PySide6/#files).
- Qt: https://download.qt.io/official_releases/qt/ y https://code.qt.io/cgit/qt/.
- Código fuente de NetGauge (MIT): https://github.com/gabiMaglia/NetGauge

**Cómo usar una versión modificada de Qt/PySide6 con NetGauge:**

- **Windows (`.exe`, PyInstaller *one-file*):** las librerías Qt viajan
  comprimidas dentro del `.exe` y se extraen a una carpeta temporal al ejecutar,
  por lo que **no se pueden reemplazar in situ**. Para usar tu propia versión,
  relinkeá construyendo NetGauge desde fuente (pasos abajo).
- **macOS (`.app`, PyInstaller *onedir*):** los frameworks de Qt están sueltos en
  `NetGauge.app/Contents/Frameworks` y **se pueden reemplazar in situ** por tu
  propia build compatible. También podés rearmar desde fuente.

Como exige la LGPL, en ambos casos podés rearmar NetGauge con tu propia versión
de PySide6/Qt:

1. Cloná el repositorio.
2. Instalá en tu entorno la versión de PySide6 que quieras (o tu build modificado).
3. Generá el ejecutable siguiendo [`docs/BUILD.md`](docs/BUILD.md)
   (`pyinstaller build/network_monitor.spec` en Windows,
   `build/network_monitor_macos.spec` en macOS).

Se puede ejecutar también directamente desde fuente (`python main.py`), sin
ningún empaquetado, con la versión de PySide6 instalada en tu entorno.

## Servicios externos opcionales

No son componentes incluidos, pero la app puede conectarse a ellos si el usuario
lo activa: **ip-api.com** (GeoIP; plan gratuito solo para uso no comercial) y
**VirusTotal** (API pública; uso no comercial). Detalle en la sección
*Privacidad* del [README](README.md).
