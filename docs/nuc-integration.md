# NUC Integration

## Current ownership

The NUC keeps upstream and legacy simulation dependencies outside this repository:

```text
/root/docker_ws/
├── uav_test/
│   ├── src/PX4-Autopilot/          # PX4 SITL and Gazebo dependency
│   ├── src/px4_msgs/               # ROS 2 interface dependency
│   ├── src/Micro-XRCE-DDS-Agent/   # Agent source
│   └── install/px4_msgs/            # ROS 2 underlay
└── 2026-autonomous-uav-racing/
    └── ros2_ws/                     # Project-owned ROS 2 overlay
```

The repository does not copy PX4 or `px4_msgs`. It points to the external PX4 checkout through the `px4_dir` launch argument and sources `uav_test/install/setup.bash` before building the project overlay.

## Gazebo GUI authorization

The current container runs as root and displays Gazebo through the NUC user's
Wayland/Xwayland desktop session. GNOME starts
`scripts/authorize_gazebo_x11.sh` after login. The script discovers Mutter's
per-session Xauthority file and grants access only to the local root user with
`xhost +SI:localuser:root`; it does not disable X11 access control globally.

The desktop entry is installed at:

```text
~/.config/autostart/racing-gazebo-x11.desktop
```

Inside the container, set `DISPLAY=:0` before launching the simulation. The
authorization is tied to the active graphical login and is refreshed
automatically at the next GNOME login.

## Build on the NUC

Inside `ros2_humble_main`:

```bash
export ROS_DOMAIN_ID=0
source /opt/ros/humble/setup.bash
source /root/docker_ws/uav_test/install/setup.bash

cd /root/docker_ws/2026-autonomous-uav-racing/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

## Default one-command simulation

After stopping any manually started duplicate PX4, Agent and camera-bridge processes:

```bash
ros2 launch racing_bringup bringup.launch.py \
  mode:=simulation \
  px4_model:=gz_x500_depth \
  px4_world:=default
```

This launch owns four boundaries:

1. project TF through `racing_description`
2. PX4 SITL from the external `uav_test/src/PX4-Autopilot`
3. `MicroXRCEAgent udp4 -p 8888`
4. Gazebo-to-ROS color and depth image bridges

When some processes are already running, disable only those owners:

```bash
ros2 launch racing_bringup bringup.launch.py \
  mode:=simulation \
  start_px4:=false \
  start_camera_bridge:=false \
  start_xrce_agent:=true
```

## Model replacement boundary

The current model is selected by configuration rather than imported by perception or control code:

```bash
ros2 launch racing_bringup bringup.launch.py \
  mode:=simulation \
  px4_model:=gz_team_racer \
  px4_world:=team_course \
  px4_model_pose:=-4,-3.65,0,0,0,0
```

Project-owned Gazebo resources belong under:

```text
ros2_ws/src/racing_simulation/models/
ros2_ws/src/racing_simulation/worlds/
```

The launcher prepends those directories to `GZ_SIM_RESOURCE_PATH`. A new top-level vehicle must also be registered as a valid PX4 `gz_*` target, or later use PX4 standalone mode with `PX4_GZ_MODEL_NAME`. This integration remains inside `racing_simulation`; camera, perception and PX4-control topic contracts do not change.

## Verified on 2026-07-12

- all six project packages built in `ros2_humble_main`
- `colcon test-result`: 9 tests, 0 failures
- the project launch started Micro XRCE-DDS Agent on UDP 8888
- the Agent established a session with the already-running PX4 SITL instance
- ROS 2 exposed `/fmu/in/*` and `/fmu/out/*` topics
- the running Gazebo bridge exposed `/camera/color/image_raw`

This proves the NUC ROS 2/PX4 simulation transport. It does not prove Offboard command behavior, real camera behavior, flight-controller serial transport or real flight safety.

## Legacy files that must not be deleted yet

The PX4 Gazebo-model submodule on the NUC contains uncommitted project work:

- modified `models/x500_depth/model.sdf` using a `realsense_d435` model
- untracked `models/realsense_d435/` including a large mesh
- untracked RoboCup obstacle models and `worlds/robocup_2025_baseline.sdf`
- untracked `robocup_2025/` scoring, route and vision-baseline scripts
- additional modifications to `OakD-Lite` and `x500_base`

These files currently make the legacy simulation work. They need a separate reviewed migration into `racing_simulation` before the old PX4 tree can be cleaned or replaced.
