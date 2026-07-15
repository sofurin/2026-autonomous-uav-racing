#!/usr/bin/env bash
set -euo pipefail

run_tests=false
case "${1:-}" in
  "") ;;
  --test) run_tests=true ;;
  -h|--help)
    printf '%s\n' 'Usage: scripts/build_workspace.sh [--test]'
    exit 0
    ;;
  *)
    printf 'Unknown argument: %s\n' "$1" >&2
    exit 2
    ;;
esac

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd -- "$script_dir/.." && pwd)"
workspace="${ROS2_WORKSPACE:-$repository_root/ros2_ws}"
ros_setup="${ROS_SETUP:-/opt/ros/humble/setup.bash}"
px4_msgs_setup="${PX4_MSGS_SETUP:-/opt/px4_msgs/install/setup.bash}"

for setup_file in "$ros_setup" "$px4_msgs_setup"; do
  [[ -f "$setup_file" ]] || {
    printf 'Required underlay does not exist: %s\n' "$setup_file" >&2
    exit 2
  }
done
[[ -d "$workspace/src" ]] || {
  printf 'ROS 2 workspace source directory does not exist: %s/src\n' "$workspace" >&2
  exit 2
}

source "$ros_setup"
source "$px4_msgs_setup"
cd "$workspace"

colcon build --symlink-install

if [[ "$run_tests" == true ]]; then
  colcon test --event-handlers console_cohesion+
  colcon test-result --verbose
fi
