"""One entry point for MID360 mapping, relocalization, and navigation."""

import os
from datetime import datetime

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _scout_node(send_control):
    return Node(
        package="scout_can", executable="scout_can_node", name="scout_can",
        output="screen", parameters=[{
            "interface_name": "can0", "send_control": send_control,
            "use_cmd_vel": True, "publish_odom": False,
            "publish_tf": False, "log_frames": False,
        }],
    )


def _start(context):
    mode = LaunchConfiguration("mode").perform(context)
    if mode not in ("mapping", "relocalization", "nav"):
        raise RuntimeError("mode must be mapping, relocalization, or nav")
    start_can = LaunchConfiguration("start_can").perform(context).lower() == "true"
    send_control = LaunchConfiguration("send_control").perform(context).lower() == "true"
    if send_control and not start_can:
        raise RuntimeError("send_control requires start_can:=true")
    if mode == "relocalization" and start_can:
        raise RuntimeError("CAN control is available in mapping and nav modes")

    bringup = get_package_share_directory("me_nav2_bringup")
    fast_lio = get_package_share_directory("fast_lio")
    driver = get_package_share_directory("livox_ros_driver2")
    lio_parameters = {"use_sim_time": False}
    if mode == "mapping":
        lio_parameters["map_file_path"] = LaunchConfiguration("map_file_path").perform(context)
    actions = [
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(driver, "launch", "fast_lio_msg_MID360_launch.py"))),
        Node(
            package="fast_lio", executable="fastlio_mapping", output="screen",
            parameters=[
                os.path.join(fast_lio, "config", "mid360.yaml" if mode == "mapping" else "mid360_nav.yaml"),
                lio_parameters,
            ],
        ),
    ]

    if mode == "mapping":
        if start_can:
            actions.append(_scout_node(send_control))
        if LaunchConfiguration("show_rviz").perform(context).lower() == "true":
            actions.append(Node(
                package="rviz2", executable="rviz2", output="screen",
                arguments=["-d", os.path.join(fast_lio, "rviz", "fastlio.rviz")]))
        return actions

    map_pcd = LaunchConfiguration("map_pcd").perform(context)
    if not os.path.isfile(map_pcd):
        raise RuntimeError(f"3D map PCD does not exist: {map_pcd}")

    actions.extend([
        Node(
            package="tf2_ros", executable="static_transform_publisher",
            arguments=["--x", "0", "--y", "0", "--z", "0",
                       "--roll", "0", "--pitch", "0", "--yaw", "0",
                       "--frame-id", "base", "--child-frame-id", "livox"],
        ),
        Node(
            package="me_nav2_bringup", executable="fastlio_bridge", output="screen",
            parameters=[os.path.join(fast_lio, "config", "mid360_nav.yaml"), {"use_sim_time": False}],
        ),
        Node(
            package="small_gicp_relocalization",
            executable="small_gicp_relocalization_node", output="screen",
            parameters=[{
                "num_threads": 4,
                "num_neighbors": 10,
                "global_leaf_size": 0.25,
                "registered_leaf_size": 0.25,
                "max_dist_sq": 1.0,
                "min_inlier_ratio": 0.25,
                "max_mean_error": 3.0,
                "prior_pcd_file": map_pcd,
            }],
        ),
    ])

    if mode == "relocalization":
        if LaunchConfiguration("show_rviz").perform(context).lower() == "true":
            gicp = get_package_share_directory("small_gicp_relocalization")
            actions.append(Node(
                package="rviz2", executable="rviz2", output="screen",
                arguments=["-d", os.path.join(gicp, "rviz", "relocalization.rviz")]))
        return actions

    map_yaml = LaunchConfiguration("map_yaml_file").perform(context)
    if not os.path.isfile(map_yaml):
        raise RuntimeError(f"Checked 2D map YAML is required: {map_yaml}")
    nav_params = os.path.join(bringup, "config", "nav2_params.yaml")
    actions.extend([
        Node(
            package="pointcloud_to_laserscan", executable="pointcloud_to_laserscan_node",
            name="Pointcloud2d_3d", output="screen",
            parameters=[os.path.join(bringup, "config", "Pointcloud2d_3d.yaml"),
                        {"use_sim_time": False}],
            remappings=[("cloud_in", "/registered_scan"), ("scan", "/scan")],
        ),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("nav2_bringup"),
                         "launch", "navigation_launch.py")),
            launch_arguments={"params_file": nav_params,
                              "use_sim_time": "false", "autostart": "true"}.items()),
        Node(
            package="nav2_map_server", executable="map_server", name="map_server",
            output="screen", parameters=[nav_params, {"yaml_filename": map_yaml,
                                                        "use_sim_time": False}],
        ),
        Node(
            package="nav2_lifecycle_manager", executable="lifecycle_manager",
            name="lifecycle_manager_map", output="screen",
            parameters=[{"use_sim_time": False, "autostart": True,
                         "node_names": ["map_server"]}],
        ),
    ])
    if start_can:
        actions.append(_scout_node(send_control))
    if LaunchConfiguration("show_rviz").perform(context).lower() == "true":
        actions.append(Node(
            package="rviz2", executable="rviz2", output="screen",
            arguments=["-d", os.path.join(bringup, "rviz", "nav2.rviz")]))
    return actions


def generate_launch_description():
    bringup = get_package_share_directory("me_nav2_bringup")
    map_output = os.path.join(os.getcwd(), f"mid360_{datetime.now():%Y%m%d_%H%M%S}.pcd")
    return LaunchDescription([
        SetEnvironmentVariable(
            "LD_LIBRARY_PATH", "/usr/lib/aarch64-linux-gnu:" + os.environ.get("LD_LIBRARY_PATH", "")),
        DeclareLaunchArgument("mode", default_value="mapping"),
        DeclareLaunchArgument("map_file_path", default_value=map_output),
        DeclareLaunchArgument("map_pcd", default_value=os.path.join(bringup, "pcd", "工位.pcd")),
        DeclareLaunchArgument("map_yaml_file", default_value=""),
        DeclareLaunchArgument("show_rviz", default_value="true"),
        DeclareLaunchArgument("start_can", default_value="false"),
        DeclareLaunchArgument("send_control", default_value="false"),
        OpaqueFunction(function=_start),
    ])
