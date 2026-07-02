#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cache_root="$repo_root/.cache"

export AGENT_REPO_ROOT="${AGENT_REPO_ROOT:-$repo_root}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$cache_root/xdg-cache}"
export TMPDIR="${TMPDIR:-$cache_root/tmp}"

export UV_CACHE_DIR="${UV_CACHE_DIR:-$cache_root/uv}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$cache_root/pip}"
export PRE_COMMIT_HOME="${PRE_COMMIT_HOME:-$cache_root/pre-commit}"
export RUFF_CACHE_DIR="${RUFF_CACHE_DIR:-$cache_root/ruff}"
export npm_config_cache="${npm_config_cache:-$cache_root/npm}"

mkdir -p \
  "$XDG_CACHE_HOME" \
  "$TMPDIR" \
  "$UV_CACHE_DIR" \
  "$PIP_CACHE_DIR" \
  "$PRE_COMMIT_HOME" \
  "$RUFF_CACHE_DIR" \
  "$npm_config_cache"

if [[ $# -eq 0 ]]; then
  printf '%s\n' \
    "AGENT_REPO_ROOT=$AGENT_REPO_ROOT" \
    "XDG_CACHE_HOME=$XDG_CACHE_HOME" \
    "TMPDIR=$TMPDIR" \
    "UV_CACHE_DIR=$UV_CACHE_DIR" \
    "PIP_CACHE_DIR=$PIP_CACHE_DIR" \
    "PRE_COMMIT_HOME=$PRE_COMMIT_HOME" \
    "RUFF_CACHE_DIR=$RUFF_CACHE_DIR" \
    "npm_config_cache=$npm_config_cache"
  exit 0
fi

exec "$@"
