# RoboCup 2025 simulation baseline

This directory preserves the validated known-map baseline recovered from the
legacy NUC PX4 tree. It is a simulation and scoring reference, not the final
2026 competition strategy.

The project-owned world is launched through the normal bringup entry point:

```bash
ros2 launch racing_bringup bringup.launch.py \
  mode:=simulation \
  px4_model:=gz_team_racer \
  px4_world:=robocup_2025_baseline \
  px4_model_pose:=-4,-3.65,0,0,0,0
```

Validate the course and score contract without flying:

```bash
python3 -m pytest -q test_score_checker.py test_fly_known_course.py
python3 fly_known_course.py --dry-run
```

`fly_known_course.py` uses direct MAVLink and remains a legacy baseline. New
autonomy code should send commands through `racing_px4_control` and PX4's ROS 2
DDS interface.
