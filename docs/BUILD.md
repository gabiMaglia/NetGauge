# Guía de build y empaquetado

Cómo pasar del código fuente al instalador `.exe` de Windows 11 (x64).

## 0. Requisito que MÁS se olvida

Las dependencias deben instalarse en **el mismo intérprete de Python** con el que
vas a compilar. Si `pywintrace` (módulo `etw`) no está en ese Python, PyInstaller
arma un exe **sin ETW** y la app queda en modo global (solo consumo total, sin
desglose por app). Verificá antes de compilar:

```powershell
python -c "import etw, PyQt6, psutil; print('deps OK')"
```

Si falla, instalá todo y reintentá:

```powershell
pip install -r requirements.txt
```

## 1. Ejecutar en desarrollo

```powershell
cd "network Monitor"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Para desglose por app, abrí PowerShell COMO ADMINISTRADOR:
python main.py
```

## 2. Compilar el .exe (PyInstaller)

```powershell
pip install pyinstaller
pyinstaller build\network_monitor.spec --noconfirm
# Resultado: dist\NetworkMonitor.exe (one-file, pide elevación al abrir)
```

Puntos clave del spec (`build/network_monitor.spec`):

- `collect_submodules("etw")` — bundlea TODO pywintrace (sin esto no hay ETW).
- `collect_submodules("PyQt6")` — incluye plugins de Qt.
- `uac_admin=True` — el exe pide elevación (necesario para ETW).
- `console=False` — app de bandeja, sin ventana de consola.
- `icon="..\assets\icon.ico"` — ícono de la app.
- `target_arch="x86_64"` — Windows x64.

### Regenerar el ícono

El ícono se genera por código (no hay editor de imágenes en juego):

```powershell
python build\make_icon.py   # genera assets\icon.ico (16–256 px)
```

## 3. Compilar el instalador (Inno Setup)

Necesitás Inno Setup 6+. Por winget:

```powershell
winget install --id JRSoftware.InnoSetup -e
```

Luego, con `dist\NetworkMonitor.exe` ya compilado:

```powershell
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" build\installer.iss
# Resultado: build\Output\NetworkMonitor-Setup-1.0.0-x64.exe
```

> La ruta de `ISCC.exe` puede ser `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
> o `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe` según cómo se haya instalado.

Puntos clave del instalador (`build/installer.iss`):

- `ArchitecturesAllowed=x64compatible` — solo Windows x64.
- `PrivilegesRequired=admin` — instala elevado.
- `SetupIconFile` + `UninstallDisplayIcon` — ícono en Setup y en "Programas".
- **Autoarranque robusto**: en vez de `HKCU\Run` (que con un instalador elevado
  va al hive equivocado y dispara UAC en cada login), crea una **tarea
  programada** `trafficMe` con `/SC ONLOGON /RL HIGHEST`. Arranca elevada al
  iniciar sesión, sin prompt repetido. Se borra en la desinstalación.
- El "Ejecutar ahora" post-instalación usa `shellexec` (no `CreateProcess`) para
  respetar el manifiesto `requireAdministrator` y evitar el error 740.

## 4. Verificación rápida tras instalar

1. Reinstalá el Setup nuevo (los viejos pueden traer un exe sin ETW).
2. Aceptá el prompt de UAC al abrir.
3. Generá algo de tráfico unos segundos.
4. La pestaña **Por aplicación** debe poblarse. Si solo ves Global, revisá
   `%LOCALAPPDATA%\NetworkMonitor\monitor.log`:
   - `Captura ETW por proceso activada.` → todo bien.
   - `Fallo inicializando ETW (...)` → faltó `etw` en el build o no hay admin.
