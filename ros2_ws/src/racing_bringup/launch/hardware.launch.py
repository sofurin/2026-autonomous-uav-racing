from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration

from racing_bringup.hardware_transport import (
    serial_agent_command,
    udp_agent_command,
)


def _start_xrce_agent(context):
    enabled = LaunchConfiguration("start_xrce_agent").perform(context).lower()
    if enabled in {"false", "0", "off", "no"}:
        return []
    if enabled not in {"true", "1", "on", "yes"}:
        raise RuntimeError("start_xrce_agent must be true or false")

    transport = LaunchConfiguration("xrce_transport").perform(context).lower()
    if transport == "serial":
        command = serial_agent_command(
            LaunchConfiguration("px4_serial_device").perform(context),
            LaunchConfiguration("px4_serial_baud").perform(context),
        )
        device = Path(command[3])
        if not device.exists():
            raise RuntimeError(f"PX4 serial device does not exist: {device}")
    elif transport == "udp4":
        command = udp_agent_command(
            LaunchConfiguration("xrce_agent_port").perform(context)
        )
    else:
        raise RuntimeError("xrce_transport must be serial or udp4")

    return [
        ExecuteProcess(
            cmd=command,
            output="screen",
            emulate_tty=True,
        )
    ]


def generate_launch_description():
    description_share = Path(get_package_share_directory("racing_description"))
    control_share = Path(get_package_share_directory("racing_px4_control"))
    start_offboard_controller = LaunchConfiguration("start_offboard_controller")
    allow_mission_start = LaunchConfiguration("allow_mission_start")

    return LaunchDescription(
        [
            DeclareLaunchArgument("start_xrce_agent", default_value="false"),
            DeclareLaunchArgument(
                "xrce_transport",
                default_value=EnvironmentVariable(
                    "PX4_XRCE_TRANSPORT", default_value="serial"
                ),
            ),
            DeclareLaunchArgument(
                "xrce_agent_port",
                default_value=EnvironmentVariable(
                    "PX4_XRCE_UDP_PORT", default_value="8888"
                ),
            ),
            DeclareLaunchArgument(
                "px4_serial_device",
                default_value=EnvironmentVariable(
                    "PX4_SERIAL_DEVICE", default_value=""
                ),
            ),
            DeclareLaunchArgument(
                "px4_serial_baud",
                default_value=EnvironmentVariable(
                    "PX4_SERIAL_BAUD", default_value="921600"
                ),
            ),
            DeclareLaunchArgument(
                "start_offboard_controller", default_value="false"
            ),
            DeclareLaunchArgument("allow_mission_start", default_value="false"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(description_share / "launch" / "description.launch.py")
                ),
                launch_arguments={"use_sim_time": "false"}.items(),
            ),
            OpaqueFunction(function=_start_xrce_agent),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(control_share / "launch" / "offboard_mission.launch.py")
                ),
                condition=IfCondition(start_offboard_controller),
                launch_arguments={
                    "allow_mission_start": allow_mission_start,
                    "allow_arming_command": "false",
                    "auto_start": "false",
                }.items(),
            ),
            LogInfo(
                msg=(
                    "Hardware mode selected. XRCE transport and Offboard control "
                    "remain opt-in; automatic arming is disabled."
                )
            ),
        ]
    )
