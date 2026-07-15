from pathlib import Path
import re


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
        "start_depth_bridge",
        "start_infrared_bridge",
    ):
        assert f'"{argument}"' in source

    assert 'default_value="gz_team_racer"' in source
    assert '"px4_model_pose", default_value="0,0,0.075,0,0,0"' in source
    assert "start_px4_sitl.sh" in source
    assert "MicroXRCEAgent" in source
    assert "ros_gz_bridge" in source
    assert 'name="racing_color_bridge"' in source
    assert 'name="racing_depth_bridge"' in source
    assert 'name="racing_infrared_bridge"' in source
    assert "8888" in source


def test_project_bringup_includes_the_simulation_orchestrator() -> None:
    source = (
        SRC_ROOT / "racing_bringup" / "launch" / "simulation.launch.py"
    ).read_text(encoding="utf-8")

    assert 'get_package_share_directory("racing_simulation")' in source
    assert '"sitl.launch.py"' in source
    assert '"px4_model"' in source
    assert 'DeclareLaunchArgument("px4_model", default_value="gz_team_racer")' in source
    assert '"px4_model_pose", default_value="0,0,0.075,0,0,0"' in source


def test_competition_gui_demo_uses_the_official_start_pose_and_color_viewer() -> None:
    source = (
        SRC_ROOT / "racing_bringup" / "launch" / "competition_demo.launch.py"
    ).read_text(encoding="utf-8")

    assert '"px4_model": "gz_team_racer"' in source
    assert '"px4_world": "robocup_2025_baseline"' in source
    assert '"px4_model_pose": "-4,-3.65,0.095,0,0,0"' in source
    assert '"headless": "false"' in source
    assert '"start_camera_bridge": "true"' in source
    assert '"start_depth_bridge": "false"' in source
    assert '"start_infrared_bridge": "false"' in source
    assert '"rqt_image_view"' in source
    assert '"/camera/color/image_raw"' in source
    assert '"fly_known_course.py"' in source
    assert '"MESA_D3D12_DEFAULT_ADAPTER_NAME", "NVIDIA"' in source


def test_d435_bridge_contract_includes_metadata_depth_points_and_infrared() -> None:
    source = (PACKAGE_ROOT / "launch" / "sitl.launch.py").read_text(encoding="utf-8")

    for argument in (
        "color_camera_info_topic",
        "depth_camera_info_topic",
        "point_cloud_topic",
        "infra1_topic",
        "infra2_topic",
    ):
        assert f'"{argument}"' in source

    assert "sensor_msgs/msg/CameraInfo" in source
    assert "sensor_msgs/msg/PointCloud2" in source
    assert "gz.msgs.PointCloudPacked" in source
    assert 'additional_env={"GZ_IP": "127.0.0.1"}' in source

    d435 = (PACKAGE_ROOT / "models" / "realsense_d435" / "model.sdf").read_text(
        encoding="utf-8"
    )
    assert "/camera/color/image_raw" in d435
    assert "/camera/depth/image_raw" in d435
    assert "/camera/infra1/image_raw" in d435
    assert "/camera/infra2/image_raw" in d435


def test_gazebo_depth_point_cloud_source_is_remapped_to_the_camera_contract() -> None:
    source = (PACKAGE_ROOT / "launch" / "sitl.launch.py").read_text(encoding="utf-8")

    assert '"gz_point_cloud_topic"' in source
    assert re.search(
        r'DeclareLaunchArgument\(\s*"gz_point_cloud_topic",\s*'
        r'default_value="/camera/depth/image_raw/points".*?\)',
        source,
        re.DOTALL,
    )
    assert 'DeclareLaunchArgument("start_depth_bridge", default_value="false")' in source
    assert (
        'DeclareLaunchArgument("start_infrared_bridge", default_value="false")'
        in source
    )
    assert "(gz_point_cloud_topic, point_cloud_topic)" in source

    bringup_source = (
        SRC_ROOT / "racing_bringup" / "launch" / "simulation.launch.py"
    ).read_text(encoding="utf-8")
    assert re.search(
        r'DeclareLaunchArgument\(\s*"gz_point_cloud_topic",\s*'
        r'default_value="/camera/depth/image_raw/points".*?\)',
        bringup_source,
        re.DOTALL,
    )
    assert '"start_depth_bridge"' in bringup_source
    assert '"start_infrared_bridge"' in bringup_source


def test_sitl_uses_the_px4_owned_gazebo_server_config() -> None:
    launch_source = (PACKAGE_ROOT / "launch" / "sitl.launch.py").read_text(
        encoding="utf-8"
    )
    script_source = (PACKAGE_ROOT / "scripts" / "start_px4_sitl.sh").read_text(
        encoding="utf-8"
    )

    assert 'package_share / "config" / "gazebo_server.config"' not in launch_source
    assert 'Tools/simulation/gz/server.config' in script_source
