cmake_minimum_required(VERSION 3.8)
project(racing_simulation)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch models tools worlds DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/start_px4_sitl.sh DESTINATION share/${PROJECT_NAME}/scripts)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(
    test_start_px4_sitl
    test/test_start_px4_sitl.py
    TIMEOUT 30
  )
  ament_add_pytest_test(
    test_launch_contract
    test/test_launch_contract.py
    TIMEOUT 30
  )
  ament_add_pytest_test(
    test_team_racer_model
    test/test_team_racer_model.py
    TIMEOUT 30
  )
  ament_add_pytest_test(
    test_robocup_2025_course
    tools/robocup_2025
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tools/robocup_2025
    TIMEOUT 30
  )
endif()

ament_package()
