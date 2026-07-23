from pathlib import Path
import re
import os
import subprocess
import sys

import pytest


# Repository-level tests are invoked from the checkout root. Keeping the base
# relative avoids WSL drvfs path-encoding issues with Chinese host directories.
REPOSITORY_ROOT = Path(".")


def _read(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def test_external_dependencies_are_machine_readable_and_pinned() -> None:
    repositories = _read("dependencies.repos")

    expected_revisions = {
        "PX4-Autopilot": "6737fe1c3754a81a983b8f5aea6797b7d1669be6",
        "px4_msgs": "aed8488dcf71184231a7b3019a179268696b7ea1",
        "Micro-XRCE-DDS-Agent": "155cfaaf8b7abac2e85d4a62d3649b09ace0be55",
    }
    for repository, revision in expected_revisions.items():
        assert repository in repositories
        assert re.search(rf"version:\s*{revision}\b", repositories)


def test_container_image_has_shared_simulation_and_nuc_stages() -> None:
    dockerfile = _read("docker/Dockerfile")

    assert (
        "FROM osrf/ros:humble-desktop@sha256:"
        "3d87cf339919a85cff7743ec9ba5e7ec81ccc26c9f722f1c7a6af5008dfdc128 AS base"
        in dockerfile
    )
    assert "FROM base AS simulation" in dockerfile
    assert "FROM base AS nuc" in dockerfile
    assert "vcs import" in dockerfile
    assert "install_team_racer_px4.sh" in dockerfile
    assert "MicroXRCEAgent" in dockerfile
    assert "/opt/px4_msgs/install/setup.bash" in dockerfile
    assert "USER racing" in dockerfile


def test_px4_setup_installs_user_python_packages_for_the_runtime_user() -> None:
    dockerfile = _read("docker/Dockerfile")
    simulation_stage = dockerfile.split("FROM base AS simulation", 1)[1].split(
        "FROM base AS nuc", 1
    )[0]

    assert re.search(
        r"USER racing.*?RUN /opt/upstream/PX4-Autopilot/Tools/setup/ubuntu.sh",
        simulation_stage,
        re.DOTALL,
    )
    assert "USER root" not in simulation_stage


def test_compose_profiles_share_the_project_and_keep_bringup_manual() -> None:
    compose = _read("compose.yaml")

    assert "simulation:" in compose
    assert 'profiles: ["simulation"]' in compose
    assert "nuc:" in compose
    assert 'profiles: ["nuc"]' in compose
    assert "network_mode: host" in compose
    assert "./:/workspace/project" in compose
    assert 'command: ["sleep", "infinity"]' in compose
    assert "ros2 launch" not in compose
    assert "PX4_SERIAL_BAUD: ${PX4_SERIAL_BAUD:-921600}" in compose


def test_entrypoint_sources_ros_dependency_and_project_overlays() -> None:
    entrypoint = _read("docker/entrypoint.sh")

    assert "source /opt/ros/humble/setup.bash" in entrypoint
    assert "source /opt/px4_msgs/install/setup.bash" in entrypoint
    assert "/workspace/project/ros2_ws/install/setup.bash" in entrypoint
    assert 'exec "$@"' in entrypoint


def test_example_environment_does_not_select_a_real_flight_controller() -> None:
    environment = _read(".env.example")

    assert "ROS_DOMAIN_ID=0" in environment
    assert "PX4_SERIAL_DEVICE=" in environment
    assert "PX4_SERIAL_BAUD=921600" in environment
    assert "/dev/ttyUSB0" not in environment
    assert "/dev/ttyACM0" not in environment


def test_xrce_agent_command_requires_a_stable_serial_identity() -> None:
    package_root = REPOSITORY_ROOT / "ros2_ws/src/racing_bringup"
    sys.path.insert(0, str(package_root))
    try:
        from racing_bringup.hardware_transport import serial_agent_command
    finally:
        sys.path.pop(0)

    assert serial_agent_command(
        "/dev/serial/by-id/usb-PX4_FMU", "921600"
    ) == [
        "MicroXRCEAgent",
        "serial",
        "--dev",
        "/dev/serial/by-id/usb-PX4_FMU",
        "-b",
        "921600",
    ]

    with pytest.raises(ValueError, match="/dev/serial/by-id"):
        serial_agent_command("/dev/ttyACM0", "921600")

    with pytest.raises(ValueError, match="baud"):
        serial_agent_command("/dev/serial/by-id/usb-PX4_FMU", "fast")


def test_hardware_launch_keeps_transport_and_motion_opt_in() -> None:
    hardware_launch = _read(
        "ros2_ws/src/racing_bringup/launch/hardware.launch.py"
    )

    assert re.search(
        r'DeclareLaunchArgument\(\s*"start_xrce_agent",\s*default_value="false"',
        hardware_launch,
    )
    assert re.search(
        r'DeclareLaunchArgument\(\s*"start_offboard_controller",\s*'
        r'default_value="false"',
        hardware_launch,
    )
    assert '"allow_mission_start": allow_mission_start' in hardware_launch
    assert '"allow_arming_command": "false"' in hardware_launch
    assert '"auto_start": "false"' in hardware_launch
    assert "serial_agent_command" in hardware_launch


def test_x11_authorization_targets_the_matching_host_user_not_root() -> None:
    authorization = _read("scripts/authorize_gazebo_x11.sh")

    assert "xhost +SI:localuser:root" not in authorization
    assert 'container_uid="${RACING_UID:-$(id -u)}"' in authorization
    assert "xhost +SI:localuser:" in authorization


def test_environment_helper_rejects_unknown_profiles() -> None:
    helper = REPOSITORY_ROOT / "scripts" / "environment.sh"

    result = subprocess.run(
        ["bash", str(helper), "flight", "up"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Expected simulation or nuc" in result.stderr


def test_environment_helper_starts_then_enters_the_selected_service(
    tmp_path: Path,
) -> None:
    helper = REPOSITORY_ROOT / "scripts" / "environment.sh"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_log = tmp_path / "docker.log"
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$*" >>"$DOCKER_LOG"\n',
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)

    environment = os.environ.copy()
    environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
    environment["DOCKER_LOG"] = str(docker_log)
    result = subprocess.run(
        ["bash", str(helper), "simulation", "shell"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert docker_log.read_text(encoding="utf-8").splitlines() == [
        "compose --profile simulation up -d simulation",
        "compose --profile simulation exec simulation bash",
    ]


def test_workspace_helper_sources_underlays_without_nounset_then_builds_and_tests(
    tmp_path: Path,
) -> None:
    helper = REPOSITORY_ROOT / "scripts" / "build_workspace.sh"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    colcon_log = tmp_path / "colcon.log"
    fake_colcon = fake_bin / "colcon"
    fake_colcon.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$*" >>"$COLCON_LOG"\n',
        encoding="utf-8",
    )
    fake_colcon.chmod(0o755)
    ros_setup = tmp_path / "ros_setup.bash"
    px4_msgs_setup = tmp_path / "px4_msgs_setup.bash"
    ros_setup.write_text(
        'if [ -n "$AMENT_TRACE_SETUP_FILES" ]; then :; fi\n'
        "export ROS_SETUP_SOURCED=1\n",
        encoding="utf-8",
    )
    px4_msgs_setup.write_text(
        "export PX4_MSGS_SETUP_SOURCED=1\n", encoding="utf-8"
    )
    workspace = tmp_path / "ros2_ws"
    (workspace / "src").mkdir(parents=True)

    environment = os.environ.copy()
    environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
    environment["COLCON_LOG"] = str(colcon_log)
    environment["ROS_SETUP"] = str(ros_setup)
    environment["PX4_MSGS_SETUP"] = str(px4_msgs_setup)
    environment["ROS2_WORKSPACE"] = str(workspace)
    result = subprocess.run(
        ["bash", str(helper), "--test"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert colcon_log.read_text(encoding="utf-8").splitlines() == [
        "build --symlink-install",
        "test --event-handlers console_cohesion+",
        "test-result --verbose",
    ]
