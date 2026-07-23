#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_root/infra/course-demo/compose.yml"
env_file="$repo_root/infra/course-demo/.env"
example_env_file="$repo_root/infra/course-demo/.env.example"
project_name="competehub-course-deployment"
deployment_generation="v1"
generation_label="io.competehub.deployment-generation"
postgres_volume="${project_name}_postgres_data"
cloudflared_version="2026.5.2"
cloudflared_sha256="5286698547f03df745adb2355f04c12dde52ef425491e81f433642d695521886"
release_sha_for_compose="local"

usage() {
  printf '%s\n' \
    "Usage: $0 prepare" \
    "       $0 registration enable|disable|status" \
    "       $0 config|config-example|prewarm|migrate|bootstrap-demo|deploy" \
    "       $0 status|url|smoke|logs [service]|stop" \
    "       $0 destroy DESTROY"
}

die() {
  printf 'Deployment v1 refused: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required host command '$1' is unavailable"
}

require_env() {
  [[ ! -L "$env_file" ]] \
    || die "$env_file is a symlink; Deployment v1 reads only an owner-created regular file"
  [[ -f "$env_file" ]] || die "missing $env_file; run '$0 prepare' first"
}

env_value() {
  local key="$1"
  sed -n "s/^${key}=//p" "$env_file"
}

unquote_single_value() {
  local value="$1"
  if [[ "$value" == \'*\' && "$value" == *\' && ${#value} -ge 2 ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

registration_state() {
  if [[ -L "$env_file" ]]; then
    printf 'unsafe-symlink'
    return
  fi
  if [[ ! -f "$env_file" ]]; then
    printf 'not-configured'
    return
  fi
  case "$(env_value PUBLIC_EMAIL_REGISTRATION_ENABLED)" in
    true) printf 'enabled' ;;
    false) printf 'disabled' ;;
    *) printf 'invalid' ;;
  esac
}

validate_env() {
  local secret_key postgres_password local_port
  local registration_enabled sender_dsn

  validate_env_identity
  secret_key="$(env_value SECRET_KEY)"
  postgres_password="$(env_value POSTGRES_PASSWORD)"
  local_port="$(env_value COURSE_DEMO_LOCAL_PORT)"
  registration_enabled="$(env_value PUBLIC_EMAIL_REGISTRATION_ENABLED)"
  sender_dsn="$(unquote_single_value "$(env_value EMAIL_VERIFICATION_SENDER_DSN)")"

  [[ "$secret_key" =~ ^[0-9a-f]{64}$ ]] \
    || die "SECRET_KEY must be one generated 64-character lowercase hex value"
  [[ "$postgres_password" =~ ^[0-9a-f]{48}$ ]] \
    || die "POSTGRES_PASSWORD must be one generated 48-character lowercase hex value"
  if [[ ! "$local_port" =~ ^[0-9]{4,5}$ ]] \
    || (( 10#$local_port < 1024 || 10#$local_port > 65535 )); then
    die "COURSE_DEMO_LOCAL_PORT must be an unprivileged TCP port from 1024 to 65535"
  fi

  case "$registration_enabled" in
    false)
      [[ -z "$sender_dsn" ]] \
        || die "registration is disabled but a sender DSN remains; run '$0 registration disable'"
      ;;
    true)
      [[ "$sender_dsn" == smtp://* || "$sender_dsn" == smtps://* ]] \
        || die "enabled registration requires a private smtp:// or smtps:// sender DSN"
      [[ ! "$sender_dsn" =~ [[:space:]] ]] \
        || die "EMAIL_VERIFICATION_SENDER_DSN must not contain unencoded whitespace"
      ;;
    *)
      die "PUBLIC_EMAIL_REGISTRATION_ENABLED must be exactly true or false"
      ;;
  esac
}

validate_env_identity() {
  local file_mode generation

  require_env
  file_mode="$(stat -c '%a' "$env_file")"
  [[ "$file_mode" == "600" ]] \
    || die "$env_file must have mode 0600; current mode is $file_mode"
  validate_env_schema
  generation="$(env_value DEPLOYMENT_GENERATION)"
  [[ "$generation" == "$deployment_generation" ]] \
    || die "$env_file is not an explicit Deployment $deployment_generation environment"
}

validate_env_schema() {
  local line key required_key
  local -A seen=()
  local -a required_keys=(
    DEPLOYMENT_GENERATION
    SECRET_KEY
    POSTGRES_PASSWORD
    COURSE_DEMO_LOCAL_PORT
    PUBLIC_EMAIL_REGISTRATION_ENABLED
    EMAIL_VERIFICATION_SENDER_DSN
  )

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -n "$line" && "$line" == *=* ]] \
      || die "$env_file must contain only the six required key assignments"
    key="${line%%=*}"
    case "$key" in
      DEPLOYMENT_GENERATION \
        | SECRET_KEY \
        | POSTGRES_PASSWORD \
        | COURSE_DEMO_LOCAL_PORT \
        | PUBLIC_EMAIL_REGISTRATION_ENABLED \
        | EMAIL_VERIFICATION_SENDER_DSN) ;;
      *) die "$env_file contains unknown key '$key'" ;;
    esac
    [[ -z "${seen[$key]+present}" ]] || die "$env_file contains duplicate key '$key'"
    seen["$key"]=1
  done <"$env_file"

  for required_key in "${required_keys[@]}"; do
    [[ -n "${seen[$required_key]+present}" ]] \
      || die "$env_file is missing required key '$required_key'"
  done
}

