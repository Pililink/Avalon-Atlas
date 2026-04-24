# Avalon-Atlas Portable Packaging Script
# Generates zip archive: exe + resource files

param(
    [string]$Version = "2.0.0"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Avalon-Atlas Portable Packaging ===" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor Green
Write-Host ""

# 1. Build Release version
Write-Host "[1/5] Building Release version..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\.."
npm run tauri build

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# 2. Create package directory
$PackageDir = ".\dist\portable\avalon-atlas-v$Version-portable"
Write-Host "[2/5] Creating package directory: $PackageDir" -ForegroundColor Yellow

if (Test-Path $PackageDir) {
    Remove-Item -Recurse -Force $PackageDir
}
New-Item -ItemType Directory -Path $PackageDir | Out-Null

# 3. Copy executable
Write-Host "[3/5] Copying executable..." -ForegroundColor Yellow
$ExePath = ".\backend\target\release\avalon-atlas.exe"

if (-not (Test-Path $ExePath)) {
    Write-Host "Error: Executable not found at $ExePath" -ForegroundColor Red
    exit 1
}

Copy-Item $ExePath -Destination "$PackageDir\avalon-atlas.exe"
$ExeSizeMB = [math]::Round((Get-Item $ExePath).Length / 1MB, 2)
Write-Host "  OK avalon-atlas.exe ($ExeSizeMB MB)" -ForegroundColor Green

# 4. Copy resource files
Write-Host "[4/5] Copying resource files..." -ForegroundColor Yellow

# Copy resources directory
Copy-Item -Recurse ".\resources" -Destination "$PackageDir\resources" -Exclude ".omc"
# Remove .omc directory if it was copied
if (Test-Path "$PackageDir\resources\models\.omc") {
    Remove-Item -Recurse -Force "$PackageDir\resources\models\.omc"
}
Write-Host "  OK resources/ (config, models, data)" -ForegroundColor Green

# Write default config template (app will also auto-generate on first run)
$DefaultConfig = @"
{
  "mouse_hotkey": "ctrl+shift+q",
  "chat_hotkey": "ctrl+shift+w",
  "ocr_debug": true,
  "log_level": "info",
  "ocr_region": {
    "width": 650,
    "height": 75,
    "vertical_offset": 0,
    "horizontal_offset": 0
  },
  "always_on_top": false,
  "debounce_ms": 200,
  "selected_monitor": 0
}
"@
Set-Content -Path "$PackageDir\config.json" -Value $DefaultConfig -Encoding UTF8
Write-Host "  OK config.json (default template)" -ForegroundColor Green

# Create README
$ReadmeContent = @"
# Avalon-Atlas v$Version - Portable Edition

## Directory Structure

avalon-atlas-v$Version-portable/
├── avalon-atlas.exe          # Main program
├── config.json                # Configuration file
└── resources/                 # Runtime resources
    ├── data/                  # Data files
    │   └── maps.json
    └── models/                # OCR model files
        ├── text-detection.rten    (2.4 MB)
        └── text-recognition.rten  (9.3 MB)

## Usage

1. **Run directly**
   Double-click avalon-atlas.exe to start

2. **Hotkeys**
   - Ctrl+Shift+Q: Mouse region OCR
   - Ctrl+Shift+W: Custom region OCR

3. **Configuration**
   Edit config.json

## System Requirements

- Windows 10/11 (64-bit)
- At least 100 MB free disk space

## Notes

- First run may require administrator privileges (for global hotkey registration)
- Ensure resources/models/ directory contains complete model files
- Log files are saved to logs/ directory

## Technical Stack

- Backend: Rust + Tauri 2.0
- Frontend: Svelte 5 + TypeScript
- OCR: RapidOCR (ocrs)
- Capture: Win32 API + screenshots

## Version Info

- Version: $Version
- Build Date: $(Get-Date -Format 'yyyy-MM-dd')
- Architecture: x86_64-pc-windows-msvc

## Changelog

### v2.0.0 (2026-02-22)
- Complete refactor based on MaaEnd architecture
- Removed Tesseract dependency, using RapidOCR only
- Implemented config-driven recognition pipeline
- Enhanced logging system with file output
- Optimized UI/UX with modern glass design
- Implemented fullscreen region selection OCR
- Multi-monitor support

## License

MIT License
"@

Set-Content -Path "$PackageDir\README.txt" -Value $ReadmeContent -Encoding UTF8
Write-Host "  OK README.txt" -ForegroundColor Green

# 5. Create zip archive
Write-Host "[5/5] Creating zip archive..." -ForegroundColor Yellow
$ZipPath = ".\dist\portable\avalon-atlas-v$Version-portable.zip"

if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}

Compress-Archive -Path "$PackageDir\*" -DestinationPath $ZipPath -CompressionLevel Optimal

$ZipSizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
Write-Host "  OK $ZipPath ($ZipSizeMB MB)" -ForegroundColor Green

# Complete
Write-Host ""
Write-Host "=== Packaging Complete ===" -ForegroundColor Cyan
Write-Host "Archive location: $ZipPath" -ForegroundColor Green
Write-Host "Extract and run - no installation required" -ForegroundColor Green
Write-Host ""

# Display file list
Write-Host "Package contents:" -ForegroundColor Yellow
Get-ChildItem -Recurse $PackageDir | Select-Object FullName | ForEach-Object {
    $RelPath = $_.FullName.Replace("$PackageDir\", "")
    Write-Host "  - $RelPath" -ForegroundColor Gray
}
