#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
api_project="$repo_root/apps/api"

export UV_CACHE_DIR="${UV_CACHE_DIR:-$repo_root/.cache/uv}"

if [[ $# -eq 0 ]]; then
  exec uv run --project "$api_project"
fi

if [[ "$1" == "uv" ]]; then
  shift
  exec uv "$@"
fi

exec uv run --project "$api_project" "$@"
