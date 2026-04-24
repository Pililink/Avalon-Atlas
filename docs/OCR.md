# OCR

Avalon Atlas uses bundled Tesseract binaries for local OCR. No game account credentials are required, and OCR processing runs on the user's machine.

## Modes

### Mouse OCR

Default hotkey:

```text
Ctrl+Shift+Q
```

Mouse OCR captures a small region near the cursor and tries to match the recognized text against the known map-name dataset. If no confident map match is found, the app should not select unrelated maps.

Default capture configuration:

```json
{
  "width": 590,
  "height": 30,
  "vertical_offset": 50
}
```

### Region OCR

Default hotkey:

```text
Ctrl+Shift+W
```

Region OCR opens a selection overlay. The selected image is recognized once and then matched against known map names.

## Debug Files

When `ocr_debug` is enabled, OCR screenshots and diagnostic logs are written under:

```text
logs/
```

In the portable package this directory is next to `avalon-atlas.exe`.

## Runtime Files

Required OCR files:

```text
binaries/tesseract/tesseract.exe
binaries/tessdata/eng.traineddata
```

During development the backend resolves these from `src-tauri/binaries/`. In portable releases they are copied into the package's `binaries/` directory.

## Troubleshooting

If OCR fails:

- Confirm the map text is fully inside the captured region.
- Enable OCR debug image saving and inspect the saved image.
- Check `logs/avalon-atlas.log`.
- Confirm the portable package contains `binaries/tesseract/` and `binaries/tessdata/`.
- Try region OCR if mouse OCR does not capture the expected area.

When reporting OCR issues, attach the debug image and the relevant log lines when possible.
