# ==============================================================================
# SCRIPT DE CONFIGURACIÓN Y EMPAQUETADO MSIX PARA CLAUDE CODE
# Proyecto: Analizador de Tráfico de Red (PySide + PyInstaller)
# Requerimiento especial: Privilegios de Administrador (Full Trust)
# ==============================================================================

# 1. Definición de variables del proyecto (Modificá según tus datos de Partner Center)
$AppName = "AnalizadorRed"
$PublisherName = "CN=TuNombreOEmpresa"
$Version = "1.0.0.0"
$ExePath = ".\dist\tu_app.exe" # Ruta de tu ejecutable ya compilado
$TargetDir = ".\MSIX_Build"
$ManifestPath = "$TargetDir\AppxManifest.xml"

Write-Host "=== Iniciando preparación de empaquetado para Microsoft Store ===" -ForegroundColor Cyan

# 2. Creación del directorio de trabajo limpio
if (Test-Path $TargetDir) { Remove-Item -Recurse -Force $TargetDir }
New-Item -ItemType Directory -Path "$TargetDir\AppX" | Out-Null

# 3. Copiar el ejecutable compilado al contenedor del paquete
Copy-Item $ExePath -Destination "$TargetDir\AppX\tu_app.exe"

# 4. Generar el Manifiesto de Aplicación con capacidades Full Trust (Requerido para Redes)
# Nota para Claude: Este XML define el acceso total al sistema y modo Administrador para la Store.
$ManifestContent = @"
<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://microsoft.com"
  xmlns:uap="http://microsoft.com"
  xmlns:rescap="http://microsoft.com/restrictedcapabilities"
  IgnorableNamespaces="uap rescap">

  

  <Properties>
    <DisplayName>$AppName</DisplayName>
    <PublisherDisplayName>Tu Nombre de Desarrollador</PublisherDisplayName>
    <Logo>Assets\StoreLogo.png</Logo>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.22000.0" />
  </Dependencies>

  <Resources>
    <Resource Language="es-ES"/>
  </Resources>

  <Applications>
    <Application Id="App"
      Executable="AppX\tu_app.exe"
      EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements
        DisplayName="$AppName"
        Description="Analizador de tráfico de red en tiempo real."
        BackgroundColor="#transparent"
        Square150x150Logo="Assets\Square150x150Logo.png"
        Square44x44Logo="Assets\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\Wide310x150Logo.png" />
      </uap:VisualElements>
    </Application>
  </Applications>

  <Capabilities>
    <!-- Capacidad crítica para salirse del Sandbox y ejecutar como Administrador -->
    <rescap:Capability Name="runFullTrust" />
    <!-- Capacidades específicas para captura y análisis de sockets de red -->
    <Capability Name="internetClientServer" />
    <Capability Name="privateNetworkClientServer" />
  </Capabilities>
</Package>
"@

Set-Content -Path $ManifestPath -Value $ManifestContent
Write-Host "[OK] AppxManifest.xml generado con capacidades Full Trust y de Red." -ForegroundColor Green

# 5. Instrucciones de compilación final con MakeAppx
Write-Host ""
Write-Host "=== INSTRUCCIONES PARA EL ENTORNO DE CLAUDE CODE ===" -ForegroundColor Yellow
Write-Host "Para compilar este directorio en un archivo .msix ejecutable, Claude debe correr:"
Write-Host "makeappx pack /d `"$TargetDir\AppX`" /p `".\$AppName.msix`"" -ForegroundColor Magenta
