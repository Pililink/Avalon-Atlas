# Architecture

Avalon Atlas is a Tauri v2 desktop app with a Svelte frontend and a Rust backend.

## Runtime Layout

```text
Avalon-Atlas/
├── src/                    # Svelte UI
├── src-tauri/              # Rust backend and Tauri configuration
├── public/static/          # Map data, map previews, and UI assets
├── scripts/                # Packaging scripts
└── build/                  # Generated local build output
```

## Frontend

The frontend is responsible for:

- Compact assistant panel UI.
- Search input and result display.
- Selected-map list and map preview behavior.
- Settings dialog and language switching.
- Calling Tauri commands through `src/lib/tauri/`.

Important paths:

- `src/App.svelte`
- `src/components/`
- `src/lib/i18n/`
- `src/lib/maps/`
- `src/lib/tauri/`

## Backend

The Rust backend is responsible for:

- Loading map data.
- Fuzzy map search.
- Tesseract OCR execution.
- Screenshot capture and OCR image preparation.
- Global hotkey registration.
- Config persistence.
- Logging to the executable-side `logs/` directory.

Important paths:

- `src-tauri/src/main.rs`
- `src-tauri/src/commands/`
- `src-tauri/src/models/`
- `src-tauri/src/services/`
- `src-tauri/src/utils/`

## Data And Assets

Map metadata:

```text
public/static/data/maps.json
```

Map previews:

```text
public/static/maps/
```

UI assets:

```text
public/static/assets/
```

OCR runtime:

```text
src-tauri/binaries/tesseract/
src-tauri/binaries/tessdata/
```

## Build Outputs

Cargo/Tauri target output is redirected to the repository-level `build/target` directory through `.cargo/config.toml`.

Common outputs:

```text
build/frontend/
build/target/release/avalon-atlas.exe
build/portable/avalon-atlas-v<version>-portable/
build/portable/avalon-atlas-v<version>-portable.zip
```

Only `build/portable/avalon-atlas-v<version>-portable.zip` is intended for GitHub Release distribution.
