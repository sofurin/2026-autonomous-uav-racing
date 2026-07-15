#include <px4_msgs/msg/offboard_control_mode.hpp>
#include <px4_msgs/msg/trajectory_setpoint.hpp>
#include <px4_msgs/msg/vehicle_command.hpp>
#include <px4_msgs/msg/vehicle_land_detected.hpp>
#include <px4_msgs/msg/vehicle_local_position.hpp>
#include <px4_msgs/msg/vehicle_status.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_srvs/srv/trigger.hpp>

#include <chrono>
#include <cmath>
#include <cstdint>
#include <limits>
#include <memory>
#include <string>

#include "racing_px4_control/mission_controller.hpp"

namespace racing_px4_control
{

class OffboardMissionNode : public rclcpp::Node
{
public:
  OffboardMissionNode()
  : Node("offboard_mission")
  {
    MissionConfig config{};
    config.allow_arming_command = declare_parameter("allow_arming_command", false);
    config.takeoff_altitude_m = declare_parameter("takeoff_altitude_m", 1.0);
    config.forward_distance_m = declare_parameter("forward_distance_m", 1.0);
    config.hover_duration_s = declare_parameter("hover_duration_s", 5.0);
    config.warmup_duration_s = declare_parameter("warmup_duration_s", 1.0);
    config.position_timeout_s = declare_parameter("position_timeout_s", 1.0);
    config.phase_timeout_s = declare_parameter("phase_timeout_s", 20.0);
    config.target_tolerance_m = declare_parameter("target_tolerance_m", 0.25);
    config.max_altitude_m = declare_parameter("max_altitude_m", 2.0);
    config.max_horizontal_distance_m =
      declare_parameter("max_horizontal_distance_m", 3.0);
    auto_start_ = declare_parameter("auto_start", false);
    command_retry_s_ = declare_parameter("command_retry_s", 1.0);
    const auto local_position_topic = declare_parameter(
      "local_position_topic", std::string{"/fmu/out/vehicle_local_position_v1"});
    const auto vehicle_status_topic = declare_parameter(
      "vehicle_status_topic", std::string{"/fmu/out/vehicle_status_v1"});
    const auto land_detected_topic = declare_parameter(
      "land_detected_topic", std::string{"/fmu/out/vehicle_land_detected"});
    mission_ = std::make_unique<MissionController>(config);

    const auto input_qos = rclcpp::QoS(rclcpp::KeepLast(10)).best_effort();
    local_position_sub_ = create_subscription<px4_msgs::msg::VehicleLocalPosition>(
      local_position_topic, input_qos,
      [this](const px4_msgs::msg::VehicleLocalPosition::SharedPtr msg) {
        telemetry_.position_valid = msg->xy_valid && msg->z_valid &&
          std::isfinite(msg->x) && std::isfinite(msg->y) && std::isfinite(msg->z) &&
          std::isfinite(msg->heading);
        telemetry_.x = msg->x;
        telemetry_.y = msg->y;
        telemetry_.z = msg->z;
        telemetry_.heading = msg->heading;
        last_position_rx_ = now();
        position_received_ = true;
      });
    vehicle_status_sub_ = create_subscription<px4_msgs::msg::VehicleStatus>(
      vehicle_status_topic, input_qos,
      [this](const px4_msgs::msg::VehicleStatus::SharedPtr msg) {
        telemetry_.armed = msg->arming_state == px4_msgs::msg::VehicleStatus::ARMING_STATE_ARMED;
        telemetry_.offboard =
          msg->nav_state == px4_msgs::msg::VehicleStatus::NAVIGATION_STATE_OFFBOARD;
      });
    land_detected_sub_ = create_subscription<px4_msgs::msg::VehicleLandDetected>(
      land_detected_topic, input_qos,
      [this](const px4_msgs::msg::VehicleLandDetected::SharedPtr msg) {
        telemetry_.landed = msg->landed;
      });

    offboard_mode_pub_ = create_publisher<px4_msgs::msg::OffboardControlMode>(
      "/fmu/in/offboard_control_mode", 10);
    trajectory_pub_ = create_publisher<px4_msgs::msg::TrajectorySetpoint>(
      "/fmu/in/trajectory_setpoint", 10);
    vehicle_command_pub_ = create_publisher<px4_msgs::msg::VehicleCommand>(
      "/fmu/in/vehicle_command", 10);
    state_pub_ = create_publisher<std_msgs::msg::String>(
      "~/state", rclcpp::QoS(1).transient_local());

    start_service_ = create_service<std_srvs::srv::Trigger>(
      "~/start",
      [this](const std_srvs::srv::Trigger::Request::SharedPtr,
      std_srvs::srv::Trigger::Response::SharedPtr response) {
        response->success = mission_->start(seconds_now());
        response->message = response->success ?
          "Offboard mission started; waiting for valid PX4 local position" :
          "Mission start rejected (arming disabled or mission already active)";
        publish_state(true);
      });
    abort_service_ = create_service<std_srvs::srv::Trigger>(
      "~/abort",
      [this](const std_srvs::srv::Trigger::Request::SharedPtr,
      std_srvs::srv::Trigger::Response::SharedPtr response) {
        const auto output = mission_->abort(seconds_now(), telemetry_);
        handle_output(output);
        response->success = true;
        response->message = "Mission abort processed";
        publish_state(true);
      });

    telemetry_.landed = false;
    timer_ = create_wall_timer(
      std::chrono::milliseconds(100), std::bind(&OffboardMissionNode::timer_callback, this));
    publish_state(true);

    RCLCPP_WARN(
      get_logger(),
      "PX4 Offboard can move and arm a vehicle. allow_arming_command=%s auto_start=%s",
      config.allow_arming_command ? "true" : "false", auto_start_ ? "true" : "false");
  }

private:
  double seconds_now() const
  {
    return now().seconds();
  }

