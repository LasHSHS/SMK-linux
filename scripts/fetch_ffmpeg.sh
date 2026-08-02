#!/usr/bin/env bash
# Fetch ffmpeg/ffprobe into tools/ffmpeg/ for Linux/macOS beta builds.
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
  # Prefer distro packages when available (reliable on Ubuntu CI).
  if command -v apt-get >/dev/null 2>&1; then
    if command -v sudo >/dev/null 2>&1; then
      sudo apt-get update -qq
      sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg
    else
      apt-get update -qq
      DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg
    fi
    cp -f "$(command -v ffmpeg)" "$(command -v ffprobe)" "$DEST/"
    chmod +x "$DEST/ffmpeg" "$DEST/ffprobe"
  else
    # Fallback: BtbN static GPL build from GitHub Releases.
    case "$ARCH" in
      x86_64|amd64) ASSET="ffmpeg-master-latest-linux64-gpl.tar.xz" ;;
      aarch64|arm64) ASSET="ffmpeg-master-latest-linuxarm64-gpl.tar.xz" ;;
      *)
        echo "[ffmpeg] Unsupported Linux arch: $ARCH" >&2
        exit 1
        ;;
    esac
    URL="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/${ASSET}"
    ARCHIVE="$TMP/ffmpeg.tar.xz"
    curl -L --fail --retry 3 -o "$ARCHIVE" "$URL"
    # Reject tiny/HTML error pages (johnvansickle-style failures).
    SIZE="$(wc -c < "$ARCHIVE" | tr -d ' ')"
    if [[ "$SIZE" -lt 1000000 ]]; then
      echo "[ffmpeg] Download too small ($SIZE bytes) — not a real archive: $URL" >&2
      exit 1
    fi
    tar -xJf "$ARCHIVE" -C "$TMP"
    BIN_DIR="$(find "$TMP" -type f -name ffmpeg -perm -111 | head -n1 | xargs dirname)"
    cp -f "$BIN_DIR/ffmpeg" "$BIN_DIR/ffprobe" "$DEST/"
    chmod +x "$DEST/ffmpeg" "$DEST/ffprobe"
  fi
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
  echo "[ffmpeg] Unsupported OS: $OS" >&2
  exit 1
fi

echo "[ffmpeg] Done. Bundled: $DEST/ffmpeg"
