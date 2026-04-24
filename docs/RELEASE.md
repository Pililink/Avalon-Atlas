# Release

Avalon Atlas releases are published through GitHub Actions as Windows portable packages.

## Versioning

Before publishing, the version must match in all three files:

```text
package.json
src-tauri/tauri.conf.json
src-tauri/Cargo.toml
```

Use semantic versions such as:

```text
2.0.1
2.1.0
2.1.0-beta.1
```

Git tags must use the `v` prefix:

```text
v2.0.1
```

## Local Checks

Run:

```bash
npm run check
cargo test --manifest-path src-tauri/Cargo.toml
```

For release and packaging changes, also run:

```bash
npm run package:portable
```

Expected portable outputs:

```text
build/portable/avalon-atlas-v<version>-portable/
build/portable/avalon-atlas-v<version>-portable.zip
```

## Publish

After committing the version changes:

```bash
git tag v2.0.1
git push origin main
git push origin v2.0.1
```

The `Release` workflow will:

- Install Node and Rust dependencies.
- Validate version consistency.
- Run `npm run check`.
- Build the portable package.
- Verify required runtime files.
- Create a GitHub Release.
- Upload `avalon-atlas-v<version>-portable.zip`.

## Post-Release Verification

After GitHub Actions completes:

- Confirm the workflow succeeded.
- Download the release zip from GitHub.
- Extract it into a clean directory.
- Run `avalon-atlas.exe`.
- Confirm search, selected map preview, settings, and OCR hotkeys work.
- Confirm `logs/` is created next to the executable.

## Rollback

If a release is broken:

- Mark the GitHub Release as pre-release or delete it.
- Do not reuse the same version for a fixed build.
- Publish a new patch version.