controlled_compose() (
  local selected_env="$1"
  shift

  unset \
    COMPOSE_ENV_FILES \
    COMPOSE_FILE \
    COMPOSE_IGNORE_ORPHANS \
    COMPOSE_PATH_SEPARATOR \
    COMPOSE_PROFILES \
    COMPOSE_PROJECT_NAME \
    COMPOSE_REMOVE_ORPHANS \
    COURSE_DEMO_LOCAL_PORT \
    EMAIL_VERIFICATION_SENDER_DSN \
    POSTGRES_PASSWORD \
    PUBLIC_EMAIL_REGISTRATION_ENABLED \
    RELEASE_SHA \
    SECRET_KEY
  RELEASE_SHA="$release_sha_for_compose" \
    docker compose \
      --project-name "$project_name" \
      --env-file "$selected_env" \
      -f "$compose_file" \
      "$@"
)

compose_with_env() {
  controlled_compose "$env_file" "$@"
}

compose_for_cleanup() {
  controlled_compose "$example_env_file" "$@"
}

prepare() {
  local secret_key postgres_password

  require_command python3
  if [[ -L "$env_file" ]]; then
    die "prepare refuses the symlink path $env_file, including a broken symlink"
  fi
  if [[ -e "$env_file" ]]; then
    printf 'Existing private environment: %s (registration: %s).\n' \
      "$env_file" "$(registration_state)"
    die "prepare never reuses or overwrites an existing environment; archive or remove it explicitly"
  fi
  require_command docker
  docker info >/dev/null 2>&1 \
    || die "Docker is unavailable; cannot prove that the formal PostgreSQL volume is absent"
  if docker volume inspect "$postgres_volume" >/dev/null 2>&1; then
    die "formal PostgreSQL volume $postgres_volume exists without its private environment; inspect/archive it or run the explicit destroy command before fresh prepare"
  fi

  umask 077
  secret_key="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  postgres_password="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
  {
    printf 'DEPLOYMENT_GENERATION=%s\n' "$deployment_generation"
    printf 'SECRET_KEY=%s\n' "$secret_key"
    printf 'POSTGRES_PASSWORD=%s\n' "$postgres_password"
    printf 'COURSE_DEMO_LOCAL_PORT=8080\n'
    printf 'PUBLIC_EMAIL_REGISTRATION_ENABLED=false\n'
    printf 'EMAIL_VERIFICATION_SENDER_DSN=\n'
  } >"$env_file"
  chmod 600 "$env_file"
  validate_env
  printf 'Created fresh Deployment %s secrets at %s with mode 0600.\n' \
    "$deployment_generation" "$env_file"
  printf 'Registration remains disabled; no SMTP credential was inherited.\n'
}

rewrite_registration() (
  local enabled="$1"
  local sender_dsn="$2"
  local temporary line

  temporary="$(mktemp "${env_file}.tmp.XXXXXX")"
  cleanup_registration_temporary() {
    if [[ -n "$temporary" ]]; then
      rm -f -- "$temporary"
    fi
  }
  trap cleanup_registration_temporary EXIT
  trap 'exit 130' HUP INT TERM

  chmod 600 "$temporary"
  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      PUBLIC_EMAIL_REGISTRATION_ENABLED=*)
        printf 'PUBLIC_EMAIL_REGISTRATION_ENABLED=%s\n' "$enabled"
        ;;
      EMAIL_VERIFICATION_SENDER_DSN=*)
        if [[ -n "$sender_dsn" ]]; then
          printf "EMAIL_VERIFICATION_SENDER_DSN='%s'\n" "$sender_dsn"
        else
          printf 'EMAIL_VERIFICATION_SENDER_DSN=\n'
        fi
        ;;
      *)
        printf '%s\n' "$line"
        ;;
    esac
  done <"$env_file" >"$temporary"
  mv "$temporary" "$env_file"
  temporary=""
  chmod 600 "$env_file"
)

