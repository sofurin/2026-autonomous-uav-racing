#pragma once

#include <string>

namespace racing_px4_control
{

enum class MissionState
{
  Standby,
  WaitForPosition,
  Warmup,
  WaitForOffboard,
  WaitForArm,
  Takeoff,
  Hover,
  Forward,
  Return,
  Landing,
  Complete,
  AbortLanding,
  Aborted,
};

struct MissionConfig
{
  bool allow_arming_command{false};
  double takeoff_altitude_m{1.0};
  double forward_distance_m{1.0};
  double hover_duration_s{5.0};
  double warmup_duration_s{1.0};
  double position_timeout_s{1.0};
  double phase_timeout_s{20.0};
  double target_tolerance_m{0.25};
  double max_altitude_m{2.0};
  double max_horizontal_distance_m{3.0};
};

struct Telemetry
{
  bool position_valid{false};
  bool armed{false};
  bool offboard{false};
  bool landed{true};
  double position_age_s{0.0};
  double x{0.0};
  double y{0.0};
  double z{0.0};
  double heading{0.0};
};

struct MissionOutput
{
  bool publish_setpoint{false};
  bool request_offboard{false};
  bool request_arm{false};
  bool request_land{false};
  double target_x{0.0};
  double target_y{0.0};
  double target_z{0.0};
  double target_yaw{0.0};
};

class MissionController
{
public:
  explicit MissionController(MissionConfig config);

  bool start(double now_s);
  MissionOutput update(double now_s, const Telemetry & telemetry);
  MissionOutput abort(double now_s, const Telemetry & telemetry);

  MissionState state() const;
  const std::string & reason() const;
  static const char * state_name(MissionState state);

private:
  bool position_is_fresh(const Telemetry & telemetry) const;
  bool target_reached(const Telemetry & telemetry, double x, double y, double z) const;
  bool flight_boundary_exceeded(const Telemetry & telemetry) const;
  bool phase_timed_out(double now_s) const;
  bool state_requires_offboard() const;
  void transition(MissionState next, double now_s);
  MissionOutput output_for_state() const;
  MissionOutput fail(double now_s, const Telemetry & telemetry, const std::string & reason);

  MissionConfig config_;
  MissionState state_{MissionState::Standby};
  std::string reason_;
  double phase_started_s_{0.0};
  bool home_captured_{false};
  double home_x_{0.0};
  double home_y_{0.0};
  double home_z_{0.0};
  double home_heading_{0.0};
};

}  // namespace racing_px4_control

