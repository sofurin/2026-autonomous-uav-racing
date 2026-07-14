#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install_team_racer_px4.sh [--px4-dir PATH]

Install the project-owned 4022_gz_team_racer airframe into a PX4-Autopilot
checkout and register it in the POSIX airframe CMake list.
EOF
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
package_dir="$(cd -- "$script_dir/.." && pwd)"
source_airframe="$package_dir/models/team_racer/config/4022_gz_team_racer"
px4_dir="${PX4_AUTOPILOT_DIR:-$HOME/PX4-Autopilot}"

while (($#)); do
  case "$1" in
    --px4-dir)
      [[ $# -ge 2 ]] || { printf '%s\n' 'Missing value for --px4-dir' >&2; exit 2; }
      px4_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

airframes_dir="$px4_dir/ROMFS/px4fmu_common/init.d-posix/airframes"
cmake_file="$airframes_dir/CMakeLists.txt"
destination="$airframes_dir/4022_gz_team_racer"

[[ -f "$source_airframe" ]] || {
  printf 'Project airframe does not exist: %s\n' "$source_airframe" >&2
  exit 2
}
[[ -d "$airframes_dir" ]] || {
  printf 'PX4 airframe directory does not exist: %s\n' "$airframes_dir" >&2
  exit 2
}
[[ -f "$cmake_file" ]] || {
  printf 'PX4 airframe CMake list does not exist: %s\n' "$cmake_file" >&2
  exit 2
}

install -m 0644 "$source_airframe" "$destination"

if ! grep -qE '^[[:space:]]*4022_gz_team_racer[[:space:]]*$' "$cmake_file"; then
  grep -qE '^[[:space:]]*4021_gz_x500_flow[[:space:]]*$' "$cmake_file" || {
    printf '%s\n' 'Could not find the 4021_gz_x500_flow insertion anchor.' >&2
    exit 2
  }
  sed -i '/^[[:space:]]*4021_gz_x500_flow[[:space:]]*$/a\	4022_gz_team_racer' "$cmake_file"
fi

printf 'Installed PX4 airframe: %s\n' "$destination"
printf 'Registered in: %s\n' "$cmake_file"
