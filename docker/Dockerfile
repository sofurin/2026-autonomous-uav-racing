# syntax=docker/dockerfile:1.7

# Pin the multi-architecture digest so every machine starts from the same ROS 2
# Humble desktop filesystem. Update it deliberately together with validation.
FROM osrf/ros:humble-desktop@sha256:3d87cf339919a85cff7743ec9ba5e7ec81ccc26c9f722f1c7a6af5008dfdc128 AS base

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG RACING_UID=1000
ARG RACING_GID=1000
ENV DEBIAN_FRONTEND=noninteractive \
    ROS_DISTRO=humble \
    PX4_AUTOPILOT_DIR=/opt/upstream/PX4-Autopilot

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ca-certificates \
      cmake \
      curl \
      git \
      libasio-dev \
      libtinyxml2-dev \
      ninja-build \
      pkg-config \
      python3-colcon-common-extensions \
      python3-pip \
      python3-pytest \
      python3-vcstool \
      python3-yaml \
      ros-humble-ament-cmake-pytest \
      ros-humble-camera-info-manager \
      ros-humble-cv-bridge \
      ros-humble-image-transport \
      ros-humble-robot-state-publisher \
      ros-humble-ros-gz-bridge \
      ros-humble-xacro \
      sudo \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --no-cache-dir pymavlink==2.4.49

COPY dependencies.repos /tmp/dependencies.repos
RUN mkdir -p /opt/upstream \
    && vcs import /opt/upstream < /tmp/dependencies.repos \
    && git -C /opt/upstream/PX4-Autopilot submodule update --init --recursive \
    && git -C /opt/upstream/Micro-XRCE-DDS-Agent submodule update --init --recursive \
    && test "$(git -C /opt/upstream/PX4-Autopilot rev-parse HEAD)" = "6737fe1c3754a81a983b8f5aea6797b7d1669be6" \
    && test "$(git -C /opt/upstream/px4_msgs rev-parse HEAD)" = "a5aec95ed69086467b1f92de30093a04d03fd1d4" \
    && test "$(git -C /opt/upstream/Micro-XRCE-DDS-Agent rev-parse HEAD)" = "155cfaaf8b7abac2e85d4a62d3649b09ace0be55"

RUN source /opt/ros/humble/setup.bash \
    && colcon --log-base /tmp/px4-msgs-log build \
      --base-paths /opt/upstream/px4_msgs \
      --build-base /tmp/px4-msgs-build \
      --install-base /opt/px4_msgs/install \
      --merge-install \
    && test -f /opt/px4_msgs/install/setup.bash \
    && rm -rf /tmp/px4-msgs-build /tmp/px4-msgs-log

RUN cmake \
      -S /opt/upstream/Micro-XRCE-DDS-Agent \
      -B /tmp/micro-xrce-agent-build \
      -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /tmp/micro-xrce-agent-build --parallel "$(nproc)" \
    && cmake --install /tmp/micro-xrce-agent-build \
    && ldconfig \
    && MicroXRCEAgent --version \
    && rm -rf /tmp/micro-xrce-agent-build

RUN groupadd --gid "$RACING_GID" racing \
    && useradd --uid "$RACING_UID" --gid "$RACING_GID" --create-home --shell /bin/bash racing \
    && usermod -aG dialout,video racing \
    && printf 'racing ALL=(ALL) NOPASSWD:ALL\n' >/etc/sudoers.d/racing \
    && chmod 0440 /etc/sudoers.d/racing

COPY docker/entrypoint.sh /usr/local/bin/racing-entrypoint
RUN chmod 0755 /usr/local/bin/racing-entrypoint \
    && chown -R racing:racing /opt/upstream /opt/px4_msgs

WORKDIR /workspace/project
USER racing
ENTRYPOINT ["/usr/local/bin/racing-entrypoint"]
CMD ["bash"]


FROM base AS simulation

USER root
ENV DEBIAN_FRONTEND=noninteractive

# PX4's official Ubuntu setup installs the matching Gazebo simulation toolchain.
RUN /opt/upstream/PX4-Autopilot/Tools/setup/ubuntu.sh --no-nuttx \
    && rm -rf /var/lib/apt/lists/*

COPY ros2_ws/src/racing_simulation/scripts/install_team_racer_px4.sh /tmp/team-racer/scripts/install_team_racer_px4.sh
COPY ros2_ws/src/racing_simulation/models/team_racer/config/4022_gz_team_racer /tmp/team-racer/models/team_racer/config/4022_gz_team_racer
RUN chmod 0755 /tmp/team-racer/scripts/install_team_racer_px4.sh \
    && /tmp/team-racer/scripts/install_team_racer_px4.sh --px4-dir /opt/upstream/PX4-Autopilot \
    && rm -rf /tmp/team-racer \
    && chown -R racing:racing /opt/upstream/PX4-Autopilot

USER racing


FROM base AS nuc

# Hardware-specific drivers are intentionally not guessed here. Add the chosen
# camera driver only after its model and ROS topic contract are accepted.
USER racing
