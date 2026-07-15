from pathlib import Path
import re


# Repository-level tests are invoked from the checkout root. Keeping the base
# relative avoids WSL drvfs path-encoding issues with Chinese host directories.
REPOSITORY_ROOT = Path(".")


def _read(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def test_external_dependencies_are_machine_readable_and_pinned() -> None:
    repositories = _read("dependencies.repos")

    expected_revisions = {
        "PX4-Autopilot": "6737fe1c3754a81a983b8f5aea6797b7d1669be6",
        "px4_msgs": "a5aec95ed69086467b1f92de30093a04d03fd1d4",
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
    assert "/dev/ttyUSB0" not in environment
    assert "/dev/ttyACM0" not in environment
