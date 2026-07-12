# Simulation and Camera Architecture

## Goal

Use the same perception, localization, planning and PX4-control code in simulation and on the real aircraft. Only the sensor adapter, environment and PX4 endpoint change.

## Package boundaries

| Package | Responsibility | Must not own |
| --- | --- | --- |
| `racing_bringup` | Select hardware or simulation mode and compose launch files | Perception algorithms |
| `racing_description` | Airframe model, sensor frames and mounting transforms | Camera SDK calls |
| `racing_camera` | Normalize the selected hardware driver into the project topic contract | Gate detection or planning |
| `racing_perception` | Detect gates, obstacles and visual features | Vendor-specific device setup |
| `racing_localization` | Fuse visual estimates with PX4 state | Motor commands |
| `racing_planning` | Race-state decisions and trajectory generation | PX4 transport details |
| `racing_px4_control` | Translate project commands and PX4 state through `px4_msgs` | Camera processing |
| `racing_simulation` | PX4 SITL, Gazebo worlds, models and virtual sensors | Hardware-only configuration |
| `racing_test` | Rosbag replay and cross-layer integration tests | Production flight control |

## Stable camera contract

The selected hardware camera and the Gazebo camera should provide equivalent streams:

```text
/camera/color/image_raw
/camera/color/camera_info
/camera/depth/image_raw       # optional; only if the selected sensor provides depth
```

The exact namespace may change before implementation, but it must be configured in one place and remain identical between real and simulated launch files. Required accompanying transforms include:

```text
base_link -> camera_link -> camera_optical_frame
```

Calibration belongs under the hardware configuration, not in perception code. The competition camera remains undecided, so no Astra-specific dependency or configuration is part of the baseline.

## Simulation path

```text
Gazebo world and gate models
  -> virtual camera and vehicle sensors
  -> standard camera topics
  -> perception / localization / planning
  -> racing_px4_control
  -> PX4 SITL through uXRCE-DDS
  -> simulated vehicle actuators and dynamics
```

Simulation validates ROS 2 interfaces, coordinate frames, mission-state transitions and trajectory continuity. It does not prove real camera timing, exposure behavior, serial reliability, motor response or flight safety.

## Hardware path

```text
Selected physical camera
  -> vendor or V4L2 ROS 2 driver
  -> racing_camera normalization
  -> perception / localization / planning
  -> racing_px4_control
  -> Micro XRCE-DDS Agent
  -> PX4 flight controller
  -> ESC and motors
```

PX4 remains responsible for state estimation, stabilization, actuator mixing and failsafe behavior.

## Bring-up interface

The intended user-facing commands are:

```bash
ros2 launch racing_bringup bringup.launch.py mode:=simulation
ros2 launch racing_bringup bringup.launch.py mode:=hardware
```

The launch implementation now selects the external PX4 SITL process, UDP XRCE Agent and Gazebo camera bridge. `mode` selects:

- the virtual or physical camera adapter
- PX4 SITL or the real flight-controller endpoint
- simulation clock behavior
- the correct calibration and sensor-frame configuration

It does not fork the perception or planning implementation into separate simulation and hardware versions. The current simulation entry point is:

```bash
ros2 launch racing_bringup bringup.launch.py \
  mode:=simulation \
  px4_model:=gz_x500_depth
```

Set `px4_model` and `px4_world` to move to a PX4-registered team model. Project-owned model and world resources are supplied through `GZ_SIM_RESOURCE_PATH`; the integration details remain confined to `racing_simulation`.

## Validation gates

1. Virtual camera topics have the agreed names, encodings, rates and frame IDs.
2. Hardware camera topics satisfy the same contract.
3. A recorded hardware bag can drive perception without the physical camera.
4. Perception and planning nodes run unchanged against Gazebo and bag replay.
5. PX4 SITL telemetry and command topics match the real PX4 message version.
6. Hardware flight testing remains a separate, controlled validation stage.
