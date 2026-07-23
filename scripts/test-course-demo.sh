#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=course-demo.sh
source "$repo_root/scripts/course-demo.sh"

fail() {
  printf 'Course demo test failed: %s\n' "$*" >&2
  return 1
}

test_failed_deploy_reports_unconfirmed_public_access() {
  local output status

  compose_for_cleanup() {
    return 1
  }
  tunnel_container_id() {
    printf 'still-running'
  }

  set +e
  output="$(stop_public_access_after_failed_deploy 2>&1)"
  status=$?
  set -e

  [[ "$status" -ne 0 ]] \
    || fail "an unconfirmed tunnel stop must return failure"
  [[ "$output" == *"PUBLIC ACCESS MAY STILL BE ACTIVE"* ]] \
    || fail "an unconfirmed tunnel stop must emit the public-access warning"
  [[ "$output" != *"tunnel is stopped"* ]] \
    || fail "an unconfirmed tunnel stop must not claim success"
}

test_failed_deploy_verifies_no_tunnel_remains_running() {
  local output status

  compose_for_cleanup() {
    return 0
  }
  tunnel_container_id() {
    printf 'still-running'
  }

  set +e
  output="$(stop_public_access_after_failed_deploy 2>&1)"
  status=$?
  set -e

  [[ "$status" -ne 0 ]] \
    || fail "a still-running tunnel must make cleanup return failure"
  [[ "$output" == *"PUBLIC ACCESS MAY STILL BE ACTIVE"* ]] \
    || fail "a still-running tunnel must emit the public-access warning"
}

test_failed_deploy_reports_confirmed_tunnel_stop() {
  local output

  compose_for_cleanup() {
    return 0
  }
  tunnel_container_id() {
    return 0
  }

  output="$(stop_public_access_after_failed_deploy 2>&1)"

  [[ "$output" == *"tunnel is confirmed stopped"* ]] \
    || fail "a verified tunnel stop must report confirmation"
  [[ "$output" != *"PUBLIC ACCESS MAY STILL BE ACTIVE"* ]] \
    || fail "a verified tunnel stop must not emit the public-access warning"
}

test_worker_probe_targets_the_current_container() {
  compose_for_cleanup() {
    [[ "$1" == "exec" && "$2" == "-T" && "$3" == "worker" ]] \
      || return 1
    [[ "${6:-}" == *'--destination "celery@$HOSTNAME"'* ]] \
      || return 1
    printf '%s\n' \
      '-> celery@course-demo-worker: OK' \
      '        pong' \
      '1 node online.'
  }

  worker_is_ready \
    || fail "the worker probe must target the current container's Celery node"
}

test_tunnel_cache_refuses_symlink_boundaries() (
  local temporary scenario scenario_root outside output status

  temporary="$(mktemp -d "${TMPDIR:-/tmp}/competehub-tunnel-cache-check.XXXXXX")"
  trap 'rm -rf -- "$temporary"' EXIT

  uname() {
    printf '%s\n' x86_64
  }
  docker() {
    case "${1:-}" in
      info) printf '%s\n' amd64 ;;
      *) return 97 ;;
    esac
  }
  curl() {
    return 98
  }
  sha256sum() {
    return 99
  }

  for scenario in cache-root cache-directory binary; do
    scenario_root="$temporary/$scenario/repo"
    outside="$temporary/$scenario/outside"
    mkdir -p "$scenario_root" "$outside"
    repo_root="$scenario_root"

    case "$scenario" in
      cache-root)
        ln -s "$outside" "$repo_root/.cache"
        ;;
      cache-directory)
        mkdir -p "$repo_root/.cache"
        ln -s "$outside" "$repo_root/.cache/course-demo-tunnel"
        ;;
      binary)
        mkdir -p "$repo_root/.cache/course-demo-tunnel"
        : >"$outside/cloudflared"
        ln -s "$outside/cloudflared" \
          "$repo_root/.cache/course-demo-tunnel/cloudflared"
        ;;
    esac

    set +e
    output="$(build_tunnel 2>&1)"
    status=$?
    set -e

    [[ "$status" -ne 0 ]] \
      || fail "build_tunnel must reject the $scenario symlink boundary"
    [[ "$output" == *symlink* ]] \
      || fail "the $scenario refusal must identify the symlink boundary"
  done
)

