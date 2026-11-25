<#
 Builds SDrop as an MSIX (run on Windows, or by the GitHub workflow).
   -Store  -> UNSIGNED package for Partner Center (the Store signs it)
   default -> signed with a throw-away certificate, for the certification-kit test
#>
param(
  [string]$IdentityName = "Smartupworld.SDrop",
  [string]$Publisher = "CN=A10ED12C-0499-4FBE-8193-87C74DAFC0BB",
  [string]$PublisherDisplayName = "Smartupworld",
  [string]$Version = "2.0.0.0",
  [switch]$Store
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$out = Join-Path $root "dist"; $layout = Join-Path $out "layout"
Remove-Item $out, build_py -Recurse -Force -ErrorAction SilentlyContinue
New-Item $layout -ItemType Directory | Out-Null

function Find-SdkTool($name) {
  $hit = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter $name -ErrorAction SilentlyContinue |
         Where-Object { $_.FullName -match "\\x64\\" } | Sort-Object FullName -Descending | Select-Object -First 1
  if (-not $hit) { throw "$name not found (Windows SDK missing)" }
  $hit.FullName
}
$makeappx = Find-SdkTool "makeappx.exe"

Write-Host "1/4 Bundling the app with PyInstaller..."
python -m pip install --upgrade PyQt6 pyinstaller pillow
python -m PyInstaller --clean --noconfirm --onedir --windowed --name SDrop --icon "$root\sdrop.ico" --hidden-import=PyQt6.sip --distpath build_py --workpath build_py\work --specpath build_py "$root\sdrop.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
Copy-Item build_py\SDrop\* $layout -Recurse -Force

Write-Host "2/4 Logos and manifest..."
python Packaging\make-assets.py "$layout\Assets" "$out\store-logos"
if ($LASTEXITCODE -ne 0) { throw "asset script failed" }
$m = Get-Content "$PSScriptRoot\AppxManifest.xml" -Raw
$m = $m.Replace("{{IDENTITY_NAME}}",$IdentityName).Replace("{{PUBLISHER}}",$Publisher).Replace("{{VERSION}}",$Version).Replace("{{PUBLISHER_DISPLAY_NAME}}",$PublisherDisplayName)
Set-Content "$layout\AppxManifest.xml" $m -Encoding UTF8

Write-Host "3/4 Packing..."
$msix = Join-Path $out "SDrop_$Version.msix"
& $makeappx pack /d $layout /p $msix /o
if ($LASTEXITCODE -ne 0) { throw "makeappx failed" }
if ($Store) { Write-Host "DONE (unsigned, for Partner Center): $msix"; return }

Write-Host "4/4 Signing with a test certificate..."
$signtool = Find-SdkTool "signtool.exe"
$cert = New-SelfSignedCertificate -Type Custom -Subject $Publisher -KeyUsage DigitalSignature -FriendlyName "SDrop test" `
        -CertStoreLocation "Cert:\CurrentUser\My" -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3","2.5.29.19={text}")
& $signtool sign /fd SHA256 /sha1 $cert.Thumbprint $msix
if ($LASTEXITCODE -ne 0) { throw "signtool failed" }
Write-Host "DONE (signed test package): $msix"
