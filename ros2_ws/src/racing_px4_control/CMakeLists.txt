cmake_minimum_required(VERSION 3.8)
project(racing_px4_control)

find_package(ament_cmake REQUIRED)
find_package(px4_msgs REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)

add_library(mission_controller src/mission_controller.cpp)
target_compile_features(mission_controller PUBLIC cxx_std_17)
target_include_directories(
  mission_controller
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

add_executable(offboard_mission src/offboard_mission_node.cpp)
target_compile_features(offboard_mission PUBLIC cxx_std_17)
target_link_libraries(offboard_mission mission_controller)
ament_target_dependencies(offboard_mission px4_msgs rclcpp std_msgs std_srvs)

install(DIRECTORY config launch DESTINATION share/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include)
install(
  TARGETS mission_controller
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
install(TARGETS offboard_mission DESTINATION lib/${PROJECT_NAME})

ament_export_targets(export_${PROJECT_NAME} HAS_LIBRARY_TARGET)
ament_export_include_directories(include)
ament_export_dependencies(px4_msgs rclcpp std_msgs std_srvs)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_mission_controller test/test_mission_controller.cpp)
  target_link_libraries(test_mission_controller mission_controller)
endif()

ament_package()