configure_registration() {
  local action="${1:-}"
  local sender_dsn confirmation

  case "$action" in
    enable)
      validate_env
      [[ -t 0 && -t 1 ]] \
        || die "registration enable requires an interactive terminal so the SMTP DSN is not a command argument"
      printf 'SMTP sender DSN (input hidden): '
      IFS= read -r -s sender_dsn
      printf '\n'
      [[ "$sender_dsn" == smtp://* || "$sender_dsn" == smtps://* ]] \
        || die "sender DSN must begin with smtp:// or smtps://"
      [[ ! "$sender_dsn" =~ [[:space:]] && "$sender_dsn" != *"'"* ]] \
        || die "percent-encode whitespace and quote characters in the sender DSN"
      printf 'Type ENABLE to authorize public registration for this deployment: '
      IFS= read -r confirmation
      [[ "$confirmation" == "ENABLE" ]] || die "registration authorization was not confirmed"
      rewrite_registration true "$sender_dsn"
      validate_env
      printf 'Public registration is enabled in the private environment; the DSN was not printed.\n'
      printf 'Existing API/worker/beat containers retain their prior environment; rerun deploy to apply this configuration.\n'
      ;;
    disable)
      validate_env_identity
      rewrite_registration false ""
      validate_env
      printf 'Public registration is disabled and the private sender DSN was cleared.\n'
      printf 'Existing API/worker/beat containers retain their prior environment; deploy recreates them, stop only makes it inactive, and destroy removes it.\n'
      ;;
    status)
      validate_env
      printf 'Configured public registration: %s. Sender DSN: %s.\n' \
        "$(registration_state)" \
        "$([[ -n "$(unquote_single_value "$(env_value EMAIL_VERIFICATION_SENDER_DSN)")" ]] && printf 'configured' || printf 'absent')"
      ;;
    *)
      die "registration requires enable, disable, or status"
      ;;
  esac
}

require_clean_exact_main() {
  local head_sha origin_main_sha

  require_command git
  if [[ ! "${EXPECTED_RELEASE_SHA:-}" =~ ^[0-9a-f]{40}$ ]]; then
    die "set EXPECTED_RELEASE_SHA to the complete lowercase SHA selected from origin/main"
  fi
  [[ -z "$(git -C "$repo_root" status --porcelain --untracked-files=all)" ]] \
    || die "the release checkout is dirty"

  printf 'Fetching origin/main before the release equality check.\n'
  git -C "$repo_root" fetch --no-tags origin \
    refs/heads/main:refs/remotes/origin/main
  head_sha="$(git -C "$repo_root" rev-parse --verify HEAD)"
  origin_main_sha="$(git -C "$repo_root" rev-parse --verify refs/remotes/origin/main)"
  if [[ "$head_sha" != "$EXPECTED_RELEASE_SHA" || "$origin_main_sha" != "$EXPECTED_RELEASE_SHA" ]]; then
    die "required HEAD == origin/main == EXPECTED_RELEASE_SHA; got HEAD=$head_sha origin/main=$origin_main_sha expected=$EXPECTED_RELEASE_SHA"
  fi

  RELEASE_SHA="$EXPECTED_RELEASE_SHA"
  export RELEASE_SHA
  release_sha_for_compose="$RELEASE_SHA"
  printf 'Release gate passed for Deployment %s at %s.\n' \
    "$deployment_generation" "$RELEASE_SHA"
}

config() {
  validate_env
  release_sha_for_compose="validation"
  compose_with_env config --quiet
  printf 'Deployment %s Compose configuration is valid (registration: %s).\n' \
    "$deployment_generation" "$(registration_state)"
}

