# Copyright 2025 Lihan Chen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    map_pcd = os.path.join(
        get_package_share_directory("me_nav2_bringup"), "pcd", "工位.pcd")
    node = Node(
        package="small_gicp_relocalization",
        executable="small_gicp_relocalization_node",
        namespace="",
        output="screen",
        emulate_tty=True,  # 开启提示颜色
        parameters=[
            {
                "num_threads": 4,
                "num_neighbors": 10,
                "global_leaf_size": 0.25,
                "registered_leaf_size": 0.25,
                "max_dist_sq": 1.0,
                "min_inlier_ratio": 0.25,
                "max_mean_error": 3.0,
                "map_frame": "map",
                "odom_frame": "odom",
                "robot_base_frame": "body",
                "prior_pcd_file": LaunchConfiguration("map_pcd"),
                "input_cloud_topic": "/cloud_registered",
            }
        ],
    )

    odom_to_camera_init = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments=["--x", "0", "--y", "0", "--z", "0", "--roll", "0",
                   "--pitch", "0", "--yaw", "0", "--frame-id", "odom",
                   "--child-frame-id", "camera_init"],
    )

    return LaunchDescription([
        SetEnvironmentVariable(
            "LD_LIBRARY_PATH", "/usr/lib/aarch64-linux-gnu:" + os.environ.get("LD_LIBRARY_PATH", "")),
        DeclareLaunchArgument("map_pcd", default_value=map_pcd),
        odom_to_camera_init,
        node,
    ])
