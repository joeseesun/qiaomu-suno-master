#!/usr/bin/env bash
set -euo pipefail

repo_url="https://github.com/paperfoot/suno-cli"
releases_url="https://github.com/paperfoot/suno-cli/releases"
export PATH="$HOME/.cargo/bin:$PATH"

if command -v suno >/dev/null 2>&1; then
  suno --version
  exit 0
fi

if [[ "${SUNO_CLI_AUTO_INSTALL:-1}" == "0" ]]; then
  cat >&2 <<EOF
The 'suno' command is not installed.

Install from the upstream paperfoot/suno-cli project:
  brew tap paperfoot/tap && brew install suno
  cargo install suno --locked
  $releases_url

Set SUNO_CLI_AUTO_INSTALL=1 or omit it to allow this script to install automatically.
EOF
  exit 127
fi

echo "Installing upstream suno CLI from $repo_url" >&2

installed=0

if command -v brew >/dev/null 2>&1; then
  if brew tap paperfoot/tap && brew install suno; then
    installed=1
  else
    cat >&2 <<EOF
Homebrew install failed. Falling back to Cargo when available.
EOF
  fi
fi

if [[ "$installed" -eq 0 ]] && command -v cargo >/dev/null 2>&1; then
  cargo install suno --locked
  installed=1
fi

if [[ "$installed" -eq 0 ]]; then
  if command -v brew >/dev/null 2>&1 && ! command -v cargo >/dev/null 2>&1; then
    cat >&2 <<EOF
Homebrew failed and Cargo is not available.

Install Cargo/Rust, or download a prebuilt binary:
  $releases_url
EOF
  else
    cat >&2 <<EOF
Could not find Homebrew or Cargo.

Install one of them, or download a prebuilt binary:
  $releases_url
EOF
  fi
  exit 127
fi

if ! command -v suno >/dev/null 2>&1; then
  cat >&2 <<EOF
Installation finished, but 'suno' is still not on PATH.

Try:
  export PATH="\$HOME/.cargo/bin:\$PATH"
  suno --version
EOF
  exit 127
fi

suno --version
