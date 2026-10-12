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

CAN_READY=false
if ip -details link show can0 2>/dev/null | grep -q '<[^>]*UP'; then
  CAN_READY=true
fi

if [[ "$SCOUT_SEND_CONTROL" == "true" && "$CAN_READY" == "false" ]]; then
  echo "can0 尚未 UP。按本机 CAN 设置 500 kbit/s 并启动接口后重试。"
  echo "  sudo ip link set can0 type can bitrate 500000"
  echo "  sudo ip link set can0 up"
  exit 2
fi

if [[ "$SCOUT_SEND_CONTROL" != "true" ]]; then
  echo "Scout 控制帧目前关闭；确认底盘型号、CAN 协议和急停后，才设置 SCOUT_SEND_CONTROL=true。"
fi
if [[ "$CAN_READY" != "true" ]]; then
  echo "can0 未启动，跳过 Scout CAN 节点；当前只能检查规划。"
fi

set +u
source /opt/ros/humble/setup.bash
source "$WORKSPACE_ROOT/install/setup.bash"
set -u
exec ros2 launch me_nav2_bringup real.launch.py mode:=nav \
  "map_yaml_file:=$NAV2_MAP_YAML" "start_can:=$CAN_READY" \
  "send_control:=$SCOUT_SEND_CONTROL"
