#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-2.0.0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Avalon-Atlas Portable Packaging ==="
echo "Version: $VERSION"
echo

echo "[1/5] Building release executable..."
npm run tauri build -- --no-bundle

RELEASE_DIR="$ROOT/build/target/release"
FRONTEND_STATIC_DIR="$ROOT/build/frontend/static"
EXE_PATH="$RELEASE_DIR/avalon-atlas.exe"
if [ ! -f "$EXE_PATH" ]; then
  echo "Executable not found: $EXE_PATH" >&2
  exit 1
fi
if [ ! -d "$FRONTEND_STATIC_DIR" ]; then
  echo "Frontend static files not found: $FRONTEND_STATIC_DIR" >&2
  exit 1
fi

PACKAGE_ROOT="$ROOT/build/portable"
PACKAGE_DIR="$PACKAGE_ROOT/avalon-atlas-v${VERSION}-portable"
ZIP_PATH="$PACKAGE_ROOT/avalon-atlas-v${VERSION}-portable.zip"

echo "[2/5] Preparing package directory..."
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

echo "[3/5] Copying runtime files..."
cp "$EXE_PATH" "$PACKAGE_DIR/avalon-atlas.exe"
if [ -f "$RELEASE_DIR/config.json" ]; then
  cp "$RELEASE_DIR/config.json" "$PACKAGE_DIR/config.json"
elif [ -f "$ROOT/config.json" ]; then
  cp "$ROOT/config.json" "$PACKAGE_DIR/config.json"
fi
cp -r "$FRONTEND_STATIC_DIR" "$PACKAGE_DIR/static"
cp -r "$RELEASE_DIR/binaries" "$PACKAGE_DIR/binaries"
mkdir -p "$PACKAGE_DIR/logs"

cat > "$PACKAGE_DIR/README.txt" << EOF
# Avalon-Atlas v$VERSION Portable

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
EOF

echo "[4/5] Creating archive..."
rm -f "$ZIP_PATH"
(cd "$PACKAGE_ROOT" && zip -r "$(basename "$ZIP_PATH")" "$(basename "$PACKAGE_DIR")" >/dev/null)

echo "[5/5] Done"
echo "Archive: $ZIP_PATH"
