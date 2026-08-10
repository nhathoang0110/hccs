#!/usr/bin/env bash
#
# install.sh — install `hccs` into ~/.local/bin and make sure it is on PATH.
#
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin"

case "$(uname -s)" in
  Darwin | Linux) ;;
  *) echo "hccs supports macOS and Linux only (detected: $(uname -s))" >&2; exit 1 ;;
esac
[ -f "$SRC_DIR/hccs" ] || { echo "'hccs' not found next to install.sh" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || echo "WARNING: 'python3' is missing — hccs needs it to read config (Ubuntu: sudo apt install python3)" >&2

mkdir -p "$BIN"
install -m 0755 "$SRC_DIR/hccs" "$BIN/hccs"
echo "Installed: $BIN/hccs"

# Claudex / CLIProxyAPI helpers (sourced by hccs at runtime)
SHARE="${HCCS_SHARE:-$HOME/.local/share/hccs}"
mkdir -p "$SHARE"
if [ -f "$SRC_DIR/hccs-proxy.lib" ]; then
  install -m 0644 "$SRC_DIR/hccs-proxy.lib" "$SHARE/hccs-proxy.lib"
  # Also keep a copy next to the bin for repo-style layouts / npm global prefix.
  install -m 0644 "$SRC_DIR/hccs-proxy.lib" "$BIN/hccs-proxy.lib"
  echo "Installed: hccs-proxy.lib"
fi

# Optional helper: sync sessions from the `ccs` tool into hccs (if present in the repo)
if [ -f "$SRC_DIR/sync-from-ccs.sh" ]; then
  install -m 0755 "$SRC_DIR/sync-from-ccs.sh" "$BIN/hccs-sync-ccs"
  echo "Installed: $BIN/hccs-sync-ccs (sync sessions from ccs)"
fi

# Attribution hook: records (session, account) on every claude start → dashboard usage.
if [ -f "$SRC_DIR/hccs-attribution-hook" ]; then
  install -m 0755 "$SRC_DIR/hccs-attribution-hook" "$BIN/hccs-attribution-hook"
  echo "Installed: $BIN/hccs-attribution-hook"
  # Register it in ~/.claude/settings.json (idempotent). Best-effort: a failure
  # does not block the install.
  if "$BIN/hccs" setup-hook; then :; else
    echo "WARNING: setup-hook failed — run 'hccs setup-hook' manually later." >&2
  fi
fi

# Dashboard runtime: python engine + self-contained UI
if [ -f "$SRC_DIR/hccs-dashboard.py" ]; then
  mkdir -p "$SHARE"
  install -m 0644 "$SRC_DIR/hccs-dashboard.py" "$SHARE/hccs-dashboard.py"
  [ -f "$SRC_DIR/dashboard/index.html" ] && install -m 0644 "$SRC_DIR/dashboard/index.html" "$SHARE/index.html"
  echo "Installed: $SHARE (dashboard — run 'hccs dashboard')"
fi

# Make sure ~/.local/bin is on PATH
case ":$PATH:" in
  *":$BIN:"*)
    echo "PATH already contains ~/.local/bin — 'hccs' is ready."
    ;;
  *)
    # Detect the USER's login shell (not the shell running this script, which is always bash).
    case "${SHELL:-}" in
      */zsh)  rc="$HOME/.zshrc" ;;
      */bash) rc="$HOME/.bashrc" ;;
      *)      rc="$HOME/.zshrc" ;;   # macOS default is zsh
    esac
    if grep -q '# hccs$' "$rc" 2>/dev/null; then
      echo "hccs PATH line already present in $rc."
    else
      # Write literal $HOME/$PATH into the rc file (expanded at shell load, not now).
      # shellcheck disable=SC2016
      printf '\nexport PATH="$HOME/.local/bin:$PATH" # hccs\n' >>"$rc"
      echo "Added ~/.local/bin to PATH in $rc."
    fi
    echo "Open a new terminal or run:  source $rc"
    ;;
esac

echo
echo "Get started:  hccs add <account>"
