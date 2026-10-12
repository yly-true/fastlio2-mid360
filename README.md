# MID360 + FAST-LIO2 + 3D 重定位（ROS 2 Humble / Orin NX）

实车部署工作空间是 `/home/orin-nx-1/Lidar_nav2_ws`，设备为 ARM64。MID360 接 `enP8p1s0`，主机地址 `192.168.1.50/24`，雷达地址 `192.168.1.3`；换设备或网卡时先核对 `src/livox_ros_driver2/config/MID360_config.json` 和主机网络配置。统一启动入口是 `me_nav2_bringup/launch/real.launch.py`，通过 `mode:=mapping|relocalization|nav` 选择模式。默认 colcon 只识别 6 个包：`fast_lio`、`livox_ros_driver2`、`me_nav2_bringup`、`small_gicp_relocalization`、`scout_can`、`pcd2pgm`；备用源码由 `COLCON_IGNORE` 排除。

## 编译

```bash
cd /home/orin-nx-1/Lidar_nav2_ws
./scripts/build.sh
source /opt/ros/humble/setup.bash
source install/setup.bash
```

`build.sh` 使用 4 个 Make 任务、1 个 colcon 包并行编译。每个新终端重新执行两条 `source` 命令；不要再 source `ws_livox`。

## 建图并保存

先确认有线接口有载波和 `192.168.1.50/24`：

```bash
ip -br addr show enP8p1s0
ip route get 192.168.1.3  # 应显示 dev enP8p1s0 src 192.168.1.50
ping -c 3 192.168.1.3
./scripts/mapping_real.sh
```

手持雷达时先保持静止，等 FAST-LIO 输出 `IMU Initial Done` 后再缓慢移动；出现明显位姿跳变或地图重影就重启建图，不要保存该次结果。第一次建图的世界坐标为 `fastlio2old`，RViz2 Fixed Frame 也设为它。脚本会打印带时间戳的新 PCD 路径，不覆盖旧地图。

建图结束**先保存，再退出**。在另一个已 source 的终端运行：

```bash
ros2 service call /map_save std_srvs/srv/Trigger '{}'
```

看到 `success=True` 后，检查启动脚本打印的 PCD 路径确实有文件且非空，再按 `Ctrl-C`。仓库现有地图为 `src/me_nav2_bringup/pcd/工位.pcd`；新建图后，重定位时需通过 `map_pcd` 传入新 PCD 的绝对路径。

## 3D 重定位

结束建图进程后运行：

```bash
ros2 launch me_nav2_bringup real.launch.py mode:=relocalization
```

RViz2 的 Fixed Frame 为 `map`，灰色是已保存的地图。等 `/registered_scan` 和 `/odom` 有数据后，用顶部 **2D Pose Estimate** 在旧地图中点选机器人当前的大致位置与方向。这是 3D GICP 的初始猜测，不是 2D 定位。匹配前绿色实时点云暂时不可见；日志出现 `GICP matched` 后，实时点云应与灰色地图重合。第二次 FAST-LIO 的世界坐标叫 `fastlio2new`；Nav2 中 `map` 与旧地图 `fastlio2old` 数值一致，`odom` 与 `fastlio2new` 数值一致。GICP 发布二者间的变换，导航 TF 为 `map → odom → base → livox`，其中 `base` 和 `livox` 完全重合；可用 `ros2 run tf2_ros tf2_echo map base` 检查。

如需指定另一张 PCD：

```bash
ros2 launch me_nav2_bringup real.launch.py mode:=relocalization map_pcd:=/绝对路径/地图.pcd
```

启动前检查：

```bash
ip -br addr show enP8p1s0
ip route get 192.168.1.3       # 应显示 dev enP8p1s0 src 192.168.1.50
ping -c 3 192.168.1.3
```

若 `/livox/lidar` 没数据，先修网线、供电和主机 IP；若 `/Odometry` 没数据，检查 `/livox/imu` 与 `/livox/lidar`。

先前已在通电 MID360 上观察到点云、IMU、FAST-LIO2 里程计和 RViz2 正常运行，也曾初步目视确认 `工位.pcd` 的 3D 重定位。当前统一入口和桥接节点已通过构建及合成数据检查，**尚未在 Orin NX 装车后完成整链路实测**；长距离运动稳定性和重定位精度仍需现场核对。

## 后续导航

当前先验证 FAST-LIO2 和 3D 重定位。`pcd2pgm` 只按 `fastlio2old` 中的 Z 高度截取点，再投影到 XY：有点的格子是障碍，其余格子仍为未知，不能把无点格子直接当作可通行区域。**目前没有经现场核对的 `工位.yaml`**，车体尺寸、雷达高度和障碍物截取范围也尚未校准。具体事项见 [TODO.md](TODO.md)；原项目说明存档见 [README_UPSTREAM.md](README_UPSTREAM.md)。

准备好 2D 地图后，先只检查定位和规划：

```bash
NAV2_MAP_YAML=/绝对路径/工位.yaml ./scripts/nav2_real.sh
```

统一入口也可直接运行 `ros2 launch me_nav2_bringup real.launch.py mode:=nav map_yaml_file:=/绝对路径/工位.yaml`。脚本默认 `SCOUT_SEND_CONTROL=false`，不发送底盘控制帧；`can0` 未启动时跳过 Scout CAN 节点。完成 [TODO.md](TODO.md) 中的地图、感知、车体参数、CAN 和急停检查后，才启用 `SCOUT_SEND_CONTROL=true`。
