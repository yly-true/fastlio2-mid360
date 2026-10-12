# 工位导航待做

部署目标：Orin NX，工作空间 `/home/orin-nx-1/Lidar_nav2_ws`，ROS 2 Humble。数据流：MID360 → FAST-LIO2 → 3D GICP 修正 `map→odom` → 同坐标的 2D 占据地图与实时障碍 → Nav2 → Scout CAN。统一启动入口为 `me_nav2_bringup/real.launch.py`。

## 已完成的代码与已有观察

- [x] 建图、3D 重定位和 Nav2 三种模式收敛到一个 launch；默认只构建 6 个包。`/odom` 与 `/registered_scan` 由 `me_nav2_bringup/fastlio_bridge` 提供；Scout CAN 默认不发控制帧、不发布里程计或 TF。
- [x] 第一次建图使用 `fastlio2old`，第二次使用 `fastlio2new`；导航 TF 为 `map→odom→base→livox`，`base` 与 `livox` 重合。Nav2 的全局规划已配置为不穿越未知区，启动时要求显式传入已存在的 2D 地图 YAML；规划效果仍待实测。
- [x] 6 包构建、统一 launch 三种模式的启动配置、桥接节点与 GICP 的合成数据检查已通过；**这不等于实车整链路验证**。
- [x] 先前在 Orin NX 上观察到 MID360 点云/IMU、FAST-LIO2 里程计和 3D GICP 运行。新地点 3D 图 `src/me_nav2_bringup/pcd/工位.pcd` 已保存，重定位曾由用户初步目视确认；统一入口改造后的 Orin NX 实测仍待进行。

## 1. 制作同坐标系的 2D 地图（下一步）

- [ ] 用 `工位.pcd` 生成预览：确定地面在 3D `map` 中的高度，选取会挡住车体的高度范围，过滤噪点后投影到 XY 栅格。`z=0` 不一定是地面；手持建图导致高度变化时不能使用单一全局 Z 截片。
- [ ] 标记三类格子：固定障碍 `100`、确认可通行 `0`、未确认 `-1`。PCD 没有点不能自动证明可通行；可结合地面点和现场核对，人工修正门、通道、桌下空间、玻璃及未扫描区域。现有 `pcd2pgm` 仅生成障碍和未知，需补齐空闲区域。
- [ ] 输出 `src/me_nav2_bringup/map/工位.pgm` 和 `工位.yaml`，分辨率暂用 0.05 m；PGM 的原点、像素方向与 PCD 的 `map` XY 一致，不额外旋转或平移地图。
- [ ] 在 RViz 叠加 2D 地图、3D 地图和已重定位的机器人位置；现场核对墙、门、通道、机器人起点和终点。检查最窄通道在考虑车体宽度后仍可通过。**通过条件：** 2D 墙体与 3D 墙体重合，车体位于可通行格，未知区不会被误规划为通路。

## 2. 装车后核对定位与感知

- [ ] 在 Orin NX 上确认 `nav2_bringup`、`nav2_map_server`、`nav2_lifecycle_manager` 和 `pointcloud_to_laserscan` 已安装；本地开发机缺少这些包，尚未运行 Nav2。
- [ ] 用 `mode:=mapping` 保存新图，再用 `mode:=relocalization map_pcd:=/绝对路径/新图.pcd` 验证统一入口，检查 MID360、FAST-LIO2、GICP、RViz 与地图对齐。
- [ ] 固定 MID360；当前按约定将 `base` 与 `livox` 设为重合，核对导航所需的车体长宽、雷达实际高度和离地间隙。若以后把 `base` 原点改回车体中心，需同步修改静态 TF 和里程计换算。
- [ ] 在车上静止、直行、转弯、回到起点，确认 FAST-LIO2 位姿无突跳，GICP 持续匹配，`map→odom→base→livox` 连续且 TF 没有重复发布者。记录闭环误差。
- [ ] 检查 `/odom` 唯一发布者、坐标系与 `base` 坐标下的 `vx/vy/wz`；当前 `/odom` 由 `me_nav2_bringup/fastlio_bridge` 对位姿差分得到，底盘节点保持不发布 `/odom`。
- [ ] 检查 `/registered_scan→/scan` 是否覆盖机器人前方及侧方的近距离障碍；按装车高度调整 `Pointcloud2d_3d.yaml` 的 `min_height/max_height`。当前范围 0.2–1.0 m 是示例，不保证能看到低矮障碍。

## 3. 接 Nav2，先只看规划

- [ ] 生成并校验 `工位.yaml` 后，通过 `NAV2_MAP_YAML=/绝对路径/工位.yaml ./scripts/nav2_real.sh` 显式传入；核对 `map_server` 发布的 `/map` 与 3D 定位的 `map` 重合。
- [ ] 按实测车体尺寸校准 `footprint`、膨胀半径、速度和加速度。确认全局静态层使用工位地图，局部障碍层使用实时 `/scan`。
- [ ] 保持 `SCOUT_SEND_CONTROL=false`，启动导航入口，在 RViz 给几个位于已知空闲区的目标。**通过条件：** 能生成不穿墙、不穿未知区的路径；移动障碍出现在局部代价地图中；机器人位置与地图重合；`/cmd_vel` 方向符合预期。

## 4. 底盘实车闭环

- [ ] 核对 Scout 型号、CAN 500 kbit/s、控制帧协议、反馈帧的速度符号和量纲；确认急停、零速超时以及通信断开后的停车行为。
- [ ] 在空旷场地低速验证前进、后退、转弯和停止，再启用 `SCOUT_SEND_CONTROL=true` 进行短距离导航。逐步检查刹停距离、定位丢失处理和动态障碍避让。
- [ ] 将现场确认的地图路径、车体参数和 Nav2/CAN 调参结果更新到 `README.md`，清除不适用的示例参数。

当前仓库有旧示例 2D 地图文件，但没有经现场核对的 `工位.yaml`；实车 Nav2 和底盘闭环尚未验证。
