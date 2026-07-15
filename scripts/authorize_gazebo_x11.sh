#!/usr/bin/env bash
set -euo pipefail

display="${DISPLAY:-:0}"
timeout_seconds="${X11_AUTH_TIMEOUT_SECONDS:-30}"
container_uid="${RACING_UID:-$(id -u)}"
container_user="$(getent passwd "$container_uid" | cut -d: -f1)"
deadline=$((SECONDS + timeout_seconds))

if [[ -z "$container_user" ]]; then
  printf 'No host user exists for container UID %s.\n' "$container_uid" >&2
  exit 2
fi

while (( SECONDS < deadline )); do
  xauthority="$({
    ps -u "$(id -u)" -eo args=
  } | sed -n "s/.*Xwayland ${display}.*-auth \\([^ ]*\\).*/\\1/p" | head -n 1)"

  if [[ -n "$xauthority" && -r "$xauthority" ]]; then
    DISPLAY="$display" XAUTHORITY="$xauthority" \
      xhost +SI:localuser:"$container_user" >/dev/null
    exit 0
  fi

  sleep 1
done

printf 'Xwayland authorization file for display %s was not found within %ss.\n' \
  "$display" "$timeout_seconds" >&2
exit 1
