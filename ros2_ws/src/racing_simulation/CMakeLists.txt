cmake_minimum_required(VERSION 3.8)
project(racing_simulation)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch models worlds DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/start_px4_sitl.sh DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(
    test_start_px4_sitl
    test/test_start_px4_sitl.py
    TIMEOUT 30
  )
endif()

ament_package()
