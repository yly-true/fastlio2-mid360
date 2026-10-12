# Orin NX 硬件配置

- Jetson Orin NX，Ubuntu 22.04、ROS 2 Humble、ARM64。
- MID360 网卡：`enP8p1s0`，Orin `192.168.1.50/24`，雷达 `192.168.1.3`。
- 雷达铭牌码尾号 `58`，不用于推算 IP。
- Scout 底盘 CAN：`can0`，500 kbit/s；每次实车运行前确认接口 UP。
- 当前 3D 地图：`src/me_nav2_bringup/pcd/工位.pcd`；`物理楼446.pcd` 是从原工作空间保留的旧地图。
- Scout/MID360 TF：按当前导航约定，`base → livox` 是零平移、零转角；`base` 原点因此位于雷达原点。车体尺寸和雷达相对地面的高度仍需实测后用于导航参数。

## 速度与控制

- FAST-LIO2 位姿差分发布 `/odom`；线速度和角速度转换到 `base` 子坐标系后写入 `/odom.twist`。
- CAN 驱动只订阅 Nav2 `/cmd_vel` 发控制帧；`publish_odom=false`，不与 FAST-LIO 抢 `/odom` 或 TF。
- `scout_can` 的 `send_control` 默认关闭。当前 CAN 控制帧实现来自旧项目，应先核实 Scout 型号和协议，再进行实车低速测试。
