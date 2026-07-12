# ROS 2 Container Baseline

The inspected NUC currently uses a local image named `ros2:humble-desktopV1.0`. Its original Dockerfile is not available in the inspected workspace, so the image is not yet reproducible from this repository.

The launcher in `scripts/start_ros2_container.sh` preserves the current runtime contract while avoiding hard-coded usernames where practical.

Before treating the container as a team baseline, add and validate a Dockerfile that installs:

- ROS 2 Humble desktop or an agreed smaller base
- the selected DDS implementation and ROS development tools
- colcon and build dependencies
- Micro XRCE-DDS Agent build/runtime dependencies
- the selected camera SDK only after the camera decision

Do not publish a Dockerfile reconstructed only from package guesses. Capture and review the actual required packages first.
