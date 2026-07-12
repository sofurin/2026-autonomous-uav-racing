from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]
SRC_ROOT = PACKAGE_ROOT.parent


def test_sitl_launch_exposes_replaceable_model_and_process_switches() -> None:
    source = (PACKAGE_ROOT / "launch" / "sitl.launch.py").read_text(encoding="utf-8")

    for argument in (
        "px4_dir",
        "px4_model",
        "px4_world",
        "px4_model_pose",
        "start_px4",
        "start_xrce_agent",
        "start_camera_bridge",
    ):
        assert f'"{argument}"' in source

    assert 'default_value="gz_x500_depth"' in source
    assert "start_px4_sitl.sh" in source
    assert "MicroXRCEAgent" in source
    assert "ros_gz_bridge" in source
    assert "8888" in source


def test_project_bringup_includes_the_simulation_orchestrator() -> None:
    source = (
        SRC_ROOT / "racing_bringup" / "launch" / "simulation.launch.py"
    ).read_text(encoding="utf-8")

    assert 'get_package_share_directory("racing_simulation")' in source
    assert '"sitl.launch.py"' in source
    assert '"px4_model"' in source
