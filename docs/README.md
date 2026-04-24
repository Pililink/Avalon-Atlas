# Documentation

This directory contains current maintainer-facing documentation for Avalon Atlas.

## Current Documents

- [Architecture](ARCHITECTURE.md): application layout, frontend/backend responsibilities, data flow, and packaging paths.
- [OCR](OCR.md): mouse OCR, region OCR, debug files, and troubleshooting notes.
- [Release](RELEASE.md): versioning, local packaging, GitHub Actions release flow, and release checklist.
- [GitHub Page Checklist](GITHUB_PAGE_CHECKLIST.md): repository About, topics, social preview, and release page presentation.

## Archived Content

Older planning notes were removed after the Tauri migration. The current project entry points are:

- `src/` for the Svelte frontend.
- `src-tauri/` for the Rust/Tauri backend.
- `public/static/` for map data, previews, and UI assets.
- `scripts/package-portable.ps1` for the Windows portable package.

Use the root [README](../README.md) for user-facing installation and usage instructions.
