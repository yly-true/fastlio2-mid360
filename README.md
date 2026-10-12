# MID360 + FAST-LIO2 + 3D 重定位（ROS 2 Humble / Orin NX）

只使用 `/home/orin-nx-1/Lidar_nav2_ws`。本机是 ARM64。MID360 接 `enP8p1s0`，主机地址 `192.168.1.50/24`，雷达地址 `192.168.1.3`。雷达序列号末尾 58 与当前 IP 无关。

## 编译

```bash
cd /home/orin-nx-1/Lidar_nav2_ws
./scripts/build.sh                    # -j4；跳过 Gazebo 等无关包
source /opt/ros/humble/setup.bash
source install/setup.bash
export LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH
```

每个新终端都运行上面三行环境命令；不要再 source `ws_livox`。

## 建图并保存

先确认有线接口有载波和 `192.168.1.50/24`。运行 `./scripts/mapping_real.sh`。手持雷达时先保持静止，等 FAST-LIO 终端出现 `IMU Initial Done` 后再缓慢移动；出现明显位姿跳变就重启建图。RViz2 的 Fixed Frame 是 `camera_init`；`/cloud_registered` 显示最近 30 秒的三维点云，鼠标左键拖动可旋转视角。换地点后重新建图，脚本会生成带时间戳的新 PCD 路径，不覆盖旧地图。

建图结束**先保存，再退出**。在另一个已 source 的终端运行：

```bash
ros2 service call /map_save std_srvs/srv/Trigger '{}'
```

看到 `success=True` 后，检查启动脚本打印的 PCD 路径确实有文件且非空，再按 `Ctrl-C`。本次地图已保存为 `src/me_nav2_bringup/pcd/工位.pcd`。

## 3D 重定位

结束建图进程后运行：

```bash
ros2 launch small_gicp_relocalization mid360_relocalization.launch.py
```

RViz2 的 Fixed Frame 为 `map`，灰色是已保存的地图。等 `/cloud_registered` 和 `/Odometry` 有数据后，用顶部 **2D Pose Estimate** 在旧地图中点选机器人当前的大致位置与方向。这是 3D GICP 的初始猜测，不是 2D 定位。匹配前绿色实时点云暂时不可见；日志出现 `GICP matched` 后，它应与灰色地图重合，此时才有 `map → odom → camera_init → body`。可用 `ros2 run tf2_ros tf2_echo map body` 检查。

如需指定另一张 PCD：

```bash
ros2 launch small_gicp_relocalization mid360_relocalization.launch.py map_pcd:=/绝对路径/地图.pcd
```

启动前检查：

```bash
ip -br addr show enP8p1s0
ip route get 192.168.1.3       # 应显示 dev enP8p1s0 src 192.168.1.50
ping -c 3 192.168.1.3
```

若 `/livox/lidar` 没数据，先修网线、供电和主机 IP；若 `/Odometry` 没数据，检查 `/livox/imu` 与 `/livox/lidar`。

本机已在通电 MID360 上确认点云、IMU、FAST-LIO2 里程计和 RViz2 正常运行。驱动现以 Livox `CustomMsg` 输入 FAST-LIO2，并固定 MID360 雷达与 IMU 外参；匹配丢失时不再把该帧加入地图。调整后静止约 22 秒位移约 0.003 米、转弯 25 秒未复现数十米跳变；长距离建图和 3D 重定位仍需现场验证。若位姿跳变或地图重影，重启建图，不要保存该次结果。

## 后续导航

当前先验证 FAST-LIO2 和 3D 重定位。`pcd2pgm` 只按 `camera_init` 中的 Z 高度截取点，再投影到 XY：有点的格子是障碍，其余格子仍为未知；尚未生成可直接用于新地点导航的 2D 地图。Nav2、2D 地图及 Scout CAN 的现场事项见 [TODO.md](TODO.md)；上游说明见 [README_UPSTREAM.md](README_UPSTREAM.md)。
