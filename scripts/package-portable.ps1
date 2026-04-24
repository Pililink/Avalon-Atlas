# Avalon-Atlas portable packaging script.

param(
    [string]$Version = "2.0.0"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

Write-Host "=== Avalon-Atlas Portable Packaging ===" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor Green
Write-Host ""

Write-Host "[1/5] Building release executable..." -ForegroundColor Yellow
npm run tauri build -- --no-bundle
if ($LASTEXITCODE -ne 0) {
    throw "Build failed"
}

$ReleaseDir = Join-Path $Root "build\target\release"
$FrontendStaticDir = Join-Path $Root "build\frontend\static"
$ExePath = Join-Path $ReleaseDir "avalon-atlas.exe"
if (-not (Test-Path $ExePath)) {
    throw "Executable not found: $ExePath"
}
if (-not (Test-Path $FrontendStaticDir)) {
    throw "Frontend static files not found: $FrontendStaticDir"
}

$PackageRoot = Join-Path $Root "build\portable"
$PackageDir = Join-Path $PackageRoot "avalon-atlas-v$Version-portable"
$ZipPath = Join-Path $PackageRoot "avalon-atlas-v$Version-portable.zip"

Write-Host "[2/5] Preparing package directory..." -ForegroundColor Yellow
if (Test-Path $PackageDir) {
    Remove-Item -Recurse -Force $PackageDir
}
New-Item -ItemType Directory -Path $PackageDir | Out-Null

Write-Host "[3/5] Copying runtime files..." -ForegroundColor Yellow
Copy-Item $ExePath -Destination (Join-Path $PackageDir "avalon-atlas.exe")
$ReleaseConfig = Join-Path $ReleaseDir "config.json"
$RootConfig = Join-Path $Root "config.json"
if (Test-Path $ReleaseConfig) {
    Copy-Item $ReleaseConfig -Destination (Join-Path $PackageDir "config.json")
} elseif (Test-Path $RootConfig) {
    Copy-Item $RootConfig -Destination (Join-Path $PackageDir "config.json")
}
Copy-Item -Recurse $FrontendStaticDir -Destination (Join-Path $PackageDir "static")
Copy-Item -Recurse (Join-Path $ReleaseDir "binaries") -Destination (Join-Path $PackageDir "binaries")
New-Item -ItemType Directory -Path (Join-Path $PackageDir "logs") -Force | Out-Null

$Readme = @"
# Avalon-Atlas v$Version Portable

Run avalon-atlas.exe directly.

Hotkeys:
- Ctrl+Shift+Q: Mouse OCR
- Ctrl+Shift+W: Region OCR

Runtime files:
- static/data/maps.json
- static/maps/*.webp
- binaries/tesseract/
- binaries/tessdata/
- logs/
"@
Set-Content -Path (Join-Path $PackageDir "README.txt") -Value $Readme -Encoding UTF8

Write-Host "[4/5] Creating archive..." -ForegroundColor Yellow
if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath -CompressionLevel Optimal

Write-Host "[5/5] Done" -ForegroundColor Yellow
$ZipSizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
Write-Host "Archive: $ZipPath ($ZipSizeMB MB)" -ForegroundColor Green
