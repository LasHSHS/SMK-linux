#!/usr/bin/env bash
# Build SMK portable folder on macOS or Linux (PyInstaller).
#
# *** BETA / UNTESTED ***
# The maintainer does not have reliable macOS or Linux test coverage.
# These builds are experimental. Do not treat them as production releases.
# Official supported platform remains Windows 10/11.
#
# Usage (from repo root):
#   chmod +x build_smk_unix.sh scripts/fetch_ffmpeg.sh
#   ./build_smk_unix.sh
#
# Output: dist/smd/SMK  (plus _internal / tools as produced by smd.spec)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

OS="$(uname -s)"
echo "[SMK BETA] Building experimental package for $OS"
echo "[SMK BETA] NOT tested or confirmed by the maintainer."

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install pyinstaller -r requirements.txt

bash scripts/fetch_ffmpeg.sh
if [[ ! -x tools/ffmpeg/ffmpeg ]]; then
  echo "[SMK BETA] ffmpeg missing under tools/ffmpeg after fetch." >&2
  exit 1
fi

rm -rf dist build
pyinstaller smd.spec --noconfirm --clean

DIST_FFMPEG="dist/smd/tools/ffmpeg"
mkdir -p "$DIST_FFMPEG"
cp -f tools/ffmpeg/* "$DIST_FFMPEG/" 2>/dev/null || true
if [[ -d dist/smd/_internal ]]; then
  mkdir -p dist/smd/_internal/tools/ffmpeg
  cp -f tools/ffmpeg/* dist/smd/_internal/tools/ffmpeg/ 2>/dev/null || true
fi

# Drop a loud banner so nobody mistakes this for a supported release.
cat > dist/smd/BETA_UNTESTED_README.txt <<'EOF'
Snapchat Memories Keeper (SMK) — BETA build for macOS / Linux

THIS BUILD IS EXPERIMENTAL AND UNTESTED by the maintainer.
Official support is Windows 10/11 only.

- Not confirmed on real Mac or Linux workflows
- May crash, miss WebEngine/map features, or fail ffmpeg merges
- No warranty; use at your own risk
- Please report issues: https://github.com/LasHSHS/SMK/issues
- Contributions welcome (see CONTRIBUTING.md)

Run: ./SMK   (macOS/Linux) from this folder
EOF

echo "[SMK BETA] Done: dist/smd/SMK"
echo "[SMK BETA] Read dist/smd/BETA_UNTESTED_README.txt before distributing."
