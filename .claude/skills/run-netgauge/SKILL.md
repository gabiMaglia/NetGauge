---
name: run-netgauge
description: Lanza NetGauge (app de escritorio PySide6) desde código fuente en Windows para probar cambios manualmente. Trigger - cuando pidan correr, levantar, probar o ver la app andando.
---

# Run NetGauge (desktop, Windows, desde código fuente)

App de escritorio nativa (PySide6 + bandeja del sistema). No es web ni
Electron — no hay forma de tomar screenshot automático de la ventana;
el usuario tiene que mirar la pantalla.

## Lanzar

```bash
cd "c:\Users\Gabriel Maglia\network Monitor"
".venv/Scripts/python.exe" main.py &
sleep 4
tasklist | grep -i python.exe
```

Si `.venv/Scripts/python.exe` no existe, crear el venv primero:

```bash
cd "c:\Users\Gabriel Maglia\network Monitor"
python -m venv .venv
".venv/Scripts/python.exe" -m pip install -r requirements.txt -r requirements-dev.txt
```

## Verificar que arrancó sin crashear

No hay ventana de consola con stdout útil (la app loguea a archivo). Revisar:

```bash
tail -10 "/c/Users/Gabriel Maglia/AppData/Local/NetGauge/monitor.log"
```

- `[WARNING] ... Sin privilegios de Administrador: no se puede usar ETW.` → normal si la
  terminal no corre como admin; la app sigue funcionando con captura por psutil en vez de ETW.
- Cualquier traceback / `[ERROR]` con stacktrace → la app crasheó o falló al iniciar, investigar.
- Sin líneas nuevas tras varios segundos y sin proceso en `tasklist` → no llegó a levantar (falta
  alguna dependencia, revisar el output del lanzamiento sin backgroundear con `&` para ver el error).

## Datos de la app (settings, DB, reportes, log)

`%LOCALAPPDATA%\NetGauge\` → `monitor.log`, `settings.json`, `usage.db`, `reports/`.

## Frenarla

```bash
tasklist | grep -i python.exe   # identificar PID del proceso principal (el de mayor memoria)
taskkill //PID <pid> //F
```

## Limitación conocida

No hay automatización de UI para esta app (no Playwright, no Electron driver). La verificación
visual de cambios en pantallas/diálogos la tiene que hacer el usuario mirando la ventana —
este skill solo cubre lanzar + confirmar que no crasheó por log.
