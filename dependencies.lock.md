# Dependency Baseline

The machine-readable source of truth is [`dependencies.repos`](dependencies.repos).
The container build imports these exact revisions instead of following moving
branches.

| Dependency | Upstream | Branch | Commit |
| --- | --- | --- | --- |
| PX4 Autopilot | `https://github.com/PX4/PX4-Autopilot.git` | `release/1.17` | `6737fe1c3754a81a983b8f5aea6797b7d1669be6` |
| px4_msgs | `https://github.com/PX4/px4_msgs.git` | `main` | `aed8488dcf71184231a7b3019a179268696b7ea1` |
| Micro XRCE-DDS Agent | `https://github.com/eProsima/Micro-XRCE-DDS-Agent.git` | `master` | `155cfaaf8b7abac2e85d4a62d3649b09ace0be55` |

## Compatibility rule

`px4_msgs` definitions must remain compatible with the PX4 firmware deployed to the flight controller. Updating either repository requires an explicit compatibility check before flight testing.

The pinned PX4 revision exports `VehicleStatus` message version 1. The
`px4_msgs` revision above was selected because its versioned PX4 ROS 2 message
definitions match that interface; newer `px4_msgs` revisions use an incompatible
`VehicleStatus` schema.

## Container baseline

| Component | Pinned value |
| --- | --- |
| ROS image | `osrf/ros:humble-desktop@sha256:3d87cf339919a85cff7743ec9ba5e7ec81ccc26c9f722f1c7a6af5008dfdc128` |
| pymavlink | `2.4.49` |

The ROS image digest and source commits are immutable. Ubuntu and ROS packages
installed through `apt` are intentionally named but not frozen to repository
snapshot timestamps, so rebuilding on different dates is functionally
reproducible but not guaranteed to be byte-for-byte identical.

## Migration warning

The WSL checkout inspected on 2026-07-15 was already at the pinned PX4 commit,
but it was modified by the team-airframe installation. The container build now
reapplies that installation from project-owned files with
`install_team_racer_px4.sh`; a dirty host PX4 checkout is no longer the team
baseline.

The former Astra driver workspace remains excluded because the competition
camera has not been selected.

Reviewed Gazebo worlds, vehicle models, D435 assets and RoboCup tools are owned
by `racing_simulation`. Legacy PX4 working trees may still contain uncommitted
copies; do not use those copies as the source of truth.
