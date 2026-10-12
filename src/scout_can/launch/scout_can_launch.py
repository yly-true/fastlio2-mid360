from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("send_control", default_value="false"),
        Node(
            package="scout_can",
            executable="scout_can_node",
            name="scout_can",
            output="screen",
            parameters=[{
                "interface_name": "can0",
                "send_control": LaunchConfiguration("send_control"),
                "use_cmd_vel": True,
                "publish_odom": False,
                "publish_tf": False,
                "log_frames": False,
            }],
        ),
    ])