config_example() {
  require_command python3
  release_sha_for_compose="validation"
  controlled_compose "$example_env_file" config --format json \
    | python3 -c '
import json
import sys

config = json.load(sys.stdin)
project_name = sys.argv[1]
api_environment = config["services"]["api"]["environment"]
postgres_environment = config["services"]["postgres"]["environment"]
redis_config = config["services"]["redis"]
web_ports = config["services"]["web"]["ports"]
postgres_volume_config = config["volumes"]["postgres_data"]
default_network_config = config["networks"]["default"]

def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


require(config["name"] == project_name, "controlled Compose project mismatch")
require(
    api_environment["SECRET_KEY"] == "replace-with-a-random-64-character-hex-value",
    "example API secret was overridden",
)
require(
    "replace-with-a-random-48-character-hex-value" in api_environment["DATABASE_URL"],
    "example API database password was overridden",
)
require(
    api_environment["PUBLIC_EMAIL_REGISTRATION_ENABLED"] == "false",
    "example registration flag was overridden",
)
require(api_environment["EMAIL_VERIFICATION_SENDER_DSN"] == "", "example SMTP DSN was overridden")
require(
    postgres_environment["POSTGRES_PASSWORD"] == "replace-with-a-random-48-character-hex-value",
    "example PostgreSQL password was overridden",
)
require(
    redis_config.get("tmpfs") == ["/data"],
    "Redis /data must be an explicit transient tmpfs",
)
require(
    not redis_config.get("volumes"),
    "Redis must not declare a persistent or anonymous data volume",
)
require(web_ports == [{
    "mode": "ingress",
    "host_ip": "127.0.0.1",
    "target": 80,
    "published": "8080",
    "protocol": "tcp",
}], "example loopback port was overridden")
require(
    postgres_volume_config["name"] == f"{project_name}_postgres_data",
    "controlled PostgreSQL volume name mismatch",
)
require(postgres_volume_config["labels"] == {
    "io.competehub.deployment-generation": "v1",
    "io.competehub.release-sha": "validation",
}, "controlled PostgreSQL volume labels mismatch")
require(
    default_network_config["name"] == f"{project_name}_default",
    "controlled network name mismatch",
)
require(default_network_config["labels"] == {
    "io.competehub.deployment-generation": "v1",
    "io.competehub.release-sha": "validation",
}, "controlled network labels mismatch")
' "$project_name"
  printf 'Controlled Deployment v1 example configuration is valid.\n'
}
build_tunnel() (
  local cache_root cache_dir binary temporary release_url host_arch docker_arch

  require_command curl
  require_command mktemp
  require_command sha256sum

  require_command uname
  host_arch="$(uname -m)"
  case "$host_arch" in
    x86_64 | amd64) ;;
    *)
      die "cloudflared checksum/build input is linux-amd64 only; host architecture is $host_arch"
      ;;
  esac
  docker_arch="$(docker info --format '{{.Architecture}}')"
  case "$docker_arch" in
    x86_64 | amd64) ;;
    *)
      die "cloudflared checksum/build input is linux-amd64 only; Docker target architecture is $docker_arch"
      ;;
  esac

  cache_root="$repo_root/.cache"
  cache_dir="$cache_root/course-demo-tunnel"
  binary="$cache_dir/cloudflared"
  temporary=""
  release_url="https://github.com/cloudflare/cloudflared/releases/download/${cloudflared_version}/cloudflared-linux-amd64"

  cleanup_tunnel_download() {
    if [[ -n "$temporary" ]]; then
      rm -f -- "$temporary"
    fi
  }
  trap cleanup_tunnel_download EXIT
  trap 'exit 130' HUP INT TERM

  [[ ! -L "$cache_root" ]] \
    || die "cloudflared cache root $cache_root is a symlink"
  [[ ! -e "$cache_root" || -d "$cache_root" ]] \
    || die "cloudflared cache root $cache_root is not a directory"
  mkdir -p -- "$cache_root"

  [[ ! -L "$cache_dir" ]] \
    || die "cloudflared cache directory $cache_dir is a symlink"
  [[ ! -e "$cache_dir" || -d "$cache_dir" ]] \
    || die "cloudflared cache path $cache_dir is not a directory"
  mkdir -p -- "$cache_dir"

  [[ ! -L "$binary" ]] \
    || die "cloudflared cache binary $binary is a symlink"
  [[ ! -e "$binary" || -f "$binary" ]] \
    || die "cloudflared cache binary $binary is not a regular file"

  if [[ ! -f "$binary" ]] \
    || ! printf '%s  %s\n' "$cloudflared_sha256" "$binary" \
      | sha256sum --check --status; then
    temporary="$(mktemp "$cache_dir/cloudflared.tmp.XXXXXX")"
    curl --fail --location --retry 3 --retry-all-errors \
      --connect-timeout 10 --max-time 300 \
      --output "$temporary" "$release_url" \
      || return
    printf '%s  %s\n' "$cloudflared_sha256" "$temporary" \
      | sha256sum --check \
      || return
    mv -- "$temporary" "$binary" || return
    temporary=""
  fi

  docker build --tag "competehub-course-deployment-tunnel:${cloudflared_version}" \
    --file "$repo_root/infra/course-demo/tunnel.Dockerfile" "$cache_dir"
)

