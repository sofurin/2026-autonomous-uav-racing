# System Architecture

## Responsibility boundary

```text
Developer workstation
  |  Wi-Fi / SSH
  v
Intel NUC (Ubuntu 22.04)
  |-- Docker: ROS 2 Humble development environment
  |-- Camera driver (TBD)
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

The currently inspected container is named `ros2_humble_main` and uses:

- image `ros2:humble-desktopV1.0`
- host networking
- privileged device access
- `/dev` and `/dev/bus/usb` mounts
- `/home/zjutdeus/docker_ws` mounted at `/root/docker_ws`

The checked-in launcher keeps these capabilities configurable and defaults `ROS_DOMAIN_ID` to `0`. Passing an empty `ROS_DOMAIN_ID` previously caused the ROS 2 CLI to fail before graph discovery.

## Verification status on 2026-07-12

| Layer | Status | Evidence |
| --- | --- | --- |
| NUC network and SSH | Verified | `nuc-13` reachable at `192.168.1.129` over Wi-Fi |
| ROS 2 container | Verified running | `ros2_humble_main` was running |
| ROS 2 application graph | Simulation bridge verified | project launch started TF and exposed PX4 DDS topics |
| PX4 source baseline | Verified on disk | `release/1.17` checkout found |
| XRCE Agent process | Verified on demand | project launch established a UDP 8888 session with PX4 SITL |
| Flight-controller transport | Not verified | no `/dev/ttyACM*`, `/dev/ttyUSB*` or `/dev/serial/by-id` detected |
| Competition camera | Undecided | do not treat the old Astra workspace as the selected camera |
| Real motor/flight behavior | Not tested | no claim of hardware or flight success |

## Required decisions before hardware integration

1. Select the competition camera and its ROS 2 driver.
2. Choose serial or UDP for the flight-controller DDS transport.
3. Record the exact flight-controller board and flashed PX4 revision.
4. Define command authority, offboard-loss behavior and manual takeover.
5. Add the team's perception, planning and mission nodes with interface contracts.

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
