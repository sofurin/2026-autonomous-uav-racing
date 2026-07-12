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
                launch_arguments={"use_sim_time": "false"}.items(),
            ),
            LogInfo(
                msg=(
                    "Hardware mode selected. Camera driver and PX4 transport are not "
                    "started until their device identities are configured."
                )
            ),
        ]
    )
