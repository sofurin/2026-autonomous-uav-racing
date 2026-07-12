#!/usr/bin/env bash
set -u

printf 'Host: '
hostname
printf 'OS: '
. /etc/os-release
printf '%s\n' "$PRETTY_NAME"
printf 'Architecture: '
uname -m

printf '\nNetwork interfaces\n'
ip -brief address

printf '\nStable serial devices\n'
if [[ -d /dev/serial/by-id ]]; then
  find /dev/serial/by-id -mindepth 1 -maxdepth 1 -printf '%f -> %l\n'
else
  printf 'No /dev/serial/by-id directory found.\n'
fi

printf '\nUSB serial candidates\n'
compgen -G '/dev/ttyACM*' || true
compgen -G '/dev/ttyUSB*' || true

printf '\nUSB devices\n'
lsusb

printf '\nRelevant processes\n'
pgrep -af 'MicroXRCEAgent|uxrce|px4|ros2|mavros' || printf 'No matching process found.\n'

printf '\nDocker containers\n'
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' 2>/dev/null || printf 'Docker is unavailable to this user.\n'
