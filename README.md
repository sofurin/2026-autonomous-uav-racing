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
- 仿真载具：默认使用项目自有的 `gz_team_racer`；`gz_x500_depth` 仍可通过 launch 参数选择

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

## 可复现开发环境

首次使用：

```bash
cp .env.example .env
./scripts/environment.sh simulation build
./scripts/environment.sh simulation shell
```

进入容器后统一构建并测试：

```bash
./scripts/build_workspace.sh --test
```

NUC 使用单独的硬件 profile：

```bash
./scripts/environment.sh nuc build
./scripts/environment.sh nuc shell
```

两个 profile 使用相同的 ROS 2、`px4_msgs` 和 Micro XRCE-DDS Agent
基线，但不会自动启动仿真或真机飞行进程。完整说明见
[`docker/README.md`](docker/README.md)。

## NUC 快速检查

在 NUC 上执行：

```bash
./scripts/check_nuc_environment.sh
```

已有旧 NUC 容器尚未迁移时，仍可临时使用兼容入口：

```bash
./scripts/start_ros2_container.sh
```

该脚本只复用旧的本地镜像，不是团队环境基线。新机器和完成迁移后的
NUC 应使用上面的 Compose profile。

## 文档

- [`docs/architecture.md`](docs/architecture.md)：系统边界、链路与当前验证状态
- [`docs/simulation-and-camera.md`](docs/simulation-and-camera.md)：仿真、相机抽象和真机/仿真切换约定
- [`docs/bringup.md`](docs/bringup.md)：建议的上电和启动顺序
- [`docs/decisions/ADR-001-px4-native-ros2-dds.md`](docs/decisions/ADR-001-px4-native-ros2-dds.md)：采用 PX4 原生 ROS 2 DDS 桥接的决策
- [`docs/decisions/ADR-002-reproducible-container-profiles.md`](docs/decisions/ADR-002-reproducible-container-profiles.md)：本地仿真与 NUC 环境统一方案

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

以上 6 个包均可构建。仿真进程、PX4 DDS 传输和最小 Offboard
任务闭环已经接通；感知算法和真机链路仍未实现。

在本地仿真电脑上验证最小任务（自动解锁、起飞 1 m、悬停 5 s、
前进 1 m、返回并降落）：

```bash
cd ~/uav/2026-autonomous-uav-racing
source /opt/ros/humble/setup.bash
source ~/uav/px4_msgs_ws/install/setup.bash
source install/setup.bash

ros2 launch racing_bringup offboard_demo.launch.py \
  px4_dir:=$HOME/PX4-Autopilot \
  headless:=false
```

这是唯一默认启用自动解锁的专用入口，只能用于 SITL。普通 bringup、硬件
launch 和独立控制节点均保持 `allow_arming_command:=false`。运行中可在另一
终端请求安全中止：

```bash
ros2 service call /offboard_mission/abort std_srvs/srv/Trigger '{}'
```

任务状态可从 `/offboard_mission/state` 查看。详细接口和安全边界见
[`docs/specs/minimal-offboard-mission.md`](docs/specs/minimal-offboard-mission.md)。

`mode:=simulation` 已能编排外部 PX4 SITL、Micro XRCE-DDS Agent 和 Gazebo 相机桥。默认模型是项目自有的 `gz_team_racer`，外部 PX4 工作树仍作为依赖；首次使用需要运行 `racing_simulation/scripts/install_team_racer_px4.sh` 注册 airframe。具体启动方式和当前迁移边界见 [`docs/nuc-integration.md`](docs/nuc-integration.md)。

`racing_localization`、`racing_planning` 和自定义消息包将在出现对应节点或消息定义时再创建，避免长期保留没有代码的空包。录包回放与跨包集成测试放在仓库级 `tests/`，无需单独建立 ROS 2 包。

## 仓库约定

- 自研代码进入本仓库，上游源码使用固定版本重新拉取。
- 不提交 `build/`、`install/`、`log/`、飞行日志、录包、视频和本地密钥。
- 硬件未接入或进程未启动时，文档必须写“未验证”，不能把构建成功当作真机通信成功。
