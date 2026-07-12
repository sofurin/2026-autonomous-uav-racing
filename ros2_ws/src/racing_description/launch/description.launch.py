from pathlib import Path

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_share = Path(get_package_share_directory("racing_description"))
    model = package_share / "urdf" / "racing_uav.urdf.xacro"
    use_sim_time = LaunchConfiguration("use_sim_time")

    robot_description = xacro.process_file(str(model)).toxml()

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                parameters=[
                    {
                        "robot_description": robot_description,
                        "use_sim_time": ParameterValue(use_sim_time, value_type=bool),
                    }
                ],
                output="screen",
            ),
        ]
    )
