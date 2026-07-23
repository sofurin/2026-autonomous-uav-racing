# Minimal ROS 2 Offboard Mission

## Purpose

Provide a small, reusable PX4 Offboard control baseline before the real vehicle,
camera, and competition course are available. The mission is intentionally
independent of perception and map data.

## Mission

After an explicit start request:

1. Wait for a fresh, valid PX4 local NED position and heading.
2. Stream position-control heartbeat and a hold setpoint for at least one second.
3. Request Offboard mode, then arm.
4. Take off 1 m relative to the captured start position.
5. Hover for 5 s.
6. Fly 1 m in the captured takeoff-heading direction.
7. Return above the captured start position.
8. Request PX4 landing and finish after land detection.

## Safety contract

- `allow_mission_start`, `allow_arming_command` and `auto_start` default to
  `false`.
- Hardware flight may enable `allow_mission_start` while keeping
  `allow_arming_command=false`, so the state machine can wait for an explicit
  manual arm.
- The normal project bringup and hardware launch files never enable arming.
- Only the dedicated simulation demo launch may explicitly enable arming and
  automatic start.
- Stale/invalid position, excessive displacement/height, phase timeout, or loss
  of Offboard mode during flight aborts the mission and requests landing if the
  vehicle is armed.
- An explicit abort service is available at all times.
- Position targets are in PX4 local NED. No implicit ROS ENU conversion occurs.

## ROS interface

- Subscriptions default to the PX4 1.17 topics
  `/fmu/out/vehicle_local_position_v1`, `/fmu/out/vehicle_status_v1`, and
  `/fmu/out/vehicle_land_detected`; topic names are parameters for older PX4
  releases.
- Publications: `/fmu/in/offboard_control_mode`,
  `/fmu/in/trajectory_setpoint`, `/fmu/in/vehicle_command`, and private
  `~/state`
- Services: private `~/start` and `~/abort` using `std_srvs/srv/Trigger`

## Acceptance criteria

- Pure mission-state tests cover the nominal route and safety aborts.
- Package and repository tests pass under ROS 2 Humble.
- The dedicated launch starts PX4 SITL plus the controller without changing the
  existing default simulation and hardware behavior.
- SITL telemetry shows the vehicle complete takeoff, hover, forward flight,
  return, and landing.
