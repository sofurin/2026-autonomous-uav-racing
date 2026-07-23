# System Architecture

## Responsibility boundary

```text
Developer workstation
  |  Wi-Fi / SSH
  v
Intel NUC (Ubuntu 22.04)
  |-- Docker: ROS 2 Humble development environment
  |-- D435 driver and adapter (selected, not implemented)
  |-- Perception and localization (planned)
  |-- Racing mission and trajectory logic (planned)
  `-- Micro XRCE-DDS Agent (planned runtime process)
           |  serial or UDP, transport not yet verified
           v
PX4 flight controller
  |-- sensor fusion and state estimation
  |-- attitude / position control loops
  |-- arming, failsafe and flight safety
  `-- actuator mixing
           v
        ESC / motors
```

The workstation is a development and monitoring endpoint. It is not part of the flight-control loop. The NUC owns compute-heavy and mission-level autonomy. The flight controller remains responsible for stable flight and safety-critical control.

## ROS 2 to PX4 boundary

The intended bridge is PX4's native uXRCE-DDS path rather than MAVROS:

```text
ROS 2 application nodes
  <-> px4_msgs topics
  <-> Micro XRCE-DDS Agent on the NUC
  <-> PX4 uXRCE-DDS Client
  <-> PX4 uORB topics
```

Commands into PX4 use `/fmu/in/*`; telemetry and state from PX4 use `/fmu/out/*`. Topic names, message definitions and QoS must match the selected PX4 release.

## Container boundary

The reproducible baseline derives `simulation` and `nuc` stages from one pinned
ROS 2 Humble image. Both run as the configurable non-root `racing` UID/GID,
source the image-built `px4_msgs` underlay and mount this repository at
`/workspace/project`.

Both profiles use host networking and default `ROS_DOMAIN_ID` to `0`. The NUC
profile temporarily retains privileged `/dev` access for legacy hardware
bring-up; simulation receives only the X11 socket. Neither profile starts any
ROS, camera or flight process automatically.

The old root container `ros2_humble_main`, local image
`ros2:humble-desktopV1.0` and `/root/docker_ws` layout are migration-only. They
remain documented so the current NUC is not disrupted before hardware
revalidation.

## Verification status on 2026-07-23

| Layer | Status | Evidence |
| --- | --- | --- |
| NUC network and SSH | Verified | `nuc-13` reachable at `192.168.1.129` over Wi-Fi |
| ROS 2 container | Verified running | `ros2_humble_main` was running |
| ROS 2 application graph | Simulation bridge verified | project launch started TF and exposed PX4 DDS topics |
| PX4 source baseline | Verified on disk | `release/1.17` checkout found |
| XRCE Agent process | Verified on demand | project launch established a UDP 8888 session with PX4 SITL |
| Flight-controller transport launcher | Implemented, not hardware-verified | opt-in serial XRCE launch requires `/dev/serial/by-id/...` and never starts automatically |
| Flight-controller transport on hardware | Not verified | no real serial session or `/fmu/*` telemetry has been observed in this checkout |
| Competition camera | D435 selected | physical camera is available; ROS driver, calibration and localization remain pending |
| Real motor/flight behavior | Not tested | no claim of hardware or flight success |

## Required decisions before hardware integration

1. Pin and integrate the D435 ROS 2 driver.
2. Record the real `/dev/serial/by-id/...` identity and verify the serial DDS session.
3. Record the exact flight-controller board and flashed PX4 revision.
4. Define and flight-test offboard-loss behavior and manual takeover.
5. Add the team's localization, perception and planning nodes with interface contracts.

## Hardware and simulation parity

The perception and autonomy layers must not depend directly on a vendor camera SDK or a Gazebo plugin. Hardware and simulation adapters publish the same ROS 2 topic contract:

```text
Hardware camera driver ----\
                            -> racing_camera -> perception -> localization/planning
Gazebo virtual camera -----/                                      |
                                                                  v
                                                    racing_px4_control
                                                        /        \
                                                PX4 hardware    PX4 SITL
```

The bring-up layer selects the adapter and PX4 endpoint. Downstream perception, localization and planning nodes remain unchanged between hardware and simulation.
