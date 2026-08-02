# Snapchat Memories Keeper — Linux **BETA (untested)**

> **This is not the official product.**  
> Official SMK is **Windows-only**: https://github.com/LasHSHS/SMK  
> This repository is an **isolated copy** for contributors to experiment with Linux packaging.
>
> **Status:** built in CI / local scripts only. **Not tested or confirmed** by the maintainer.  
> We do not know whether it works. Expect crashes, missing map/WebEngine, or ffmpeg issues.  
> Use at your own risk. Prefer the Windows release for real Memories exports.

## Why a separate repo?

So Linux work cannot break the Windows tree. Do **not** treat this as the source of truth for the pipeline. Fix Linux here; propose carefully reviewed ports back to Windows only when solid.

## Build (on Linux)

```bash
chmod +x build_smk_unix.sh scripts/fetch_ffmpeg.sh
./build_smk_unix.sh
```

System packages vary by distro (Qt/X11 libs). CI uses Ubuntu 22.04 deps as a starting point.

Output: `dist/smd/SMK` plus `BETA_UNTESTED_README.txt`.

Or run GitHub Action **Beta Linux build (untested)** → Artifacts.

## Version

Beta line: **0.1.0-beta** (independent of Windows 1.x numbering).

## Contributing

Help welcome: packaging (AppImage/Flatpak later), real Linux testing, bug reports.  
See `CONTRIBUTING.md`. Parent product docs: Windows repo `agent-docs/`.

## License

Same as Windows SMK (GPLv3) — see `LICENSE` / `NOTICE`.