prewarm() {
  validate_env
  require_clean_exact_main
  compose_with_env config --quiet
  printf 'Pulling version-selected base/runtime images; this changes only Docker image/cache state.\n'
  docker pull ghcr.io/astral-sh/uv:0.9.17
  docker pull public.ecr.aws/docker/library/python:3.11-slim
  docker pull public.ecr.aws/docker/library/node:22-alpine
  docker pull public.ecr.aws/docker/library/nginx:1.28-alpine
  docker pull public.ecr.aws/docker/library/alpine:3.23
  compose_with_env pull postgres redis
  build_tunnel
  printf 'Building release images sequentially for the small host.\n'
  compose_with_env build api
  compose_with_env build web
  printf 'Prewarm complete. Images, the verified cloudflared cache file, and BuildKit cache remain.\n'
}

volume_generation() {
  docker volume inspect \
    --format "{{ index .Labels \"$generation_label\" }}" "$postgres_volume" 2>/dev/null
}

volume_release_sha() {
  docker volume inspect \
    --format '{{ index .Labels "io.competehub.release-sha" }}' "$postgres_volume" 2>/dev/null
}

guard_postgres_volume() {
  local actual_generation actual_release_sha

  if ! docker volume inspect "$postgres_volume" >/dev/null 2>&1; then
    return
  fi
  actual_generation="$(volume_generation)"
  [[ "$actual_generation" == "$deployment_generation" ]] \
    || die "existing volume $postgres_volume is not labelled as Deployment $deployment_generation; no v0/in-place import is allowed"
  actual_release_sha="$(volume_release_sha)"
  [[ -n "${RELEASE_SHA:-}" && "$actual_release_sha" == "$RELEASE_SHA" ]] \
    || die "existing volume $postgres_volume belongs to release ${actual_release_sha:-unknown}, not ${RELEASE_SHA:-an exact selected release}; Deployment v1 supports fresh data per release SHA only"
}

require_postgres_volume() {
  docker volume inspect "$postgres_volume" >/dev/null 2>&1 \
    || die "fresh PostgreSQL volume is absent; run the explicit migrate step first"
  guard_postgres_volume
}

require_image() {
  docker image inspect "$1" >/dev/null 2>&1 \
    || die "required image $1 is absent; run the exact-release prewarm step first"
}

migrate() {
  validate_env
  require_clean_exact_main
  guard_postgres_volume
  require_image "competehub-course-deployment-api:${RELEASE_SHA}"
  compose_with_env config --quiet
  compose_with_env up -d --wait postgres redis
  guard_postgres_volume
  printf 'Applying Alembic migrations to the fresh Deployment %s PostgreSQL volume.\n' \
    "$deployment_generation"
  compose_with_env run --rm --no-deps api \
    flask --app competehub_api.app:create_app db --directory migrations upgrade
  compose_with_env run --rm --no-deps api \
    flask --app competehub_api.app:create_app db --directory migrations current
  printf 'Migration step complete. Demo bootstrap has not run.\n'
}

bootstrap_demo() {
  validate_env
  require_clean_exact_main
  require_postgres_volume
  require_image "competehub-course-deployment-api:${RELEASE_SHA}"
  compose_with_env up -d --wait postgres redis
  printf 'Explicitly provisioning the fictional #57 development-demo dataset.\n'
  compose_with_env run --rm --no-deps -e COMPETEHUB_ENV=development api \
    flask --app competehub_api.app:create_app bootstrap-development-demo
  printf 'Demo bootstrap step complete. Public services have not been deployed.\n'
}

local_port() {
  local value="8080"
  if [[ -f "$env_file" && ! -L "$env_file" ]]; then
    value="$(env_value COURSE_DEMO_LOCAL_PORT)"
    value="${value:-8080}"
  fi
  printf '%s' "$value"
}

