# ROS 2 Workspace

This workspace contains project-owned packages only. Build upstream PX4 interface packages separately and source them before this workspace when required.

```bash
cd ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

The initial packages define stable ownership boundaries. They intentionally contain no flight behavior yet.

On the NUC, source the existing dependency workspace before building:

```bash
source /opt/ros/humble/setup.bash
source /root/docker_ws/uav_test/install/setup.bash
colcon build --symlink-install
source install/setup.bash
```

The default simulation entry point uses the external PX4 checkout and the current depth-camera vehicle:

```bash
ros2 launch racing_bringup bringup.launch.py \
  mode:=simulation \
  px4_model:=gz_x500_depth
```

Replace `px4_model`, `px4_world` and `px4_model_pose` when the team airframe is registered. No perception or control package should depend on a concrete Gazebo model name.

Current packages:

- `racing_bringup`: hardware/simulation mode selection
- `racing_description`: base and camera coordinate frames
- `racing_camera`: vendor-neutral topic and calibration contract
- `racing_perception`: future gate and obstacle perception code
- `racing_px4_control`: future PX4 telemetry and Offboard boundary
- `racing_simulation`: simulator configuration, models and worlds
