#!/usr/bin/env bash
# Fetch ffmpeg/ffprobe into tools/ffmpeg/ for macOS/Linux beta builds.
# BETA / UNTESTED — maintainer does not verify these platforms.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/tools/ffmpeg"
mkdir -p "$DEST"

if [[ -x "$DEST/ffmpeg" && -x "$DEST/ffprobe" ]]; then
  echo "[ffmpeg] Already present in tools/ffmpeg - skipping download."
  exit 0
fi

OS="$(uname -s)"
ARCH="$(uname -m)"
TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "[ffmpeg] BETA fetch for $OS/$ARCH (untested by maintainer)"

if [[ "$OS" == "Linux" ]]; then
  # Static amd64 build; arm64 falls back to PATH if URL layout differs.
  URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
  if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
    URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
  fi
  ARCHIVE="$TMP/ffmpeg.tar.xz"
  curl -L --fail -o "$ARCHIVE" "$URL"
  tar -xJf "$ARCHIVE" -C "$TMP"
  BIN_DIR="$(find "$TMP" -type f -name ffmpeg -perm -111 | head -n1 | xargs dirname)"
  cp -f "$BIN_DIR/ffmpeg" "$BIN_DIR/ffprobe" "$DEST/"
  chmod +x "$DEST/ffmpeg" "$DEST/ffprobe"
elif [[ "$OS" == "Darwin" ]]; then
  if command -v brew >/dev/null 2>&1; then
    brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
    FF="$(brew --prefix ffmpeg)/bin/ffmpeg"
    FP="$(brew --prefix ffmpeg)/bin/ffprobe"
    cp -f "$FF" "$FP" "$DEST/"
    chmod +x "$DEST/ffmpeg" "$DEST/ffprobe"
  else
    echo "[ffmpeg] Homebrew not found. Install ffmpeg and copy binaries to tools/ffmpeg/" >&2
    echo "  brew install ffmpeg" >&2
    exit 1
  fi
else
  echo "[ffmpeg] Unsupported OS: $OS (use scripts/fetch_ffmpeg.ps1 on Windows)" >&2
  exit 1
fi

echo "[ffmpeg] Done. Bundled: $DEST/ffmpeg"