spa_smoke() {
  local base_url="$1"
  local html asset_path

  html="$(curl --fail --silent --show-error --connect-timeout 3 --max-time 5 \
    "${base_url}/")" || return 1
  [[ "$html" == *'<div id="app"></div>'* ]] || return 1
  asset_path="$(printf '%s' "$html" \
    | sed -n 's#.*src="\(/assets/[^"]*\.js\)".*#\1#p' \
    | head -n 1)"
  [[ -n "$asset_path" ]] || return 1
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 \
    "${base_url}${asset_path}" >/dev/null
}

api_contract_smoke() {
  local base_url="$1"
  local expected_registration

  require_command python3
  expected_registration="$(env_value PUBLIC_EMAIL_REGISTRATION_ENABLED)"
  python3 - "$base_url" "$expected_registration" <<'PY'
import json
import sys
import urllib.request


def get_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": "CompeteHub-Deployment-v1-Smoke"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


base_url = sys.argv[1].rstrip("/")
expected_registration = sys.argv[2] == "true"

discovery = get_json(f"{base_url}/api/v1/competitions?page=1&page_size=1")
try:
    discovery_items = discovery["data"]["items"]
except (KeyError, TypeError):
    raise SystemExit("discovery smoke response did not match the expected envelope") from None
if not isinstance(discovery_items, list) or not discovery_items:
    raise SystemExit("discovery smoke requires at least one bootstrapped competition")

capability_response = get_json(f"{base_url}/api/v1/auth/capabilities")
try:
    capabilities = capability_response["data"]
except (KeyError, TypeError):
    raise SystemExit("auth capability smoke response did not match the expected envelope") from None
expected_capabilities = {"public_email_registration_enabled": expected_registration}
if capabilities != expected_capabilities:
    raise SystemExit("runtime registration capability does not match the private deployment configuration")
PY
}

worker_ping() {
  compose_for_cleanup exec -T worker sh -c \
    'exec celery -A competehub_api.tasks.celery_app.celery_app inspect ping --timeout=5 --destination "celery@$HOSTNAME"'
}

worker_is_ready() {
  local output

  output="$(worker_ping 2>/dev/null)" || return 1
  [[ "$output" == *pong* ]]
}

local_smoke() {
  local port worker_ready beat_id beat_state celery_result_key_state

  port="$(local_port)"
  spa_smoke "http://127.0.0.1:${port}" \
    || die "local Nginx did not serve the built SPA shell and JavaScript asset"
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 \
    "http://127.0.0.1:${port}/healthz" >/dev/null
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 \
    "http://127.0.0.1:${port}/api/v1/health" >/dev/null
  api_contract_smoke "http://127.0.0.1:${port}"

  worker_ready=false
  for _ in $(seq 1 6); do
    if worker_is_ready; then
      worker_ready=true
      break
    fi
    sleep 2
  done
  [[ "$worker_ready" == true ]] || die "Celery worker did not answer a bounded ping"

  beat_id="$(docker ps -q \
    --filter "label=com.docker.compose.project=$project_name" \
    --filter "label=com.docker.compose.service=beat")"
  [[ -n "$beat_id" ]] || die "Celery beat container is not running"
  beat_state="$(docker inspect --format '{{.State.Running}} {{.RestartCount}}' "$beat_id")"
  [[ "$beat_state" == "true 0" ]] \
    || die "Celery beat is not stable: $beat_state"

  celery_result_key_state="$(compose_for_cleanup exec -T redis redis-cli --raw EVAL_RO \
    'local cursor = "0"; for _ = 1, 1000 do local page = redis.call("SCAN", cursor, "MATCH", ARGV[1], "COUNT", 100); if #page[2] > 0 then return 1 end; cursor = page[1]; if cursor == "0" then return 0 end end; return 2' \
    0 'celery-task-meta-*')"
  case "$celery_result_key_state" in
    0) ;;
    1) die "Redis contains a celery-task-meta-* result key; #68 result suppression is not effective" ;;
    *) die "bounded read-only Redis result-key inspection was inconclusive" ;;
  esac

  printf 'Local SPA, API, usable demo discovery, registration capability, worker, scheduler, and Redis result-key smoke passed.\n'
}

tunnel_container_id() {
  docker ps -q \
    --filter "label=com.docker.compose.project=$project_name" \
    --filter "label=com.docker.compose.service=tunnel" \
    | head -n 1
}

current_tunnel_url() {
  local tunnel_id started_at

  tunnel_id="$(tunnel_container_id)"
  [[ -n "$tunnel_id" ]] || return 1
  started_at="$(docker inspect --format '{{.State.StartedAt}}' "$tunnel_id")"
  docker logs --since "$started_at" "$tunnel_id" 2>&1 \
    | sed -n 's#.*\(https://[-a-z0-9]*\.trycloudflare\.com\).*#\1#p' \
    | tail -n 1
}

