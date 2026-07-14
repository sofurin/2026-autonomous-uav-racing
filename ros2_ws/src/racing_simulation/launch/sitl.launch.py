from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share = Path(get_package_share_directory("racing_simulation"))
    start_script = package_share / "scripts" / "start_px4_sitl.sh"

    px4_dir = LaunchConfiguration("px4_dir")
    px4_model = LaunchConfiguration("px4_model")
    px4_world = LaunchConfiguration("px4_world")
    px4_model_pose = LaunchConfiguration("px4_model_pose")
    start_px4 = LaunchConfiguration("start_px4")
    start_xrce_agent = LaunchConfiguration("start_xrce_agent")
    start_camera_bridge = LaunchConfiguration("start_camera_bridge")
    start_depth_bridge = LaunchConfiguration("start_depth_bridge")
    start_infrared_bridge = LaunchConfiguration("start_infrared_bridge")
    headless = LaunchConfiguration("headless")
    xrce_agent_port = LaunchConfiguration("xrce_agent_port")
    color_topic = LaunchConfiguration("color_topic")
    color_camera_info_topic = LaunchConfiguration("color_camera_info_topic")
    depth_topic = LaunchConfiguration("depth_topic")
    depth_camera_info_topic = LaunchConfiguration("depth_camera_info_topic")
    gz_point_cloud_topic = LaunchConfiguration("gz_point_cloud_topic")
    point_cloud_topic = LaunchConfiguration("point_cloud_topic")
    infra1_topic = LaunchConfiguration("infra1_topic")
    infra2_topic = LaunchConfiguration("infra2_topic")

    px4 = ExecuteProcess(
        cmd=[
            str(start_script),
            "--px4-dir",
            px4_dir,
            "--model",
            px4_model,
            "--world",
            px4_world,
            "--pose",
            px4_model_pose,
            "--models-dir",
            str(package_share / "models"),
            "--worlds-dir",
            str(package_share / "worlds"),
        ],
        additional_env={"RACING_HEADLESS": headless},
        condition=IfCondition(start_px4),
        output="screen",
        emulate_tty=True,
    )

    xrce_agent = ExecuteProcess(
        cmd=["MicroXRCEAgent", "udp4", "-p", xrce_agent_port],
        condition=IfCondition(start_xrce_agent),
        output="screen",
        emulate_tty=True,
    )

    color_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="racing_color_bridge",
        arguments=[
            [color_topic, "@sensor_msgs/msg/Image[gz.msgs.Image"],
            [
                color_camera_info_topic,
                "@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
            ],
        ],
        condition=IfCondition(start_camera_bridge),
        additional_env={"GZ_IP": "127.0.0.1"},
        output="screen",
    )

    depth_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="racing_depth_bridge",
        arguments=[
            [depth_topic, "@sensor_msgs/msg/Image[gz.msgs.Image"],
            [
                depth_camera_info_topic,
                "@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
            ],
            [
                gz_point_cloud_topic,
                "@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked",
            ],
        ],
        condition=IfCondition(start_depth_bridge),
        remappings=[(gz_point_cloud_topic, point_cloud_topic)],
        additional_env={"GZ_IP": "127.0.0.1"},
        output="screen",
    )

    infrared_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="racing_infrared_bridge",
        arguments=[
            [infra1_topic, "@sensor_msgs/msg/Image[gz.msgs.Image"],
            [infra2_topic, "@sensor_msgs/msg/Image[gz.msgs.Image"],
        ],
        condition=IfCondition(start_infrared_bridge),
        additional_env={"GZ_IP": "127.0.0.1"},
        output="screen",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "px4_dir",
                default_value=EnvironmentVariable(
                    "PX4_AUTOPILOT_DIR",
                    default_value="/root/docker_ws/uav_test/src/PX4-Autopilot",
                ),
                description="External PX4-Autopilot checkout used by SITL.",
            ),
            DeclareLaunchArgument(
                "px4_model",
                default_value="gz_team_racer",
                description="PX4 Gazebo model target; gz_x500_depth remains selectable.",
            ),
            DeclareLaunchArgument("px4_world", default_value="default"),
            DeclareLaunchArgument(
                "px4_model_pose", default_value="0,0,0,0,0,0"
            ),
            DeclareLaunchArgument("start_px4", default_value="true"),
            DeclareLaunchArgument("start_xrce_agent", default_value="true"),
            DeclareLaunchArgument("start_camera_bridge", default_value="true"),
            DeclareLaunchArgument("start_depth_bridge", default_value="false"),
            DeclareLaunchArgument("start_infrared_bridge", default_value="false"),
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("xrce_agent_port", default_value="8888"),
            DeclareLaunchArgument(
                "color_topic", default_value="/camera/color/image_raw"
            ),
            DeclareLaunchArgument(
                "color_camera_info_topic",
                default_value="/camera/color/camera_info",
            ),
            DeclareLaunchArgument(
                "depth_topic", default_value="/camera/depth/image_raw"
            ),
            DeclareLaunchArgument(
                "depth_camera_info_topic",
                default_value="/camera/depth/camera_info",
            ),
            DeclareLaunchArgument(
                "gz_point_cloud_topic",
                default_value="/camera/depth/image_raw/points",
                description="Gazebo point-cloud source published by the D435 depth sensor.",
            ),
            DeclareLaunchArgument(
                "point_cloud_topic",
                default_value="/camera/depth/image_raw/points",
                description="Stable ROS point-cloud topic exposed to perception and RViz.",
            ),
            DeclareLaunchArgument(
                "infra1_topic", default_value="/camera/infra1/image_raw"
            ),
            DeclareLaunchArgument(
                "infra2_topic", default_value="/camera/infra2/image_raw"
            ),
            LogInfo(msg=["PX4 SITL model: ", px4_model, ", world: ", px4_world]),
            px4,
            xrce_agent,
            color_bridge,
            depth_bridge,
            infrared_bridge,
        ]
    )
