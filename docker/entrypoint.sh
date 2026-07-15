#!/usr/bin/env bash
set -e

source /opt/ros/humble/setup.bash
source /opt/px4_msgs/install/setup.bash

project_setup=/workspace/project/ros2_ws/install/setup.bash
if [[ -f "$project_setup" ]]; then
  source "$project_setup"
fi

export PX4_AUTOPILOT_DIR="${PX4_AUTOPILOT_DIR:-/opt/upstream/PX4-Autopilot}"

exec "$@"
