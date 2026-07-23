# Reproducible ROS 2 Environments

The repository builds two environments from one pinned ROS 2 Humble base:

| Profile | Purpose | Includes |
| --- | --- | --- |
| `simulation` | Developer workstation | ROS 2, RViz, PX4 SITL dependencies, Gazebo, project airframe |
| `nuc` | NUC hardware runtime | ROS 2, `px4_msgs`, Micro XRCE-DDS Agent, generic device access |

Both images import the exact commits in `dependencies.repos`, build the
`px4_msgs` underlay, install Micro XRCE-DDS Agent and run as UID/GID 1000 by
default. Neither profile starts a flight process automatically.

## Prerequisites

- Docker Engine with Compose v2 (`docker compose version`)
- Linux, Ubuntu in dual boot, or WSL2 with Docker integration
- internet access for the first image build
- for Gazebo GUI on Linux: a running Xwayland/X11 display

PX4 supports Ubuntu 22.04 and documents
`Tools/setup/ubuntu.sh --no-nuttx` for simulation-only setup. The simulation
stage uses that project-owned installer rather than duplicating its package
list: <https://docs.px4.io/main/en/dev_setup/dev_env_linux_ubuntu.html>

Compose profiles are used so the hardware service is not started during a
normal simulation session: <https://docs.docker.com/compose/how-tos/profiles/>

## First use

```bash
cp .env.example .env
```

On a Linux host whose desktop user is not UID/GID 1000, edit `RACING_UID` and
`RACING_GID` in `.env` before building:

```bash
id -u
id -g
```

## Local simulation

Build and enter the environment:

```bash
./scripts/environment.sh simulation build
./scripts/environment.sh simulation shell
```

Inside the container:

```bash
./scripts/build_workspace.sh --test

ros2 launch racing_bringup bringup.launch.py \
  mode:=simulation \
  px4_dir:=/opt/upstream/PX4-Autopilot \
  px4_model:=gz_team_racer \
  px4_world:=robocup_2025_baseline \
  px4_model_pose:=-4,-3.65,0.095,0,0,0
```

For the competition demo:

```bash
ros2 launch racing_bringup competition_demo.launch.py \
  px4_dir:=/opt/upstream/PX4-Autopilot
```

On the NUC desktop, authorize the matching non-root container UID once per
graphical login before opening Gazebo:

```bash
./scripts/authorize_gazebo_x11.sh
```

## NUC hardware environment

Build and enter the idle hardware environment:

```bash
./scripts/environment.sh nuc build
./scripts/environment.sh nuc shell
```

Set `PX4_SERIAL_DEVICE` in the untracked `.env` only after selecting a stable
`/dev/serial/by-id/...` device. The current NUC profile keeps the legacy broad
`/dev` access so existing hardware bring-up remains possible. Replace this with
explicit device mappings after the flight controller and camera are finalized.
`PX4_SERIAL_BAUD` defaults to `921600`.

Inside the NUC service, the opt-in real-flight transport command is:

```bash
ros2 launch racing_bringup hardware.launch.py \
  start_xrce_agent:=true
```

This rejects unstable `/dev/ttyACM*` and `/dev/ttyUSB*` names. The separate
`start_offboard_controller` and `allow_mission_start` switches also default to
`false`, and the hardware launch cannot enable ROS 2 automatic arming.

Only one operator should own the hardware service. Other SSH users may enter
the same service for diagnostics, but they must not start duplicate camera,
XRCE Agent or Offboard-control processes.

## Lifecycle commands

```bash
./scripts/environment.sh simulation up
./scripts/environment.sh simulation shell
./scripts/environment.sh simulation down

./scripts/environment.sh nuc up
./scripts/environment.sh nuc shell
./scripts/environment.sh nuc down
```

Use `config` to inspect the fully resolved Compose configuration:

```bash
./scripts/environment.sh simulation config
```

## Reproducibility boundary

Pinned:

- ROS base-image digest
- PX4, `px4_msgs` and Micro XRCE-DDS Agent commits
- pymavlink version
- team-airframe installation procedure
- ROS workspace build/test command

Host-specific and deliberately not baked into the image:

- GPU kernel driver and container runtime integration
- X11/Wayland authorization
- camera and flight-controller device identities
- calibration, network identity and secrets
- measured mass, inertia and propulsion parameters

The `apt` packages are named but not bound to an Ubuntu repository snapshot, so
the environment is functionally reproducible rather than byte-for-byte
reproducible. Update the base digest and dependency commits only through a
reviewed change with simulation and ROS regression tests.
