import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def include(package, file_name, arguments=None):
    path = os.path.join(get_package_share_directory(package), "launch", file_name)
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(path),
        launch_arguments=(arguments or {}).items(),
    )


def generate_launch_description():
    default_map = os.path.join(
        get_package_share_directory("me_nav2_bringup"), "pcd", "工位.pcd")
    rviz_config = os.path.join(
        get_package_share_directory("small_gicp_relocalization"), "rviz", "relocalization.rviz")

    return LaunchDescription([
        SetEnvironmentVariable(
            "LD_LIBRARY_PATH", "/usr/lib/aarch64-linux-gnu:" + os.environ.get("LD_LIBRARY_PATH", "")),
        DeclareLaunchArgument("map_pcd", default_value=default_map),
        DeclareLaunchArgument("show_rviz", default_value="true"),
        include("livox_ros_driver2", "fast_lio_msg_MID360_launch.py"),
        include("fast_lio", "mapping.launch.py", {
            "config_file": "mid360_nav.yaml", "rviz": "false"}),
        include("small_gicp_relocalization", "small_gicp_relocalization_launch.py", {
            "map_pcd": LaunchConfiguration("map_pcd")}),
        Node(
            package="rviz2", executable="rviz2",
            arguments=["-d", rviz_config],
            condition=IfCondition(LaunchConfiguration("show_rviz")),
        ),
    ])
