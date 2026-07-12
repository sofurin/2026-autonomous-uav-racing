from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression


def generate_launch_description():
    mode = LaunchConfiguration("mode")
    package_share = Path(get_package_share_directory("racing_bringup"))

    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(package_share / "launch" / "hardware.launch.py")),
        condition=IfCondition(PythonExpression(["'", mode, "' == 'hardware'"])),
    )
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(package_share / "launch" / "simulation.launch.py")),
        condition=IfCondition(PythonExpression(["'", mode, "' == 'simulation'"])),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "mode",
                default_value="simulation",
                choices=["hardware", "simulation"],
                description="Select the real aircraft or PX4 SITL integration path.",
            ),
            LogInfo(msg=["Racing bringup mode: ", mode]),
            hardware,
            simulation,
        ]
    )
