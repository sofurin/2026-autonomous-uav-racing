#!/usr/bin/env bash
set -euo pipefail

display="${DISPLAY:-:0}"
timeout_seconds="${X11_AUTH_TIMEOUT_SECONDS:-30}"
deadline=$((SECONDS + timeout_seconds))

while (( SECONDS < deadline )); do
  xauthority="$({
    ps -u "$(id -u)" -eo args=
  } | sed -n "s/.*Xwayland ${display}.*-auth \\([^ ]*\\).*/\\1/p" | head -n 1)"

  if [[ -n "$xauthority" && -r "$xauthority" ]]; then
    DISPLAY="$display" XAUTHORITY="$xauthority" \
      xhost +SI:localuser:root >/dev/null
    exit 0
  fi

  sleep 1
done

printf 'Xwayland authorization file for display %s was not found within %ss.\n' \
  "$display" "$timeout_seconds" >&2
exit 1
