; Inno Setup script para Network Monitor (Windows x64).
; Compilar con: ISCC.exe build\installer.iss
; (requiere Inno Setup 6+: https://jrsoftware.org/isdl.php)

#define AppName "Network Monitor"
#define AppVersion "1.7.0"
#define AppExe "NetworkMonitor.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\NetworkMonitor
DefaultGroupName={#AppName}
OutputBaseFilename=NetworkMonitor-Setup-{#AppVersion}-x64
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; ETW necesita privilegios elevados:
PrivilegesRequired=admin
WizardStyle=modern
; Icono del propio Setup.exe y el que se ve en "Programas instalados".
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
; Muestra la licencia MIT durante la instalación.
LicenseFile=..\LICENSE

[Files]
; Salida one-file de PyInstaller (dist\NetworkMonitor.exe):
Source: "..\dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"

[Tasks]
Name: "startup"; Description: "Iniciar con Windows"; GroupDescription: "Opciones:"

[Run]
; Autoarranque robusto: tarea programada al iniciar sesion, con privilegios
; maximos (ETW necesita admin) y SIN prompt de UAC en cada login.
; HKCU\Run no sirve: corriendo elevado iria al hive equivocado y pediria UAC.
Filename: "{sys}\schtasks.exe"; \
    Parameters: "/Create /F /TN ""{#AppName}"" /TR ""\""{app}\{#AppExe}\"""" /SC ONLOGON /RL HIGHEST"; \
    Flags: runhidden; Tasks: startup; StatusMsg: "Configurando inicio con Windows..."
; shellexec (no CreateProcess): respeta el manifiesto requireAdministrator del
; exe y eleva bien. Con CreateProcess da error 740 (requiere elevacion).
Filename: "{app}\{#AppExe}"; Description: "Ejecutar ahora"; \
    Flags: nowait postinstall skipifsilent shellexec

[UninstallRun]
; Borra la tarea al desinstalar (si no existe, schtasks devuelve error inocuo).
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""{#AppName}"""; \
    Flags: runhidden; RunOnceId: "DelTraficMeTask"