test_tunnel_cache_cleans_failed_download() (
  local temporary output_path output status

  temporary="$(mktemp -d "${TMPDIR:-/tmp}/competehub-tunnel-download-check.XXXXXX")"
  trap 'rm -rf -- "$temporary"' EXIT
  repo_root="$temporary/repo"
  mkdir -p "$repo_root"

  uname() {
    printf '%s\n' x86_64
  }
  docker() {
    case "${1:-}" in
      info) printf '%s\n' amd64 ;;
      *) return 97 ;;
    esac
  }
  curl() {
    output_path=""
    while (( $# > 0 )); do
      case "$1" in
        --output)
          output_path="$2"
          shift 2
          ;;
        *)
          shift
          ;;
      esac
    done
    [[ -n "$output_path" ]] || return 96
    printf 'partial download\n' >"$output_path"
    return 98
  }
  sha256sum() {
    return 99
  }

  set +e
  output="$(build_tunnel 2>&1)"
  status=$?
  set -e

  [[ "$status" -ne 0 ]] || fail "a failed cloudflared download must fail the build"
  [[ ! -e "$repo_root/.cache/course-demo-tunnel/cloudflared" ]] \
    || fail "a failed cloudflared download must not become the cached binary"
  [[ -z "$(compgen -G "$repo_root/.cache/course-demo-tunnel/cloudflared.tmp.*" || true)" ]] \
    || fail "a failed cloudflared download must remove its unique temporary file"
)

test_python_bytecode_is_excluded_from_docker_context() (
  local probe_relative probe_path temporary dockerfile export_dir
  local image_id container_id

  probe_relative="apps/api/src/competehub_api/course_demo_context_probe.pyc"
  probe_path="$repo_root/$probe_relative"
  [[ ! -e "$probe_path" ]] \
    || fail "refusing to overwrite pre-existing probe $probe_path"

  temporary="$(mktemp -d "${TMPDIR:-/tmp}/competehub-context-check.XXXXXX")"
  dockerfile="$temporary/Dockerfile"
  export_dir="$temporary/export"
  image_id=""
  container_id=""
  cleanup() {
    if [[ -n "$container_id" ]]; then
      docker rm "$container_id" >/dev/null 2>&1 || true
    fi
    if [[ -n "$image_id" ]]; then
      docker image rm "$image_id" >/dev/null 2>&1 || true
    fi
    rm -f -- "$probe_path"
    rm -rf -- "$temporary"
  }
  trap cleanup EXIT

  : >"$probe_path"
  git -C "$repo_root" check-ignore --quiet "$probe_relative" \
    || fail "the bytecode probe must be ignored by Git to exercise the release-boundary gap"

  printf '%s\n' \
    'FROM scratch' \
    'COPY apps/api/src /src' \
    'CMD ["/bin/false"]' >"$dockerfile"
  if docker buildx version >/dev/null 2>&1; then
    DOCKER_BUILDKIT=1 docker build \
      --file "$dockerfile" \
      --output "type=local,dest=$export_dir" \
      "$repo_root" >/dev/null
    [[ ! -e "$export_dir/src/competehub_api/course_demo_context_probe.pyc" ]] \
      || fail "Git-ignored Python bytecode entered the Docker build context"
  else
    DOCKER_BUILDKIT=0 docker build \
      --file "$dockerfile" \
      --iidfile "$temporary/image-id" \
      "$repo_root" >/dev/null
    image_id="$(<"$temporary/image-id")"
    container_id="$(docker create "$image_id")"

    if docker cp \
      "$container_id:/src/competehub_api/course_demo_context_probe.pyc" \
      "$temporary/probe-copy" >/dev/null 2>&1; then
      fail "Git-ignored Python bytecode entered the Docker build context"
    fi
  fi
)

main() {
  case "${1:-all}" in
    tunnel-cleanup)
      test_failed_deploy_reports_unconfirmed_public_access
      test_failed_deploy_verifies_no_tunnel_remains_running
      test_failed_deploy_reports_confirmed_tunnel_stop
      ;;
    worker-probe)
      test_worker_probe_targets_the_current_container
      ;;
    tunnel-cache)
      test_tunnel_cache_refuses_symlink_boundaries
      test_tunnel_cache_cleans_failed_download
      ;;
    docker-context)
      test_python_bytecode_is_excluded_from_docker_context
      ;;
    all)
      test_failed_deploy_reports_unconfirmed_public_access
      test_failed_deploy_verifies_no_tunnel_remains_running
      test_failed_deploy_reports_confirmed_tunnel_stop
      test_worker_probe_targets_the_current_container
      test_tunnel_cache_refuses_symlink_boundaries
      test_tunnel_cache_cleans_failed_download
      test_python_bytecode_is_excluded_from_docker_context
      ;;
    *)
      printf 'Usage: %s [all|tunnel-cleanup|worker-probe|tunnel-cache|docker-context]\n' "$0" >&2
      return 1
      ;;
  esac
}

main "$@"
