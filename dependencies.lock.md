# Dependency Baseline

The following revisions were read from the NUC on 2026-07-12. Clone these upstream repositories into a local ROS 2 workspace instead of copying their source into this repository.

| Dependency | Upstream | Branch | Commit |
| --- | --- | --- | --- |
| PX4 Autopilot | `https://github.com/PX4/PX4-Autopilot.git` | `release/1.17` | `2c355919e4ff0ffb0b68a138038f205b6dbefa97` |
| px4_msgs | `https://github.com/PX4/px4_msgs.git` | `main` | `a5aec95ed69086467b1f92de30093a04d03fd1d4` |
| Micro XRCE-DDS Agent | `https://github.com/eProsima/Micro-XRCE-DDS-Agent.git` | `master` | `155cfaaf8b7abac2e85d4a62d3649b09ace0be55` |

## Compatibility rule

`px4_msgs` definitions must remain compatible with the PX4 firmware deployed to the flight controller. Updating either repository requires an explicit compatibility check before flight testing.

## NUC working-tree warning

The inspected PX4 checkout was not clean: `Tools/simulation/gz` was modified and an untracked Xtensa toolchain archive existed under `Tools/setup/`. Those local files are deliberately excluded from this baseline. Review and preserve them separately if they represent intentional work.

The former Astra driver workspace is also deliberately excluded because the competition camera has not been selected.

The NUC Gazebo-model submodule currently contains an uncommitted `realsense_d435` model, an `x500_depth` override and RoboCup course assets. These are project-owned migration candidates, not part of the clean upstream commit recorded above. Do not reset that submodule before the assets are reviewed and migrated.
