# ADR-001: Use PX4 Native ROS 2 DDS Integration

## Status

Accepted as the development baseline; real flight-controller transport remains unverified.

## Date

2026-07-12

## Context

The NUC already contains PX4 Autopilot, `px4_msgs` and Micro XRCE-DDS Agent checkouts. The project needs a clear boundary between mission-level autonomy on ROS 2 and safety-critical flight control on PX4.

## Decision

Use PX4's uXRCE-DDS integration as the primary ROS 2 interface:

- PX4 runs the uXRCE-DDS Client.
- The NUC runs Micro XRCE-DDS Agent.
- Team nodes exchange typed `px4_msgs` topics through `/fmu/in/*` and `/fmu/out/*`.
- PX4 retains state estimation, stabilization, failsafe and actuator authority.
- The NUC owns perception, localization, race strategy and high-level trajectory generation.

## Alternatives considered

### MAVROS over MAVLink

Mature and widely documented, but introduces a translation layer that is not present in the current NUC workspace. It remains a fallback for tooling or compatibility needs, not the primary control interface.

### Direct motor control from the NUC

Rejected because a general-purpose Linux computer and ROS 2 are not the correct owners for hard real-time stabilization, actuator mixing and safety-critical failsafe behavior.

## Consequences

- `px4_msgs` and PX4 firmware versions must be kept compatible.
- DDS transport and QoS become part of the flight-critical integration contract.
- The team must explicitly manage offboard heartbeat, command authority and link-loss behavior.
- Simulation and ROS 2 graph success do not prove real flight-controller or motor behavior.