wait_for_tunnel_url() {
  local url

  for _ in $(seq 1 30); do
    url="$(current_tunnel_url || true)"
    if [[ -n "$url" ]]; then
      printf '%s\n' "$url"
      return
    fi
    sleep 2
  done
  die "Quick Tunnel URL was not ready after 60 seconds"
}

public_smoke() {
  local url="$1"

  for _ in $(seq 1 5); do
    if spa_smoke "$url" \
      && curl --fail --silent --show-error --connect-timeout 3 --max-time 5 \
      "${url}/healthz" >/dev/null \
      && curl --fail --silent --show-error --connect-timeout 3 --max-time 5 \
        "${url}/api/v1/health" >/dev/null \
      && api_contract_smoke "$url"; then
      printf 'Public SPA, API, usable demo discovery, and registration capability smoke passed.\n'
      return
    fi
    sleep 2
  done
  die "public smoke did not pass within the bounded retry window"
}

stop_public_access_after_failed_deploy() {
  local running_tunnel_id

  if compose_for_cleanup stop tunnel >/dev/null 2>&1 \
    && running_tunnel_id="$(tunnel_container_id 2>/dev/null)" \
    && [[ -z "$running_tunnel_id" ]]; then
    printf 'Deployment failed; this project tunnel is confirmed stopped. Inspect bounded logs before retrying.\n' >&2
    return 0
  fi

  printf '%s\n' \
    'PUBLIC ACCESS MAY STILL BE ACTIVE: deployment failed and this project tunnel stop could not be confirmed.' \
    "Run 'just course-demo-status' and 'just course-demo-stop', then verify no running $project_name tunnel before assuming public access ended." >&2
  return 1
}

deploy() {
  local public_url deploy_succeeded=false

  validate_env
  require_clean_exact_main
  require_postgres_volume
  require_image "competehub-course-deployment-api:${RELEASE_SHA}"
  require_image "competehub-course-deployment-web:${RELEASE_SHA}"
  require_image "competehub-course-deployment-tunnel:${cloudflared_version}"
  compose_with_env config --quiet

  stop_public_access_on_failure() {
    if [[ "$deploy_succeeded" != true ]]; then
      stop_public_access_after_failed_deploy || :
    fi
  }
  trap stop_public_access_on_failure EXIT

  printf 'Stopping this project tunnel before local release validation.\n'
  compose_for_cleanup stop tunnel
  printf 'Starting the already-migrated and explicitly bootstrapped release without rebuilding.\n'
  compose_with_env up -d --wait --no-build api worker beat web
  local_smoke
  compose_with_env up -d --no-build tunnel
  public_url="$(wait_for_tunnel_url)"
  public_smoke "$public_url"
  deploy_succeeded=true
  trap - EXIT
  printf 'Deployment %s release: %s\n' "$deployment_generation" "$RELEASE_SHA"
  printf 'Public URL: %s\n' "$public_url"
}

status() {
  local head_sha origin_main_sha release_container release_sha public_url

  head_sha="$(git -C "$repo_root" rev-parse --verify HEAD 2>/dev/null || printf 'unavailable')"
  origin_main_sha="$(git -C "$repo_root" rev-parse --verify refs/remotes/origin/main 2>/dev/null || printf 'unavailable')"
  release_container="$(docker ps -aq \
    --filter "label=com.docker.compose.project=$project_name" \
    --filter "label=com.docker.compose.service=api" | head -n 1)"
  release_sha="not-running"
  if [[ -n "$release_container" ]]; then
    release_sha="$(docker inspect \
      --format '{{ index .Config.Labels "io.competehub.release-sha" }}' \
      "$release_container")"
  fi

  printf 'Deployment generation: %s\n' "$deployment_generation"
  printf 'Compose project: %s\n' "$project_name"
  printf 'Checkout HEAD: %s\n' "$head_sha"
  printf 'Fetched origin/main: %s\n' "$origin_main_sha"
  printf 'Runtime release label: %s\n' "$release_sha"
  printf 'Configured registration: %s (sender secret never displayed)\n' "$(registration_state)"
  printf 'Configured loopback port: 127.0.0.1:%s\n' "$(local_port)"

  printf '\nContainers and published ports:\n'
  docker ps -a \
    --filter "label=com.docker.compose.project=$project_name" \
    --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

  printf '\nPersistent volumes:\n'
  docker volume ls \
    --filter "label=com.docker.compose.project=$project_name" \
    --format 'table {{.Name}}\t{{.Driver}}\t{{.Labels}}'

  printf '\nNetworks:\n'
  docker network ls \
    --filter "label=com.docker.compose.project=$project_name" \
    --format 'table {{.Name}}\t{{.Driver}}\t{{.Labels}}'

  printf '\nProject images (images and BuildKit cache survive stop/destroy):\n'
  docker image ls --format '{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}' \
    | awk '$1 ~ /^competehub-course-deployment-/ {print}'

  public_url="$(current_tunnel_url || true)"
  printf '\nCurrent public URL: %s\n' "${public_url:-not-running}"
  printf 'Restart policy: runtime containers use unless-stopped and may return after a Docker/host restart.\n'
  if [[ -L "$env_file" ]]; then
    printf 'Private environment: %s (unsafe symlink; not read)\n' "$env_file"
  elif [[ -f "$env_file" ]]; then
    printf 'Private environment: %s (retained regular file)\n' "$env_file"
  else
    printf 'Private environment: %s (absent)\n' "$env_file"
  fi
}

