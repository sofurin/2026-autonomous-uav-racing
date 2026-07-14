from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    LogInfo,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution


def generate_launch_description():
    bringup_share = Path(get_package_share_directory("racing_bringup"))
    simulation_share = Path(get_package_share_directory("racing_simulation"))

    px4_dir = LaunchConfiguration("px4_dir")
    start_course = LaunchConfiguration("start_course")
    start_image_viewer = LaunchConfiguration("start_image_viewer")

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(bringup_share / "launch" / "simulation.launch.py")
        ),
        launch_arguments={
            "px4_dir": px4_dir,
            "px4_model": "gz_team_racer",
            "px4_world": "robocup_2025_baseline",
            "px4_model_pose": "-4,-3.65,0,0,0,0",
            "headless": "false",
            "start_camera_bridge": "true",
            "start_depth_bridge": "false",
            "start_infrared_bridge": "false",
        }.items(),
    )

    image_viewer = TimerAction(
        period=5.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    "ros2",
                    "run",
                    "rqt_image_view",
                    "rqt_image_view",
                    "/camera/color/image_raw",
                    "--on-top",
                ],
                condition=IfCondition(start_image_viewer),
                output="screen",
            )
        ],
    )

    course = TimerAction(
        period=12.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    "python3",
                    str(
                        simulation_share
                        / "tools"
                        / "robocup_2025"
                        / "fly_known_course.py"
                    ),
                    "--connection",
                    "udpin:127.0.0.1:14540",
                ],
                condition=IfCondition(start_course),
                output="screen",
                emulate_tty=True,
            )
        ],
    )

    return LaunchDescription(
        [
            SetEnvironmentVariable(
                "MESA_D3D12_DEFAULT_ADAPTER_NAME", "NVIDIA"
            ),
            SetEnvironmentVariable("QT_X11_NO_MITSHM", "1"),
            DeclareLaunchArgument(
                "px4_dir",
                default_value=PathJoinSubstitution(
                    [EnvironmentVariable("HOME"), "PX4-Autopilot"]
                ),
            ),
            DeclareLaunchArgument("start_course", default_value="true"),
            DeclareLaunchArgument("start_image_viewer", default_value="true"),
            LogInfo(
                msg=(
                    "Competition GUI demo: team_racer at start zone, "
                    "color camera and known course enabled."
                )
            ),
            simulation,
            image_viewer,
            course,
        ]
    )
