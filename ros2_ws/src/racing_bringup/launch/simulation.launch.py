from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    description_share = Path(get_package_share_directory("racing_description"))

    return LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(description_share / "launch" / "description.launch.py")
                ),
                launch_arguments={"use_sim_time": "true"}.items(),
            ),
            LogInfo(
                msg=(
                    "Simulation mode selected. Gazebo and PX4 SITL processes remain "
                    "disabled until their installed versions are pinned."
                )
            ),
        ]
    )
