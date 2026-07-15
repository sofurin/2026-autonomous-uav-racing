#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/environment.sh <simulation|nuc> [build|up|shell|down|config]

Examples:
  scripts/environment.sh simulation build
  scripts/environment.sh simulation shell
  scripts/environment.sh nuc up
EOF
}

profile="${1:-}"
action="${2:-shell}"

case "$profile" in
  simulation|nuc) ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    printf 'Expected simulation or nuc, got: %s\n' "${profile:-<empty>}" >&2
    usage >&2
    exit 2
    ;;
esac

case "$action" in
  build|up|shell|down|config) ;;
  *)
    printf 'Expected build, up, shell, down or config, got: %s\n' "$action" >&2
    usage >&2
    exit 2
    ;;
esac

command -v docker >/dev/null 2>&1 || {
  printf '%s\n' 'Docker CLI is not installed or is not on PATH.' >&2
  exit 127
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd -- "$script_dir/.." && pwd)"
cd "$repository_root"

compose=(docker compose --profile "$profile")

case "$action" in
  build)
    exec "${compose[@]}" build "$profile"
    ;;
  up)
    exec "${compose[@]}" up -d "$profile"
    ;;
  shell)
    "${compose[@]}" up -d "$profile"
    exec "${compose[@]}" exec "$profile" bash
    ;;
  down)
    exec "${compose[@]}" down
    ;;
  config)
    exec "${compose[@]}" config
    ;;
esac
