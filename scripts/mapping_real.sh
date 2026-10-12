#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(dirname -- "$SCRIPT_DIR")"
MAP_OUTPUT="${MAP_OUTPUT:-$WORKSPACE_ROOT/src/me_nav2_bringup/pcd/mid360_$(date +%Y%m%d_%H%M%S).pcd}"
mkdir -p "$(dirname -- "$MAP_OUTPUT")"

open_ros_window() {
  local title="$1"
  shift
  gnome-terminal --title="$title" -- bash -c '
    cd "$1" || exit 1
    source /opt/ros/humble/setup.bash || exit 1
    source install/setup.bash || exit 1
    shift
    "$@"
    exec bash
  ' bash "$WORKSPACE_ROOT" "$@"
}

open_ros_window "MID360 驱动" ros2 launch livox_ros_driver2 fast_lio_msg_MID360_launch.py
open_ros_window "FAST-LIO 建图" ros2 launch fast_lio mapping.launch.py \
  use_sim_time:=false config_file:=mid360.yaml rviz:=true "map_file_path:=$MAP_OUTPUT"
open_ros_window "Scout 与 MID360 TF" ros2 launch gld_robot_description scout_mid360_description_launch.py

printf '地图保存路径：%s\n' "$MAP_OUTPUT"
printf '手持雷达请先保持静止，等 FAST-LIO 终端出现 IMU Initial Done 后再缓慢移动。\n'
printf '建图完成后先在新终端 source 环境并运行：ros2 service call /map_save std_srvs/srv/Trigger "{}"\n'
printf '确认 success=True 且文件已生成，再按 Ctrl-C。\n'
