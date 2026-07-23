from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share = Path(get_package_share_directory("racing_px4_control"))
    return LaunchDescription(
        [
            DeclareLaunchArgument("allow_mission_start", default_value="false"),
            DeclareLaunchArgument("allow_arming_command", default_value="false"),
            DeclareLaunchArgument("auto_start", default_value="false"),
            Node(
                package="racing_px4_control",
                executable="offboard_mission",
                name="offboard_mission",
                output="screen",
                parameters=[
                    str(package_share / "config" / "px4_interface.yaml"),
                    {
                        "allow_mission_start": LaunchConfiguration(
                            "allow_mission_start"
                        ),
                        "allow_arming_command": LaunchConfiguration(
                            "allow_arming_command"
                        ),
                        "auto_start": LaunchConfiguration("auto_start"),
                    },
                ],
            ),
        ]
    )
