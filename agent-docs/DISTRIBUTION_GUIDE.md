# Distribution Guide — All-in-One SMK (Windows)

SMK is distributed as **one self-contained package**. End users install or unzip once and run `SMK.exe`. They never install Python, ffmpeg, pip, or other tools.

## What is bundled

| Component | Purpose |
|-----------|---------|
| Python runtime | App execution (inside PyInstaller build) |
| PyQt5 + Qt WebEngine | GUI + in-app GPS map |
| ffmpeg + ffprobe | Video overlays, repair, GPS read |
| Pillow, mutagen, exif | Metadata embed |
| folium + assets | Map HTML generation |

## Build (release maintainer only)

```powershell
powershell -ExecutionPolicy Bypass -File .\build_smk.ps1
```

This script:

1. Creates/uses `.venv` (developers only — not shipped)
2. Downloads ffmpeg into `tools/ffmpeg/` if missing
3. Runs `pyinstaller smd.spec`
4. Copies ffmpeg beside `dist/smd/SMK.exe`

**Output:** `dist/smd/` — zip this folder or compile `smk_installer.iss` with Inno Setup.

## Release checklist

- [ ] `dist/smd/SMK.exe` launches without console window
- [ ] About dialog shows ffmpeg: **Bundled**
- [ ] Bundled export: merge + metadata on sample ZIP
- [ ] GPS map tab loads (WebEngine)
- [ ] No prompts to install external software
- [ ] Publish SHA-256 for installer/ZIP
- [ ] Include FFmpeg LGPL notice in release notes (ffmpeg.org/legal.html)

## User messaging

- **Not affiliated with Snap Inc.**
- **All-in-one:** no extra installs
- **Bundled exports (2026+):** works fully offline
- **Link-only exports (legacy JSON with URLs):** not supported - request a new export with media in the ZIP
- **My Eyes Only** not included in Memories export

## Platforms

- **Official:** Windows (`build_smk.ps1` → installer + portable ZIP on GitHub Releases).
- **Beta / untested:** macOS and Linux via `build_smk_unix.sh` or workflow
  `.github/workflows/beta-unix.yml`. Label every artifact clearly
  (`BETA-UNTESTED`). Do **not** call these official releases.
- **Not planned:** iOS / Android (desktop app only).

## Trust / SmartScreen (GitHub only)

**Decision (2026-08):** distribute via **GitHub Releases only**. No Microsoft Store,
no paid Authenticode cert, no ID/selfie onboarding. The app stays offline and
independent of Microsoft’s store/account pipeline.

Unsigned builds may show SmartScreen (“unknown publisher”). That is expected.
Document it in README + release notes; users use **More info → Run anyway** if
they trust this repo. Always publish SHA-256.

If someone later wants to fund a code signing cert (no Store), sign `SMK.exe` +
the Inno setup and ship a new release with new hashes. Not planned by the maintainer.
