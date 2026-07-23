#!/usr/bin/env bash
set -euo pipefail

if ! command -v ros2 >/dev/null 2>&1; then
  printf 'ros2 is unavailable; enter the NUC container first.\n' >&2
  exit 2
fi

required_topics=(
  /fmu/out/vehicle_status_v1
  /fmu/out/vehicle_local_position_v1
  /fmu/out/vehicle_land_detected
  /fmu/in/offboard_control_mode
  /fmu/in/trajectory_setpoint
  /fmu/in/vehicle_command
)
sample_topics=(
  /fmu/out/vehicle_status_v1
  /fmu/out/vehicle_local_position_v1
  /fmu/out/vehicle_land_detected
)

topic_list="$(ros2 topic list)"
missing=0
printf 'Required PX4 ROS 2 topics\n'
for topic in "${required_topics[@]}"; do
  if grep -Fxq "$topic" <<<"$topic_list"; then
    printf '  OK      %s\n' "$topic"
  else
    printf '  MISSING %s\n' "$topic"
    missing=1
  fi
done

if ((missing)); then
  printf 'PX4 DDS graph is incomplete; no commands were sent.\n' >&2
  exit 1
fi

sample_timeout_s="${ROS_TOPIC_TIMEOUT_S:-5}"
printf '\nOne-sample telemetry probes\n'
for topic in "${sample_topics[@]}"; do
  printf '\n[%s]\n' "$topic"
  if ! timeout "$sample_timeout_s" ros2 topic echo "$topic" --once; then
    printf 'No sample received from %s within %ss.\n' \
      "$topic" "$sample_timeout_s" >&2
    exit 1
  fi
done

printf '\nHardware topic check passed. No command topic was published.\n'
