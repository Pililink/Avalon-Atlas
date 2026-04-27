# Contributing

Thanks for your interest in Avalon Atlas. This project is a compact desktop assistant for Albion Online Avalon road map lookup.

## Before You Start

- Keep changes focused. Small pull requests are easier to review and test.
- Open an issue first for large UI, OCR, data model, packaging, or architecture changes.
- Do not include unrelated formatting churn or generated build artifacts.
- Do not commit local configuration, logs, screenshots, or packaged release outputs.

## Development Setup

Requirements:

- Windows 10/11 64-bit
- Node.js 22 or newer
- Rust stable toolchain
- Microsoft C++ Build Tools / Windows SDK

Install dependencies:

```bash
npm install
```

Run the desktop app:

```bash
npm run tauri dev
```

Run frontend-only development:

```bash
npm run dev
```

## Checks

Run the relevant checks before submitting:

```bash
npm run check
cargo test --manifest-path src-tauri/Cargo.toml
```

For packaging or release changes, also run:

```bash
npm run package:portable
```

## Commit Convention

Prefer a short, focused title with either gitmoji or the existing conventional prefix style.

Recommended gitmoji prefixes:

- `✨` Feature
- `🐛` Bug fix
- `♻️` Refactor
- `🎨` UI or styling
- `⚡️` Performance
- `🔒` Security
- `🔧` Tooling, config, or CI
- `✅` Tests
- `📄` Documentation
- `🚀` Release

Existing titles such as `feat: ...`, `fix: ...`, `docs: ...`, and `chore: ...` are also acceptable. Keep each commit scoped to one logical change and avoid committing generated build output.

## Pull Request Guidelines

- Explain what changed and why.
- Include screenshots or a short video for UI changes.
- Mention the tested platform and commands you ran.
- Keep public-facing text in English unless the change is specifically for localization.
- Update Chinese and English i18n strings together when adding or changing UI text.
- Use the pull request checklist to record `npm run check`, `cargo test --manifest-path src-tauri/Cargo.toml`, and `npm run package:portable` when relevant.
- Redact logs, OCR debug images, screenshots, and sample data before sharing them publicly.

## Issue Guidelines

For bugs, include:

- App version
- Windows version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant log file content from the `logs/` directory

For OCR issues, include:

- Whether mouse OCR or region OCR was used
- Whether OCR debug image saving was enabled
- A cropped screenshot if it does not include private information
