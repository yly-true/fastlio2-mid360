import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    model = os.path.join(
        get_package_share_directory("gld_robot_description"),
        "model",
        "scout_mid360.urdf",
    )
    with open(model, encoding="utf-8") as urdf:
        robot_description = urdf.read()

    return LaunchDescription([
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": robot_description}],
            output="screen",
        ),
    ])
