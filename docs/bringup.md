# Bring-up Sequence

This sequence separates environment readiness from real hardware success.

## 1. Inspect the host

```bash
./scripts/check_nuc_environment.sh
```

Confirm the intended camera and flight controller appear by stable device identity. Do not rely on a changing `/dev/ttyUSB0` number when `/dev/serial/by-id` is available.

## 2. Start the ROS 2 container

```bash
./scripts/start_ros2_container.sh
```

Inside the container, verify:

```bash
echo "$ROS_DOMAIN_ID"
source /opt/ros/humble/setup.bash
ros2 node list
```

An empty node list is valid before applications start. A traceback caused by an empty `ROS_DOMAIN_ID` is not valid.

## 3. Start the selected camera driver

The competition camera is not selected yet. Add its driver and calibration only after the hardware decision is made. Verification must include image timestamps, frame IDs, resolution, frame rate and exposure behavior—not only USB enumeration.

## 4. Start the PX4 bridge

Start the Micro XRCE-DDS Agent with the selected transport. Examples are intentionally omitted until serial versus UDP and the actual device identity are confirmed.

Verify that PX4 topics appear:

```bash
ros2 topic list | grep '^/fmu/'
ros2 topic echo /fmu/out/vehicle_status --once
```

## 5. Start autonomy nodes

Bring up perception, localization, mission and trajectory components in that order. Before publishing vehicle commands, confirm:

- coordinate frames and timestamp source
- PX4 message compatibility and QoS
- offboard heartbeat rate
- manual takeover and emergency stop behavior
- safe behavior when camera, ROS 2 or NUC communication is lost

## 6. Stage hardware validation

Treat these as separate gates:

1. source builds
2. ROS 2 nodes start
3. camera data is valid
4. DDS Agent connects to PX4
5. telemetry is received
6. commands are accepted while disarmed
7. restrained motor test passes
8. controlled flight test passes
