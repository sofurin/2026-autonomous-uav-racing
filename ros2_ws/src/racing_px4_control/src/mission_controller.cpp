#include "racing_px4_control/mission_controller.hpp"

#include <algorithm>
#include <cmath>
#include <utility>

namespace racing_px4_control
{

MissionController::MissionController(MissionConfig config)
: config_(std::move(config))
{
}

bool MissionController::start(const double now_s)
{
  if (!config_.allow_arming_command ||
    (state_ != MissionState::Standby && state_ != MissionState::Complete &&
    state_ != MissionState::Aborted))
  {
    return false;
  }

  reason_.clear();
  home_captured_ = false;
  transition(MissionState::WaitForPosition, now_s);
  return true;
}

MissionOutput MissionController::update(const double now_s, const Telemetry & telemetry)
{
  if (state_ == MissionState::Standby || state_ == MissionState::Complete ||
    state_ == MissionState::Aborted)
  {
    return output_for_state();
  }

  if (state_ == MissionState::WaitForPosition) {
    if (!position_is_fresh(telemetry) || !std::isfinite(telemetry.heading)) {
      return output_for_state();
    }
    home_x_ = telemetry.x;
    home_y_ = telemetry.y;
    home_z_ = telemetry.z;
    home_heading_ = telemetry.heading;
    home_captured_ = true;
    transition(MissionState::Warmup, now_s);
    return output_for_state();
  }

  if (!position_is_fresh(telemetry)) {
    return fail(now_s, telemetry, "PX4 local position became invalid or stale");
  }
  if (telemetry.armed && flight_boundary_exceeded(telemetry)) {
    return fail(now_s, telemetry, "mission safety boundary exceeded");
  }
  if (telemetry.armed && state_requires_offboard() && !telemetry.offboard) {
    return fail(now_s, telemetry, "Offboard mode was lost during flight");
  }
  if (phase_timed_out(now_s) && state_ != MissionState::Hover &&
    state_ != MissionState::Landing && state_ != MissionState::AbortLanding)
  {
    return fail(now_s, telemetry, "mission phase timed out");
  }

  switch (state_) {
    case MissionState::Warmup:
      if (now_s - phase_started_s_ >= config_.warmup_duration_s) {
        transition(MissionState::WaitForOffboard, now_s);
      }
      break;
    case MissionState::WaitForOffboard:
      if (telemetry.offboard) {
        transition(MissionState::WaitForArm, now_s);
      }
      break;
    case MissionState::WaitForArm:
      if (!telemetry.offboard) {
        transition(MissionState::WaitForOffboard, now_s);
      } else if (telemetry.armed) {
        transition(MissionState::Takeoff, now_s);
      }
      break;
    case MissionState::Takeoff:
      if (target_reached(telemetry, home_x_, home_y_, home_z_ - config_.takeoff_altitude_m)) {
        transition(MissionState::Hover, now_s);
      }
      break;
    case MissionState::Hover:
      if (now_s - phase_started_s_ >= config_.hover_duration_s) {
        transition(MissionState::Forward, now_s);
      }
      break;
    case MissionState::Forward:
      if (target_reached(
          telemetry,
          home_x_ + config_.forward_distance_m * std::cos(home_heading_),
          home_y_ + config_.forward_distance_m * std::sin(home_heading_),
          home_z_ - config_.takeoff_altitude_m))
      {
        transition(MissionState::Return, now_s);
      }
      break;
    case MissionState::Return:
      if (target_reached(telemetry, home_x_, home_y_, home_z_ - config_.takeoff_altitude_m)) {
        transition(MissionState::Landing, now_s);
      }
      break;
    case MissionState::Landing:
      if (telemetry.landed) {
        transition(MissionState::Complete, now_s);
      }
      break;
    case MissionState::AbortLanding:
      if (telemetry.landed) {
        transition(MissionState::Aborted, now_s);
      }
      break;
    default:
      break;
  }

  return output_for_state();
}

MissionOutput MissionController::abort(const double now_s, const Telemetry & telemetry)
{
  if (state_ == MissionState::Standby || state_ == MissionState::Complete ||
    state_ == MissionState::Aborted)
  {
    return output_for_state();
  }
  return fail(now_s, telemetry, "abort requested");
}

MissionState MissionController::state() const
{
  return state_;
}

const std::string & MissionController::reason() const
{
  return reason_;
}

const char * MissionController::state_name(const MissionState state)
{
  switch (state) {
    case MissionState::Standby: return "standby";
    case MissionState::WaitForPosition: return "wait_for_position";
    case MissionState::Warmup: return "warmup";
    case MissionState::WaitForOffboard: return "wait_for_offboard";
    case MissionState::WaitForArm: return "wait_for_arm";
    case MissionState::Takeoff: return "takeoff";
    case MissionState::Hover: return "hover";
    case MissionState::Forward: return "forward";
    case MissionState::Return: return "return";
    case MissionState::Landing: return "landing";
    case MissionState::Complete: return "complete";
    case MissionState::AbortLanding: return "abort_landing";
    case MissionState::Aborted: return "aborted";
  }
  return "unknown";
}

bool MissionController::position_is_fresh(const Telemetry & telemetry) const
{
  return telemetry.position_valid && telemetry.position_age_s <= config_.position_timeout_s &&
         std::isfinite(telemetry.x) && std::isfinite(telemetry.y) &&
         std::isfinite(telemetry.z);
}

bool MissionController::target_reached(
  const Telemetry & telemetry, const double x, const double y, const double z) const
{
  const double dx = telemetry.x - x;
  const double dy = telemetry.y - y;
  const double dz = telemetry.z - z;
  return std::sqrt(dx * dx + dy * dy + dz * dz) <= config_.target_tolerance_m;
}

bool MissionController::flight_boundary_exceeded(const Telemetry & telemetry) const
{
  if (!home_captured_) {
    return false;
  }
  const double dx = telemetry.x - home_x_;
  const double dy = telemetry.y - home_y_;
  const double horizontal_distance = std::hypot(dx, dy);
  const double altitude = home_z_ - telemetry.z;
  return horizontal_distance > config_.max_horizontal_distance_m ||
         altitude > config_.max_altitude_m || altitude < -0.5;
}

bool MissionController::phase_timed_out(const double now_s) const
{
  return now_s - phase_started_s_ > config_.phase_timeout_s;
}

bool MissionController::state_requires_offboard() const
{
  return state_ == MissionState::Takeoff || state_ == MissionState::Hover ||
         state_ == MissionState::Forward || state_ == MissionState::Return;
}

void MissionController::transition(const MissionState next, const double now_s)
{
  state_ = next;
  phase_started_s_ = now_s;
}

MissionOutput MissionController::output_for_state() const
{
  MissionOutput output{};
  const double flight_z = home_z_ - config_.takeoff_altitude_m;
  output.target_x = home_x_;
  output.target_y = home_y_;
  output.target_z = home_z_;
  output.target_yaw = home_heading_;

  switch (state_) {
    case MissionState::Warmup:
    case MissionState::WaitForOffboard:
    case MissionState::WaitForArm:
      output.publish_setpoint = true;
      break;
    case MissionState::Takeoff:
    case MissionState::Hover:
    case MissionState::Return:
      output.publish_setpoint = true;
      output.target_z = flight_z;
      break;
    case MissionState::Forward:
      output.publish_setpoint = true;
      output.target_x = home_x_ + config_.forward_distance_m * std::cos(home_heading_);
      output.target_y = home_y_ + config_.forward_distance_m * std::sin(home_heading_);
      output.target_z = flight_z;
      break;
    case MissionState::Landing:
    case MissionState::AbortLanding:
      output.request_land = true;
      break;
    default:
      break;
  }

  output.request_offboard = state_ == MissionState::WaitForOffboard;
  output.request_arm = state_ == MissionState::WaitForArm;
  return output;
}

MissionOutput MissionController::fail(
  const double now_s, const Telemetry & telemetry, const std::string & reason)
{
  reason_ = reason;
  transition(telemetry.armed ? MissionState::AbortLanding : MissionState::Aborted, now_s);
  return output_for_state();
}

}  // namespace racing_px4_control

