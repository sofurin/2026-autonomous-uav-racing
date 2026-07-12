from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    description_share = Path(get_package_share_directory("racing_description"))
    simulation_share = Path(get_package_share_directory("racing_simulation"))

    simulation_arguments = {
        name: LaunchConfiguration(name)
        for name in (
            "px4_dir",
            "px4_model",
            "px4_world",
            "px4_model_pose",
            "start_px4",
            "start_xrce_agent",
            "start_camera_bridge",
            "headless",
            "xrce_agent_port",
            "color_topic",
            "depth_topic",
        )
    }

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "px4_dir",
                default_value="/root/docker_ws/uav_test/src/PX4-Autopilot",
            ),
            DeclareLaunchArgument("px4_model", default_value="gz_x500_depth"),
            DeclareLaunchArgument("px4_world", default_value="default"),
            DeclareLaunchArgument(
                "px4_model_pose", default_value="0,0,0,0,0,0"
            ),
            DeclareLaunchArgument("start_px4", default_value="true"),
            DeclareLaunchArgument("start_xrce_agent", default_value="true"),
            DeclareLaunchArgument("start_camera_bridge", default_value="true"),
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("xrce_agent_port", default_value="8888"),
            DeclareLaunchArgument(
                "color_topic", default_value="/camera/color/image_raw"
            ),
            DeclareLaunchArgument(
                "depth_topic", default_value="/camera/depth/image_raw"
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(description_share / "launch" / "description.launch.py")
                ),
                launch_arguments={"use_sim_time": "true"}.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(simulation_share / "launch" / "sitl.launch.py")
                ),
                launch_arguments=simulation_arguments.items(),
            ),
            LogInfo(msg="Simulation mode selected with project-owned orchestration."),
        ]
    )
