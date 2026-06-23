@echo off
REM ===========================================================================
REM Firma de codigo para NetLeak (exe + instalador).
REM Requiere un certificado de firma (.pfx) y signtool.exe (Windows SDK).
REM
REM Uso (PowerShell o CMD, desde la raiz del proyecto):
REM   set CERT_PFX=C:\ruta\miCert.pfx
REM   set CERT_PASS=tu_password
REM   build\sign.cmd
REM
REM Sin CERT_PFX definido, el script avisa y no hace nada (no rompe el build).
REM ===========================================================================

if "%CERT_PFX%"=="" (
  echo [sign] CERT_PFX no definido: se omite la firma ^(build sin firmar^).
  echo [sign] Para firmar: set CERT_PFX y CERT_PASS, luego corre build\sign.cmd
  exit /b 0
)

set TS=http://timestamp.digicert.com
set EXE=dist\NetLeak.exe

echo [sign] Firmando %EXE% ...
signtool sign /f "%CERT_PFX%" /p "%CERT_PASS%" /fd SHA256 /tr %TS% /td SHA256 "%EXE%" || exit /b 1

REM El instalador toma el nombre con la versión actual (comodín).
for %%F in (build\Output\NetLeak-Setup-*-x64.exe) do (
  echo [sign] Firmando %%F ...
  signtool sign /f "%CERT_PFX%" /p "%CERT_PASS%" /fd SHA256 /tr %TS% /td SHA256 "%%F" || exit /b 1
)

echo [sign] OK: exe e instalador firmados.
