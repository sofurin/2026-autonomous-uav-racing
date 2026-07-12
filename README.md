# 2026 Autonomous UAV Racing

浙江工业大学 2026 无人机自主竞速项目。

本仓库用于保存团队自研的 ROS 2 节点、可复现的 NUC 运行配置、飞控接口约定和架构决策。PX4、`px4_msgs`、Micro XRCE-DDS Agent 等上游项目不直接复制进仓库，其版本记录在 [`dependencies.lock.md`](dependencies.lock.md) 中。

## 当前基线

- 伴随计算机：Intel NUC，Ubuntu 22.04.5 LTS，x86_64
- 开发方式：工作站通过 Remote SSH 连接 NUC
- ROS 环境：Docker 容器中的 ROS 2 Humble
- 飞控栈：PX4 `release/1.17`
- ROS 2 与 PX4 接口：`px4_msgs` + Micro XRCE-DDS Agent
- 相机：比赛相机型号和驱动尚未确定，不把 NUC 上遗留的 Astra 工作区作为方案基线
- 仿真载具：当前使用旧 PX4 工作树中的 `gz_x500_depth`；模型选择由 launch 参数控制

## 目标数据链路

```text
Camera (TBD)
  -> camera driver
  -> perception / localization
  -> racing mission and trajectory nodes
  -> px4_msgs (/fmu/in/* and /fmu/out/*)
  -> Micro XRCE-DDS Agent
  -> PX4 flight controller
  -> ESC and motors
```

NUC 负责感知、定位、赛道决策和高层轨迹；PX4 飞控负责状态估计、姿态/位置闭环、安全保护和电机输出。

## 快速检查

在 NUC 上执行：

```bash
./scripts/check_nuc_environment.sh
```

启动 ROS 2 开发容器：

```bash
./scripts/start_ros2_container.sh
```

脚本默认使用现有本地镜像 `ros2:humble-desktopV1.0`，可通过 `ROS_IMAGE` 覆盖。该镜像当前还没有可复现的 Dockerfile，详见 [`docker/README.md`](docker/README.md)。

## 文档

- [`docs/architecture.md`](docs/architecture.md)：系统边界、链路与当前验证状态
- [`docs/simulation-and-camera.md`](docs/simulation-and-camera.md)：仿真、相机抽象和真机/仿真切换约定
- [`docs/bringup.md`](docs/bringup.md)：建议的上电和启动顺序
- [`docs/decisions/ADR-001-px4-native-ros2-dds.md`](docs/decisions/ADR-001-px4-native-ros2-dds.md)：采用 PX4 原生 ROS 2 DDS 桥接的决策

## ROS 2 包结构

```text
ros2_ws/src/
├─ racing_bringup/          # 真机与仿真的统一启动入口
├─ racing_description/      # 无人机模型、传感器安装位姿和坐标系
├─ racing_camera/           # 相机驱动适配、参数与标定入口
├─ racing_perception/       # 门框和障碍物感知
├─ racing_px4_control/      # Offboard 与 px4_msgs 接口
└─ racing_simulation/       # PX4 SITL、Gazebo 场景和虚拟传感器
```

以上 6 个包已经有可构建的 ROS 2 骨架。仿真进程与 PX4 DDS 传输已经接通；感知算法、Offboard 控制和真机链路仍未实现。

`mode:=simulation` 已能编排外部 PX4 SITL、Micro XRCE-DDS Agent 和 Gazebo 相机桥。默认模型是 `gz_x500_depth`，旧 PX4 工作树仍作为外部依赖。具体启动方式和当前迁移边界见 [`docs/nuc-integration.md`](docs/nuc-integration.md)。

`racing_localization`、`racing_planning` 和自定义消息包将在出现对应节点或消息定义时再创建，避免长期保留没有代码的空包。录包回放与跨包集成测试放在仓库级 `tests/`，无需单独建立 ROS 2 包。

## 仓库约定

- 自研代码进入本仓库，上游源码使用固定版本重新拉取。
- 不提交 `build/`、`install/`、`log/`、飞行日志、录包、视频和本地密钥。
- 硬件未接入或进程未启动时，文档必须写“未验证”，不能把构建成功当作真机通信成功。
