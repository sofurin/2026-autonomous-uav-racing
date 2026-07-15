# ADR-002: Use a shared container base with simulation and NUC profiles

## Status

Accepted

## Date

2026-07-15

## Context

The team develops on different Ubuntu/WSL2 computers and deploys hardware code
to one shared NUC. The original `ros2:humble-desktopV1.0` image was a local tag
whose Dockerfile was unavailable. PX4 was also installed as a mutable host
checkout, so two machines could use different commits or different manual
airframe modifications while appearing to follow the same instructions.

Simulation and NUC runtime have different device and package needs, but must
share ROS interfaces, `px4_msgs`, Micro XRCE-DDS Agent and project code.

## Decision

- Pin the ROS 2 Humble desktop base by multi-architecture image digest.
- Import PX4, `px4_msgs` and Micro XRCE-DDS Agent from exact commits recorded in
  `dependencies.repos`.
- Build `px4_msgs` and Micro XRCE-DDS Agent into a shared `base` stage.
- Derive a `simulation` stage that runs PX4's official Ubuntu simulation setup
  and installs the project-owned `gz_team_racer` airframe.
- Derive a `nuc` stage without guessed camera drivers.
- Select the stages through Compose `simulation` and `nuc` profiles.
- Run both stages as a normal `racing` user whose UID/GID can match the host.
- Start containers idle; require an operator to launch simulation or hardware
  processes explicitly.

Official implementation references:

- PX4 Ubuntu development environment:
  <https://docs.px4.io/main/en/dev_setup/dev_env_linux_ubuntu.html>
- Docker Compose profiles:
  <https://docs.docker.com/compose/how-tos/profiles/>
- Docker multi-stage builds:
  <https://docs.docker.com/build/building/multi-stage/>
- OSRF ROS image registry:
  <https://hub.docker.com/r/osrf/ros/tags?name=humble-desktop>

## Alternatives considered

### Continue using the local `ros2:humble-desktopV1.0` image

Rejected because its installation history cannot be reconstructed on a new
computer or after a NUC reinstall.

### Install all dependencies directly on each host

Rejected because Ubuntu/WSL2 package drift and one-off `pip` installations
would remain team-member specific.

### Use one image and automatically start the complete flight stack

Rejected because simulation and hardware have different device access, and an
automatic hardware launch is unsafe when several users share the NUC.

### Vendor complete upstream repositories into the project repository

Rejected because it duplicates large upstream histories and obscures which
official revision is in use. Exact commits are imported during the image build
instead.

## Consequences

- A clean machine can rebuild the same source baseline from Git and Docker.
- Local simulation and NUC deployment use the same project workspace and ROS
  interface underlay.
- The first simulation build is large because PX4/Gazebo dependencies are
  installed from the official setup script.
- GPU drivers, GUI authorization, USB identities and calibration remain host
  responsibilities and require explicit checks.
- `apt` repositories are not snapshot-pinned, so builds are not guaranteed to
  be byte-identical.
- Broad NUC `/dev` access remains temporarily for compatibility and should be
  narrowed after the final flight controller and camera are selected.
