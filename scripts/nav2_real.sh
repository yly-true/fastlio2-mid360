#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(dirname -- "$SCRIPT_DIR")"
NAV2_MAP_YAML="${NAV2_MAP_YAML:-}"
SCOUT_SEND_CONTROL="${SCOUT_SEND_CONTROL:-false}"

if [[ -z "$NAV2_MAP_YAML" || ! -f "$NAV2_MAP_YAML" ]]; then
  echo "先准备与工位.pcd 对齐并检查过的 2D 地图 YAML。"
  echo "运行方式：NAV2_MAP_YAML=/绝对路径/地图.yaml ./scripts/nav2_real.sh"
  exit 2
fi

if ! ip -details link show can0 2>/dev/null | grep -q '<[^>]*UP'; then
  echo "can0 尚未 UP。按本机 CAN 设置 500 kbit/s 并启动接口后重试。"
  echo "  sudo ip link set can0 type can bitrate 500000"
  echo "  sudo ip link set can0 up"
  exit 2
fi

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
open_ros_window "FAST-LIO 里程计" ros2 launch fast_lio mapping.launch.py \
  use_sim_time:=false config_file:=mid360_nav.yaml rviz:=false
open_ros_window "Scout 与 MID360 TF" ros2 launch gld_robot_description scout_mid360_description_launch.py
open_ros_window "FAST-LIO 接口与 /odom" ros2 launch lio_interface fastlio_lio_interface_launch.py use_sim_time:=false
open_ros_window "差分里程计与 /scan" ros2 launch sensor_scan_generation sensor_scan_generation_launch.py use_sim_time:=false
open_ros_window "3D 点云转实时 /scan" ros2 launch me_nav2_bringup pointcloud_to_laserscan_launch.py use_sim_time:=false
open_ros_window "3D GICP 定位" ros2 launch small_gicp_relocalization small_gicp_relocalization_launch.py
open_ros_window "Scout CAN 控制" ros2 launch scout_can scout_can_launch.py "send_control:=$SCOUT_SEND_CONTROL"
open_ros_window "Nav2 导航" ros2 launch me_nav2_bringup my_nav2_launch.py "map_yaml_file:=$NAV2_MAP_YAML"

if [[ "$SCOUT_SEND_CONTROL" != "true" ]]; then
  echo "Scout 控制帧目前关闭；确认底盘型号、CAN 协议和急停后，才设置 SCOUT_SEND_CONTROL=true。"
fi
