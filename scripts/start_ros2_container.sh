#!/usr/bin/env bash
set -euo pipefail

IMAGE="${ROS_IMAGE:-ros2:humble-desktopV1.0}"
CONTAINER_NAME="${ROS_CONTAINER_NAME:-ros2_humble_main}"
HOST_WORKSPACE="${HOST_WORKSPACE:-$HOME/docker_ws}"
CONTAINER_WORKSPACE="${CONTAINER_WORKSPACE:-/root/docker_ws}"
ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
DISPLAY="${DISPLAY:-:0}"

if [[ ! "$ROS_DOMAIN_ID" =~ ^[0-9]+$ ]]; then
  printf 'ROS_DOMAIN_ID must be a non-negative integer, got: %s\n' "$ROS_DOMAIN_ID" >&2
  exit 2
fi

if [[ ! -d "$HOST_WORKSPACE" ]]; then
  printf 'Host workspace does not exist: %s\n' "$HOST_WORKSPACE" >&2
  exit 2
fi

if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  if ! docker top "$CONTAINER_NAME" >/dev/null 2>&1; then
    docker start "$CONTAINER_NAME" >/dev/null
  fi

  exec docker exec -it \
    -e DISPLAY="$DISPLAY" \
    -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
    "$CONTAINER_NAME" bash
fi

xhost +local:root >/dev/null 2>&1 || true

exec docker run -it \
  --name "$CONTAINER_NAME" \
  --network host \
  --privileged \
  --mount type=bind,source=/dev,target=/dev \
  --mount type=bind,source=/dev/bus/usb,target=/dev/bus/usb \
  --mount type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix \
  --mount type=bind,source="$HOST_WORKSPACE",target="$CONTAINER_WORKSPACE" \
  -e DISPLAY="$DISPLAY" \
  -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  "$IMAGE" bash
