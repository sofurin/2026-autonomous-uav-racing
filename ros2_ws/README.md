# ROS 2 Workspace

This workspace contains project-owned packages only. PX4, `px4_msgs`, and the
Micro XRCE-DDS Agent remain external, pinned dependencies.

```bash
cd ..
./scripts/build_workspace.sh --test
```

The package boundaries are stable. Simulation orchestration, PX4 DDS transport,
the project airframe, and a minimal simulation-only Offboard mission are
implemented. Perception algorithms and the real flight-controller transport are
still unimplemented and must not be reported as verified.

For a native WSL or legacy NUC environment whose `px4_msgs` underlay is not at
`/opt/px4_msgs/install`, override it explicitly:

```bash
PX4_MSGS_SETUP=$HOME/uav/px4_msgs_ws/install/setup.bash \
  ./scripts/build_workspace.sh --test
```

The default simulation entry point uses the external PX4 checkout and the
project-owned team airframe:

```bash
ros2 launch racing_bringup bringup.launch.py \
  mode:=simulation \
  px4_model:=gz_team_racer
```

The minimal no-camera control validation is:

```bash
ros2 launch racing_bringup offboard_demo.launch.py \
  px4_dir:=$HOME/PX4-Autopilot \
  headless:=true
```

`competition_demo.launch.py` and `racing_simulation/tools/robocup_2025/` are
legacy 2025 known-map references. They are useful for regression testing but
are not the final random-course competition strategy.

No perception or control package should depend on a concrete Gazebo model
name.

Current packages:

- `racing_bringup`: hardware/simulation mode selection
- `racing_description`: base and camera coordinate frames
- `racing_camera`: vendor-neutral topic and calibration contract
- `racing_perception`: future gate and obstacle perception code
- `racing_px4_control`: PX4 telemetry boundary and minimal Offboard mission
- `racing_simulation`: simulator configuration, models and worlds
