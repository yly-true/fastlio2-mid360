#!/usr/bin/env bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(dirname -- "$SCRIPT_DIR")"
cd "$WORKSPACE_ROOT" || exit 1

# Build against Humble, not the workspace currently sourced by the shell.
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH
source /opt/ros/humble/setup.bash
export LD_LIBRARY_PATH="/usr/lib/aarch64-linux-gnu:/usr/local/lib:${LD_LIBRARY_PATH:-}"
export MAKEFLAGS="-j4 -l4"

colcon build --symlink-install --parallel-workers 1 \
  --packages-up-to \
    livox_ros_driver2 fast_lio lio_interface sensor_scan_generation \
    me_nav2_bringup small_gicp_relocalization scout_can gld_robot_description pcd2pgm \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
