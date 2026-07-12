# ROS 2 Workspace

This workspace contains project-owned packages only. Build upstream PX4 interface packages separately and source them before this workspace when required.

```bash
cd ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

The initial packages define stable ownership boundaries. They intentionally contain no flight behavior yet.

Current packages:

- `racing_bringup`: hardware/simulation mode selection
- `racing_description`: base and camera coordinate frames
- `racing_camera`: vendor-neutral topic and calibration contract
- `racing_perception`: future gate and obstacle perception code
- `racing_px4_control`: future PX4 telemetry and Offboard boundary
- `racing_simulation`: simulator configuration, models and worlds