  uint64_t timestamp_us() const
  {
    return static_cast<uint64_t>(now().nanoseconds() / 1000);
  }

  void timer_callback()
  {
    if (auto_start_ && !auto_start_attempted_) {
      auto_start_attempted_ = true;
      if (!mission_->start(seconds_now())) {
        RCLCPP_ERROR(get_logger(), "auto_start was rejected; check allow_arming_command");
      }
    }

    telemetry_.position_age_s = position_received_ ?
      (now() - last_position_rx_).seconds() : std::numeric_limits<double>::infinity();

    const auto previous_state = mission_->state();
    const auto output = mission_->update(seconds_now(), telemetry_);
    handle_output(output);
    if (mission_->state() != previous_state) {
      publish_state(true);
    }
  }

  void handle_output(const MissionOutput & output)
  {
    if (output.publish_setpoint) {
      publish_offboard_mode();
      publish_trajectory(output);
    }

    const double current_s = seconds_now();
    if (current_s - last_command_s_ < command_retry_s_) {
      return;
    }
    if (output.request_offboard) {
      publish_vehicle_command(
        px4_msgs::msg::VehicleCommand::VEHICLE_CMD_DO_SET_MODE, 1.0F, 6.0F);
      last_command_s_ = current_s;
    } else if (output.request_arm) {
      publish_vehicle_command(
        px4_msgs::msg::VehicleCommand::VEHICLE_CMD_COMPONENT_ARM_DISARM,
        static_cast<float>(px4_msgs::msg::VehicleCommand::ARMING_ACTION_ARM), 0.0F);
      last_command_s_ = current_s;
    } else if (output.request_land) {
      publish_vehicle_command(px4_msgs::msg::VehicleCommand::VEHICLE_CMD_NAV_LAND, 0.0F, 0.0F);
      last_command_s_ = current_s;
    }
  }

  void publish_offboard_mode()
  {
    px4_msgs::msg::OffboardControlMode msg{};
    msg.timestamp = timestamp_us();
    msg.position = true;
    offboard_mode_pub_->publish(msg);
  }

  void publish_trajectory(const MissionOutput & output)
  {
    const float nan = std::numeric_limits<float>::quiet_NaN();
    px4_msgs::msg::TrajectorySetpoint msg{};
    msg.timestamp = timestamp_us();
    msg.position = {
      static_cast<float>(output.target_x), static_cast<float>(output.target_y),
      static_cast<float>(output.target_z)};
    msg.velocity = {nan, nan, nan};
    msg.acceleration = {nan, nan, nan};
    msg.jerk = {nan, nan, nan};
    msg.yaw = static_cast<float>(output.target_yaw);
    msg.yawspeed = nan;
    trajectory_pub_->publish(msg);
  }

  void publish_vehicle_command(const uint32_t command, const float param1, const float param2)
  {
    px4_msgs::msg::VehicleCommand msg{};
    msg.timestamp = timestamp_us();
    msg.param1 = param1;
    msg.param2 = param2;
    msg.command = command;
    msg.target_system = 1;
    msg.target_component = 1;
    msg.source_system = 1;
    msg.source_component = 1;
    msg.from_external = true;
    vehicle_command_pub_->publish(msg);
  }

  void publish_state(const bool log)
  {
    std_msgs::msg::String msg{};
    msg.data = MissionController::state_name(mission_->state());
    if (!mission_->reason().empty()) {
      msg.data += ": " + mission_->reason();
    }
    state_pub_->publish(msg);
    if (log) {
      RCLCPP_INFO(get_logger(), "Mission state: %s", msg.data.c_str());
    }
  }

  std::unique_ptr<MissionController> mission_;
  Telemetry telemetry_{};
  bool auto_start_{false};
  bool auto_start_attempted_{false};
  bool position_received_{false};
  double command_retry_s_{1.0};
  double last_command_s_{-std::numeric_limits<double>::infinity()};
  rclcpp::Time last_position_rx_{0, 0, RCL_ROS_TIME};

  rclcpp::Subscription<px4_msgs::msg::VehicleLocalPosition>::SharedPtr local_position_sub_;
  rclcpp::Subscription<px4_msgs::msg::VehicleStatus>::SharedPtr vehicle_status_sub_;
  rclcpp::Subscription<px4_msgs::msg::VehicleLandDetected>::SharedPtr land_detected_sub_;
  rclcpp::Publisher<px4_msgs::msg::OffboardControlMode>::SharedPtr offboard_mode_pub_;
  rclcpp::Publisher<px4_msgs::msg::TrajectorySetpoint>::SharedPtr trajectory_pub_;
  rclcpp::Publisher<px4_msgs::msg::VehicleCommand>::SharedPtr vehicle_command_pub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr state_pub_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr start_service_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr abort_service_;
  rclcpp::TimerBase::SharedPtr timer_;
};

}  // namespace racing_px4_control

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<racing_px4_control::OffboardMissionNode>());
  rclcpp::shutdown();
  return 0;
}
