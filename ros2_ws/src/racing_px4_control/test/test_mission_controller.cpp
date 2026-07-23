#include <gtest/gtest.h>

#include <cmath>

#include "racing_px4_control/mission_controller.hpp"

namespace
{
using racing_px4_control::MissionConfig;
using racing_px4_control::MissionController;
using racing_px4_control::MissionState;
using racing_px4_control::Telemetry;

Telemetry valid_telemetry()
{
  Telemetry telemetry{};
  telemetry.position_valid = true;
  telemetry.position_age_s = 0.0;
  telemetry.landed = true;
  telemetry.heading = 0.0;
  return telemetry;
}

TEST(MissionController, DefaultsDoNotPermitArming)
{
  MissionController mission{MissionConfig{}};
  EXPECT_FALSE(mission.start(0.0));
  EXPECT_EQ(mission.state(), MissionState::Standby);
}

TEST(MissionController, ManualArmingCanBeRequiredForHardwareFlight)
{
  MissionConfig config{};
  config.allow_mission_start = true;
  config.allow_arming_command = false;
  config.warmup_duration_s = 0.0;
  MissionController mission{config};
  auto telemetry = valid_telemetry();

  ASSERT_TRUE(mission.start(0.0));
  mission.update(0.0, telemetry);
  auto output = mission.update(0.1, telemetry);
  ASSERT_EQ(mission.state(), MissionState::WaitForOffboard);
  EXPECT_TRUE(output.request_offboard);

  telemetry.offboard = true;
  output = mission.update(0.2, telemetry);
  ASSERT_EQ(mission.state(), MissionState::WaitForArm);
  EXPECT_FALSE(output.request_arm);

  telemetry.armed = true;
  telemetry.landed = false;
  output = mission.update(0.3, telemetry);
  EXPECT_EQ(mission.state(), MissionState::Takeoff);
  EXPECT_TRUE(output.publish_setpoint);
}

TEST(MissionController, CompletesNominalMissionInNed)
{
  MissionConfig config{};
  config.allow_mission_start = true;
  config.allow_arming_command = true;
  config.warmup_duration_s = 1.0;
  config.hover_duration_s = 5.0;
  MissionController mission{config};
  auto telemetry = valid_telemetry();

  ASSERT_TRUE(mission.start(0.0));
  auto output = mission.update(0.0, telemetry);
  EXPECT_EQ(mission.state(), MissionState::Warmup);
  EXPECT_TRUE(output.publish_setpoint);

  output = mission.update(1.1, telemetry);
  EXPECT_EQ(mission.state(), MissionState::WaitForOffboard);
  EXPECT_TRUE(output.request_offboard);

  telemetry.offboard = true;
  output = mission.update(1.2, telemetry);
  EXPECT_EQ(mission.state(), MissionState::WaitForArm);
  EXPECT_TRUE(output.request_arm);

  telemetry.armed = true;
  telemetry.landed = false;
  output = mission.update(1.3, telemetry);
  EXPECT_EQ(mission.state(), MissionState::Takeoff);
  EXPECT_NEAR(output.target_z, -1.0, 1e-6);

  telemetry.z = -1.0;
  output = mission.update(2.0, telemetry);
  EXPECT_EQ(mission.state(), MissionState::Hover);

  output = mission.update(7.1, telemetry);
  EXPECT_EQ(mission.state(), MissionState::Forward);
  EXPECT_NEAR(output.target_x, 1.0, 1e-6);
  EXPECT_NEAR(output.target_y, 0.0, 1e-6);

  telemetry.x = 1.0;
  output = mission.update(7.2, telemetry);
  EXPECT_EQ(mission.state(), MissionState::Return);
  EXPECT_NEAR(output.target_x, 0.0, 1e-6);

  telemetry.x = 0.0;
  output = mission.update(7.3, telemetry);
  EXPECT_EQ(mission.state(), MissionState::Landing);
  EXPECT_TRUE(output.request_land);

  telemetry.landed = true;
  telemetry.armed = false;
  mission.update(8.0, telemetry);
  EXPECT_EQ(mission.state(), MissionState::Complete);
}

TEST(MissionController, ForwardUsesCapturedHeading)
{
  MissionConfig config{};
  config.allow_mission_start = true;
  config.allow_arming_command = true;
  config.warmup_duration_s = 0.0;
  config.hover_duration_s = 0.0;
  MissionController mission{config};
  auto telemetry = valid_telemetry();
  telemetry.x = 4.0;
  telemetry.y = -3.0;
  telemetry.z = 0.2;
  telemetry.heading = M_PI_2;

  ASSERT_TRUE(mission.start(0.0));
  mission.update(0.0, telemetry);
  mission.update(0.1, telemetry);
  telemetry.offboard = true;
  mission.update(0.2, telemetry);
  telemetry.armed = true;
  telemetry.landed = false;
  mission.update(0.3, telemetry);
  telemetry.z = -0.8;
  mission.update(0.4, telemetry);
  const auto output = mission.update(0.5, telemetry);

  ASSERT_EQ(mission.state(), MissionState::Forward);
  EXPECT_NEAR(output.target_x, 4.0, 1e-6);
  EXPECT_NEAR(output.target_y, -2.0, 1e-6);
}

TEST(MissionController, StalePositionWhileArmedRequestsLanding)
{
  MissionConfig config{};
  config.allow_mission_start = true;
  config.allow_arming_command = true;
  config.warmup_duration_s = 0.0;
  MissionController mission{config};
  auto telemetry = valid_telemetry();

  ASSERT_TRUE(mission.start(0.0));
  mission.update(0.0, telemetry);
  mission.update(0.1, telemetry);
  telemetry.offboard = true;
  mission.update(0.2, telemetry);
  telemetry.armed = true;
  telemetry.landed = false;
  mission.update(0.3, telemetry);
  telemetry.position_age_s = config.position_timeout_s + 0.1;

  const auto output = mission.update(0.4, telemetry);
  EXPECT_EQ(mission.state(), MissionState::AbortLanding);
  EXPECT_TRUE(output.request_land);
}

TEST(MissionController, GeofenceViolationWhileArmedRequestsLanding)
{
  MissionConfig config{};
  config.allow_mission_start = true;
  config.allow_arming_command = true;
  config.warmup_duration_s = 0.0;
  MissionController mission{config};
  auto telemetry = valid_telemetry();

  ASSERT_TRUE(mission.start(0.0));
  mission.update(0.0, telemetry);
  mission.update(0.1, telemetry);
  telemetry.offboard = true;
  mission.update(0.2, telemetry);
  telemetry.armed = true;
  telemetry.landed = false;
  mission.update(0.3, telemetry);
  telemetry.x = config.max_horizontal_distance_m + 0.1;

  const auto output = mission.update(0.4, telemetry);
  EXPECT_EQ(mission.state(), MissionState::AbortLanding);
  EXPECT_TRUE(output.request_land);
}

TEST(MissionController, AbortBeforeArmingNeverRequestsLand)
{
  MissionConfig config{};
  config.allow_mission_start = true;
  config.allow_arming_command = true;
  MissionController mission{config};
  auto telemetry = valid_telemetry();
  ASSERT_TRUE(mission.start(0.0));
  mission.update(0.0, telemetry);

  const auto output = mission.abort(0.1, telemetry);
  EXPECT_EQ(mission.state(), MissionState::Aborted);
  EXPECT_FALSE(output.request_land);
}
}  // namespace
