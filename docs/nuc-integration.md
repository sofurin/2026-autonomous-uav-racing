# NUC Integration

## Reproducible deployment ownership

The new `nuc` image owns the shared software underlay:

```text
/opt/upstream/
├── PX4-Autopilot/          # exact commit from dependencies.repos
├── px4_msgs/               # exact source commit
└── Micro-XRCE-DDS-Agent/   # exact source commit
/opt/px4_msgs/install/      # image-built ROS 2 underlay
/workspace/project/         # bind-mounted team repository
```

Build and enter it from the repository root:

```bash
cp .env.example .env
./scripts/environment.sh nuc build
./scripts/environment.sh nuc shell
./scripts/build_workspace.sh --test
```

The image starts idle. Only the designated operator starts camera, XRCE Agent
and flight processes. Multiple SSH users must not start duplicate hardware
owners.

## Legacy NUC ownership during migration

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

The legacy local image and `uav_test` workspace remain usable until the new NUC
image has been built and hardware transport has been revalidated. They are not
the baseline for new machines.

## Gazebo GUI authorization

The simulation image runs as the same numeric UID as the NUC desktop user.
GNOME starts `scripts/authorize_gazebo_x11.sh` after login. The script
discovers Mutter's per-session Xauthority file and grants access only to the
host user matching `RACING_UID`; it does not disable X11 access control
globally and no longer authorizes container root.

The desktop entry is installed at:

```text
~/.config/autostart/racing-gazebo-x11.desktop
```

Inside the container, set `DISPLAY=:0` before launching the simulation. The
authorization is tied to the active graphical login and is refreshed
automatically at the next GNOME login.

## Build on the NUC

Inside the legacy `ros2_humble_main` only:

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
  px4_model:=gz_team_racer \
  px4_world:=racing_empty
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

The current model is selected by configuration rather than imported by perception or control code. The reproducible simulation image registers the project airframe during its build. Run the installer manually only in a legacy external PX4 checkout:

```bash
bash ros2_ws/src/racing_simulation/scripts/install_team_racer_px4.sh \
  --px4-dir /root/docker_ws/uav_test/src/PX4-Autopilot
```

Then select it normally:

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

## Legacy files retained during migration validation

The PX4 Gazebo-model submodule on the NUC contains uncommitted project work:

- modified `models/x500_depth/model.sdf` using a `realsense_d435` model
- untracked `models/realsense_d435/` including a large mesh
- untracked RoboCup obstacle models and `worlds/robocup_2025_baseline.sdf`
- untracked `robocup_2025/` scoring, route and vision-baseline scripts
- additional modifications to `OakD-Lite` and `x500_base`

The project now owns reviewed copies of the RoboCup 2025 baseline world,
obstacle models, course/scoring tools and a D435-compatible `x500_depth`
override under `racing_simulation`. The external PX4 checkout is still required
for SITL itself, but these migrated assets no longer depend on the dirty Gazebo
model submodule. The legacy 16 MB D435 mesh was copied at the project owner's
request and is tracked with an explicit provenance warning because its source
directory did not contain a license file.

Do not clean the old PX4 tree until the migrated default world and RoboCup
world have both passed runtime validation. The `OakD-Lite` and `x500_base`
changes remain legacy-only compatibility experiments and were not migrated.