url() {
  local public_url
  public_url="$(current_tunnel_url || true)"
  [[ -n "$public_url" ]] || die "no current Quick Tunnel URL is available"
  printf '%s\n' "$public_url"
}

smoke() {
  local public_url
  validate_env
  local_smoke
  public_url="$(wait_for_tunnel_url)"
  public_smoke "$public_url"
  printf 'Current public URL: %s\n' "$public_url"
}

logs() {
  case "${1:-}" in
    "")
      compose_for_cleanup logs --tail 200
      ;;
    postgres | redis | api | worker | beat | web | tunnel)
      compose_for_cleanup logs --tail 200 "$1"
      ;;
    *)
      die "logs service must be one of postgres, redis, api, worker, beat, web, or tunnel"
      ;;
  esac
}

stop_stack() {
  printf 'Stopping only current services in Compose project %s; all labelled containers:\n' \
    "$project_name"
  docker ps -a \
    --filter "label=com.docker.compose.project=$project_name" \
    --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
  compose_for_cleanup stop
  printf 'Stopped. Retained: containers, network, logs, PostgreSQL volume, private environment, images, build cache, and checkout.\n'
  printf 'Docker records this manual stop; unless-stopped will not restart these containers until an explicit start/deploy.\n'
}

destroy_stack() {
  local volume_project volume_generation_value

  [[ "${1:-}" == "DESTROY" ]] \
    || die "destructive cleanup requires '$0 destroy DESTROY'"

  if docker volume inspect "$postgres_volume" >/dev/null 2>&1; then
    volume_project="$(docker volume inspect \
      --format '{{ index .Labels "com.docker.compose.project" }}' \
      "$postgres_volume")"
    volume_generation_value="$(volume_generation)"
    [[ "$volume_project" == "$project_name" \
      && "$volume_generation_value" == "$deployment_generation" ]] \
      || die "same-name volume $postgres_volume lacks the expected project/generation labels; refusing an unpreviewed deletion"
  fi

  printf 'Destroy preview for every container labelled as Compose project %s, including orphans:\n' \
    "$project_name"
  docker ps -a \
    --filter "label=com.docker.compose.project=$project_name" \
    --format '  container {{.Names}} image={{.Image}} status={{.Status}} ports={{.Ports}}'
  docker volume ls \
    --filter "label=com.docker.compose.project=$project_name" \
    --format '  volume {{.Name}} labels={{.Labels}}'
  docker network ls \
    --filter "label=com.docker.compose.project=$project_name" \
    --format '  network {{.Name}} labels={{.Labels}}'
  printf 'Will remove only this project containers, network, and PostgreSQL volume.\n'
  printf 'Will retain: %s, project images, BuildKit/cache files, checkout, provider records, and v0 archives.\n' \
    "$env_file"

  compose_for_cleanup down --volumes --remove-orphans
  printf 'Destroy complete. The private environment and non-project-global assets were not removed.\n'
}

main() {
  local command="${1:-}"

  case "$command" in
    prepare)
      prepare
      ;;
    registration)
      configure_registration "${2:-}"
      ;;
    config)
      config
      ;;
    config-example)
      config_example
      ;;
    prewarm)
      prewarm
      ;;
    migrate)
      migrate
      ;;
    bootstrap-demo)
      bootstrap_demo
      ;;
    deploy)
      deploy
      ;;
    status)
      status
      ;;
    url)
      url
      ;;
    smoke)
      smoke
      ;;
    logs)
      logs "${2:-}"
      ;;
    stop)
      stop_stack
      ;;
    destroy)
      destroy_stack "${2:-}"
      ;;
    *)
      usage >&2
      return 1
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
