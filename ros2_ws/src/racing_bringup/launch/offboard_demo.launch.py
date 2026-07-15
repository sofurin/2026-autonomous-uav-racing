from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration


def generate_launch_description():
    bringup_share = Path(get_package_share_directory("racing_bringup"))
    control_share = Path(get_package_share_directory("racing_px4_control"))
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "px4_dir",
                default_value=[EnvironmentVariable("HOME"), "/PX4-Autopilot"],
            ),
            DeclareLaunchArgument("px4_model", default_value="gz_team_racer"),
            DeclareLaunchArgument(
                "px4_world", default_value="robocup_2025_baseline"
            ),
            DeclareLaunchArgument(
                "px4_model_pose", default_value="-4,-3.65,0.075,0,0,0"
            ),
            DeclareLaunchArgument("headless", default_value="true"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(bringup_share / "launch" / "simulation.launch.py")
                ),
                launch_arguments={
                    "px4_dir": LaunchConfiguration("px4_dir"),
                    "px4_model": LaunchConfiguration("px4_model"),
                    "px4_world": LaunchConfiguration("px4_world"),
                    "px4_model_pose": LaunchConfiguration("px4_model_pose"),
                    "headless": LaunchConfiguration("headless"),
                    "start_camera_bridge": "false",
                    "start_depth_bridge": "false",
                    "start_infrared_bridge": "false",
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(control_share / "launch" / "offboard_mission.launch.py")
                ),
                launch_arguments={
                    "allow_arming_command": "true",
                    "auto_start": "true",
                }.items(),
            ),
            LogInfo(
                msg=(
                    "SIMULATION ONLY: automatic Offboard arming is enabled for "
                    "the minimal mission demo."
                )
            ),
        ]
    )

