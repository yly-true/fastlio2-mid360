#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(dirname -- "$SCRIPT_DIR")"
MAP_OUTPUT="${MAP_OUTPUT:-$WORKSPACE_ROOT/src/me_nav2_bringup/pcd/mid360_$(date +%Y%m%d_%H%M%S).pcd}"
SCOUT_SEND_CONTROL="${SCOUT_SEND_CONTROL:-false}"
mkdir -p "$(dirname -- "$MAP_OUTPUT")"

if [[ "$SCOUT_SEND_CONTROL" == "true" ]]; then
  if ! ip -details link show can0 2>/dev/null | grep -q '<[^>]*UP'; then
    echo "can0 尚未 UP。先按底盘要求设置 500 kbit/s 并启动 CAN 接口。"
    exit 2
  fi
  echo "建图将同时启动 Scout CAN。等 IMU Initial Done 后，在另一终端运行 ros2 run keyboard_teleop keyboard_teleop。"
fi

printf '地图保存路径：%s\n' "$MAP_OUTPUT"
printf '手持雷达请先保持静止，等 FAST-LIO 终端出现 IMU Initial Done 后再缓慢移动。\n'
printf '建图完成后先在新终端 source 环境并运行：ros2 service call /map_save std_srvs/srv/Trigger "{}"\n'
printf '确认 success=True 且文件已生成，再按 Ctrl-C。\n'

set +u
source /opt/ros/humble/setup.bash
source "$WORKSPACE_ROOT/install/setup.bash"
set -u
exec ros2 launch me_nav2_bringup real.launch.py mode:=mapping \
  "map_file_path:=$MAP_OUTPUT" "start_can:=$SCOUT_SEND_CONTROL" \
  "send_control:=$SCOUT_SEND_CONTROL"
