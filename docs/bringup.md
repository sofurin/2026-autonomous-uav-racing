# Bring-up Sequence

This sequence separates environment readiness from real hardware success.

## 1. Inspect the host

```bash
./scripts/check_nuc_environment.sh
```

Confirm the intended camera and flight controller appear by stable device identity. Do not rely on a changing `/dev/ttyUSB0` number when `/dev/serial/by-id` is available.

## 2. Start the ROS 2 container

For the reproducible NUC profile:

```bash
./scripts/environment.sh nuc up
./scripts/environment.sh nuc shell
```

The service starts idle. This is intentional: entering the environment must not
arm, launch Offboard control or claim the camera automatically.

During migration only, the legacy local-image launcher remains available:

```bash
./scripts/start_ros2_container.sh
```

Inside the container, verify:

```bash
echo "$ROS_DOMAIN_ID"
source /opt/ros/humble/setup.bash
ros2 node list
```

Build the checked-out project with the same command used by developers:

```bash
./scripts/build_workspace.sh --test
```

An empty node list is valid before applications start. A traceback caused by an empty `ROS_DOMAIN_ID` is not valid.

## 3. Start the selected camera driver

The Intel RealSense D435 is selected, but its driver and calibration are not
part of the runtime yet. The hardware launch intentionally works without a
camera so flight-controller transport can be validated first. When the D435
adapter is added, verification must include image timestamps, frame IDs,
resolution, frame rate and exposure behavior—not only USB enumeration.

## 4. Start the PX4 bridge

Configure PX4 to run uXRCE-DDS on the dedicated companion-computer serial port.
For TELEM2 this normally means `UXRCE_DDS_CFG=TELEM2` and
`SER_TEL2_BAUD=921600`; confirm that another protocol is not assigned to the
same port.

On the NUC host, copy `.env.example` to the untracked `.env` and set the
flight controller's stable identity:

```bash
PX4_SERIAL_DEVICE=/dev/serial/by-id/<actual-flight-controller-or-adapter>
PX4_SERIAL_BAUD=921600
```

Start only the description and serial XRCE Agent:

```bash
ros2 launch racing_bringup hardware.launch.py \
  start_xrce_agent:=true
```

The launch rejects `/dev/ttyACM0` and `/dev/ttyUSB0`; use
`/dev/serial/by-id/...` so reconnecting another USB device cannot silently
change the flight-controller target.

Verify that PX4 topics appear:

```bash
./scripts/check_hardware_topics.sh
```

## 5. Start autonomy nodes

The real-aircraft control node is also opt-in. The following starts it in
standby but does not permit a mission start or automatic arming:

```bash
ros2 launch racing_bringup hardware.launch.py \
  start_xrce_agent:=true \
  start_offboard_controller:=true
```

After a valid PX4 local position, RC takeover, emergency stop and loss actions
have been verified, mission start can be enabled:

```bash
ros2 launch racing_bringup hardware.launch.py \
  start_xrce_agent:=true \
  start_offboard_controller:=true \
  allow_mission_start:=true
```

This hardware launch always forces `allow_arming_command=false` and
`auto_start=false`. The operator must explicitly call
`/offboard_mission/start` and arm through the approved manual path.

Bring up perception, localization, mission and trajectory components in that
order. Before publishing vehicle commands, confirm:

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
6. the controller remains in standby by default
7. manual mission start reaches `wait_for_position` without arming
8. commands are accepted while disarmed
9. propeller-free actuator direction test passes
10. controlled low-altitude flight test passes
